import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import uuid

from app.services.ai_normalizer import ai_normalizer
from app.services.geocoding_service import geocoding_service
from app.services.postgres_database import get_postgres_database
from app.models.property import Property, PropertyCategory, AuctionType
from app.utils.quality_auditor import get_quality_auditor, QualityAuditor

logger = logging.getLogger(__name__)
db = get_postgres_database()

class ScraperPipeline:
    """Pipeline completo: Extração -> Normalização IA -> Geocoding -> Banco"""
    
    def __init__(self):
        self.stats = {
            "extracted": 0,
            "normalized": 0,
            "geocoded": 0,
            "saved": 0,
            "errors": 0
        }
    
    async def process_properties(
        self, 
        properties: List[Dict], 
        source: str = "unknown",
        skip_geocoding: bool = False
    ) -> Dict:
        """Processa lista de imóveis pelo pipeline completo"""
        
        logger.info(f"Iniciando pipeline para {len(properties)} imóveis de '{source}'")
        self.stats = {"extracted": len(properties), "normalized": 0, "geocoded": 0, "saved": 0, "errors": 0}
        
        try:
            # FASE 1: Normalização com IA
            logger.info("FASE 1: Normalizando dados com IA...")
            normalized = await ai_normalizer.normalize_batch(properties)
            self.stats["normalized"] = len(normalized)
            
            # FASE 2: Geocoding
            if not skip_geocoding:
                logger.info("FASE 2: Geocodificando endereços...")
                geocoded = await geocoding_service.geocode_batch(normalized, delay=1.0)
                self.stats["geocoded"] = sum(1 for p in geocoded if p.get('latitude'))
            else:
                geocoded = normalized
                logger.info("FASE 2: Geocoding pulado (skip_geocoding=True)")
            
            # FASE 3: Salvar no banco
            logger.info("FASE 3: Salvando no banco de dados...")
            saved_count = await self._save_to_database(geocoded, source)
            self.stats["saved"] = saved_count
            
        except Exception as e:
            logger.error(f"Erro no pipeline: {e}")
            self.stats["errors"] += 1
        
        logger.info(f"Pipeline finalizado: {self.stats}")
        return self.stats
    
    def _map_category_to_enum(self, category_str: str) -> PropertyCategory:
        """Mapeia string de categoria para enum PropertyCategory"""
        category_map = {
            "Apartamento": PropertyCategory.APARTAMENTO,
            "Casa": PropertyCategory.CASA,
            "Terreno": PropertyCategory.TERRENO,
            "Comercial": PropertyCategory.COMERCIAL,
            "Galpão": PropertyCategory.COMERCIAL,  # Mapeia para Comercial
            "Fazenda": PropertyCategory.RURAL,
            "Sítio": PropertyCategory.RURAL,
            "Chácara": PropertyCategory.RURAL,
            "Sala Comercial": PropertyCategory.COMERCIAL,
            "Loja": PropertyCategory.COMERCIAL,
            "Prédio": PropertyCategory.COMERCIAL,
            "Garagem": PropertyCategory.ESTACIONAMENTO,
            "Imóvel Rural": PropertyCategory.RURAL,
            "Outro": PropertyCategory.OUTRO,
        }
        return category_map.get(category_str, PropertyCategory.OUTRO)
    
    def _dict_to_property(self, prop_dict: Dict, source: str) -> Optional[Property]:
        """Converte dicionário para objeto Property"""
        try:
            # Mapear campos do pipeline para o modelo Property
            category_str = prop_dict.get('category', 'Outro')
            category = self._map_category_to_enum(category_str)
            
            # Mapear auction_type (default para EXTRAJUDICIAL se não especificado)
            auction_type_str = prop_dict.get('auction_type', 'Extrajudicial')
            try:
                auction_type = AuctionType(auction_type_str)
            except:
                auction_type = AuctionType.EXTRAJUDICIAL
            
            # Criar ID único se não existir
            prop_id = prop_dict.get('external_id') or prop_dict.get('id') or prop_dict.get('url', '')
            if not prop_id:
                prop_id = str(uuid.uuid4())
            
            # Mapear valores
            price = prop_dict.get('price') or prop_dict.get('second_auction_value')
            evaluated_price = prop_dict.get('evaluated_price') or prop_dict.get('evaluation_value')
            discount = prop_dict.get('discount') or prop_dict.get('discount_percentage')
            area = prop_dict.get('area') or prop_dict.get('area_total')
            
            # Parse de data de leilão
            auction_date = prop_dict.get('auction_date') or prop_dict.get('second_auction_date')
            if isinstance(auction_date, str):
                try:
                    auction_date = datetime.fromisoformat(auction_date.replace('Z', '+00:00'))
                except:
                    auction_date = None
            
            property_obj = Property(
                id=prop_id,
                title=prop_dict.get('title', 'Imóvel em Leilão'),
                category=category,
                auction_type=auction_type,
                state=prop_dict.get('state', 'SP'),
                city=prop_dict.get('city', 'Não informado'),
                neighborhood=prop_dict.get('neighborhood'),
                address=prop_dict.get('address'),
                description=prop_dict.get('description'),
                area_total=area,
                area_privativa=prop_dict.get('area_privativa'),
                evaluation_value=evaluated_price,
                first_auction_value=prop_dict.get('first_auction_value'),
                first_auction_date=prop_dict.get('first_auction_date'),
                second_auction_value=price,
                second_auction_date=auction_date,
                discount_percentage=discount,
                image_url=prop_dict.get('image_url'),
                auctioneer_id=prop_dict.get('auctioneer_id', source),
                source_url=prop_dict.get('url') or prop_dict.get('source_url', ''),
                accepts_financing=prop_dict.get('accepts_financing'),
                accepts_fgts=prop_dict.get('accepts_fgts'),
                accepts_installments=prop_dict.get('accepts_installments'),
                occupation_status=prop_dict.get('occupation_status'),
                pending_debts=prop_dict.get('pending_debts'),
                auctioneer_name=prop_dict.get('auctioneer_name', source),
                auctioneer_url=prop_dict.get('url') or prop_dict.get('auctioneer_url'),
                source=source,
                latitude=prop_dict.get('latitude'),
                longitude=prop_dict.get('longitude'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            return property_obj
            
        except Exception as e:
            logger.error(f"Erro ao converter dicionário para Property: {e}")
            return None
    
    async def _save_to_database(self, properties: List[Dict], source: str) -> int:
        """Salva imóveis no banco de dados após auditoria de qualidade"""
        auditor = get_quality_auditor()
        
        # Auditar todos os imóveis
        passed, failed, stats = auditor.audit_batch(properties)
        
        logger.info(f"Auditoria: {len(passed)} aprovados, {len(failed)} rejeitados")
        
        saved = 0
        
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                for prop_dict in passed:
                    try:
                        # Converter dicionário para Property
                        prop = self._dict_to_property(prop_dict, source)
                        if not prop:
                            self.stats["errors"] += 1
                            continue
                        
                        # Verificar se já existe (pelo external_id ou URL)
                        external_id = prop_dict.get('external_id') or prop_dict.get('url', '') or prop.id
                        
                        cur.execute("""
                            SELECT id FROM properties WHERE id = %s OR source_url = %s
                        """, (prop.id, prop.source_url))
                        
                        existing = cur.fetchone()
                        
                        if existing:
                            # Atualizar existente
                            cur.execute("""
                                UPDATE properties SET
                                    title = COALESCE(%s, title),
                                    description = COALESCE(%s, description),
                                    second_auction_value = COALESCE(%s, second_auction_value),
                                    evaluation_value = COALESCE(%s, evaluation_value),
                                    discount_percentage = COALESCE(%s, discount_percentage),
                                    address = COALESCE(%s, address),
                                    city = COALESCE(%s, city),
                                    state = COALESCE(%s, state),
                                    category = COALESCE(%s, category),
                                    area_total = COALESCE(%s, area_total),
                                    latitude = COALESCE(%s, latitude),
                                    longitude = COALESCE(%s, longitude),
                                    second_auction_date = COALESCE(%s, second_auction_date),
                                    image_url = COALESCE(%s, image_url),
                                    updated_at = NOW()
                                WHERE id = %s OR source_url = %s
                            """, (
                                prop.title,
                                prop.description,
                                prop.second_auction_value,
                                prop.evaluation_value,
                                prop.discount_percentage,
                                prop.address,
                                prop.city,
                                prop.state,
                                prop.category.value if prop.category else None,
                                prop.area_total,
                                prop.latitude,
                                prop.longitude,
                                prop.second_auction_date,
                                prop.image_url,
                                prop.id,
                                prop.source_url
                            ))
                        else:
                            # Inserir novo
                            cur.execute("""
                                INSERT INTO properties (
                                    id, title, description, second_auction_value, evaluation_value,
                                    discount_percentage, address, city, state, category, area_total,
                                    latitude, longitude, second_auction_date, image_url, source,
                                    auctioneer_id, source_url, auctioneer_name, auctioneer_url,
                                    created_at, updated_at
                                ) VALUES (
                                    %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s,
                                    NOW(), NOW()
                                )
                            """, (
                                prop.id,
                                prop.title,
                                prop.description,
                                prop.second_auction_value,
                                prop.evaluation_value,
                                prop.discount_percentage,
                                prop.address,
                                prop.city,
                                prop.state,
                                prop.category.value if prop.category else None,
                                prop.area_total,
                                prop.latitude,
                                prop.longitude,
                                prop.second_auction_date,
                                prop.image_url,
                                source,
                                prop.auctioneer_id,
                                prop.source_url,
                                prop.auctioneer_name,
                                prop.auctioneer_url,
                            ))
                        
                        saved += 1
                        
                    except Exception as e:
                        logger.error(f"Erro ao salvar imóvel: {e}")
                        self.stats["errors"] += 1
                
                conn.commit()
        
        # Atualizar estatísticas de auditoria
        self.stats["audit_passed"] = len(passed)
        self.stats["audit_failed"] = len(failed)
        
        return saved
    
    async def run_for_auctioneer(self, auctioneer_slug: str) -> Dict:
        """Executa pipeline para um leiloeiro específico"""
        
        # Aqui você integraria com o scraper existente
        # Por enquanto, retorna stats vazias
        logger.info(f"Iniciando scraping para leiloeiro: {auctioneer_slug}")
        
        # TODO: Integrar com o scraper existente
        # properties = await scraper.scrape_auctioneer(auctioneer_slug)
        # return await self.process_properties(properties, source=auctioneer_slug)
        
        return {"message": f"Scraper para {auctioneer_slug} não implementado ainda"}
    
    async def run_all_auctioneers(self) -> Dict:
        """Executa pipeline para todos os leiloeiros configurados"""
        
        # TODO: Obter lista de leiloeiros do banco ou configuração
        # auctioneers = get_configured_auctioneers()
        
        all_stats = {
            "total_extracted": 0,
            "total_normalized": 0,
            "total_geocoded": 0,
            "total_saved": 0,
            "total_errors": 0,
            "by_auctioneer": {}
        }
        
        logger.info("Iniciando scraping de todos os leiloeiros...")
        
        # TODO: Implementar loop pelos leiloeiros
        # for auctioneer in auctioneers:
        #     stats = await self.run_for_auctioneer(auctioneer['slug'])
        #     all_stats['by_auctioneer'][auctioneer['slug']] = stats
        #     all_stats['total_extracted'] += stats.get('extracted', 0)
        #     ...
        
        return all_stats


# Instância global
scraper_pipeline = ScraperPipeline()


