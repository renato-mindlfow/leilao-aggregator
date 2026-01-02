import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from app.services.universal_scraper import universal_scraper, parse_brazilian_date
from app.services.ai_normalizer import ai_normalizer
from app.services.geocoding_service import geocoding_service
from app.services.postgres_database import get_postgres_database

logger = logging.getLogger(__name__)
db = get_postgres_database()

class ScraperOrchestrator:
    """Orquestra o scraping de todos os leiloeiros"""
    
    def __init__(self):
        self.stats = {
            "started_at": None,
            "finished_at": None,
            "total_auctioneers": 0,
            "successful": 0,
            "failed": 0,
            "total_properties": 0,
            "new_properties": 0,
            "updated_properties": 0,
            "errors": []
        }
    
    async def run_all(self, skip_geocoding: bool = False, limit: Optional[int] = None) -> Dict:
        """Executa scraping de todos os leiloeiros ativos"""
        
        self.stats = {
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "total_auctioneers": 0,
            "successful": 0,
            "failed": 0,
            "total_properties": 0,
            "new_properties": 0,
            "updated_properties": 0,
            "errors": []
        }
        
        # Buscar leiloeiros ativos
        auctioneers = self._get_active_auctioneers(limit)
        self.stats["total_auctioneers"] = len(auctioneers)
        
        logger.info(f"Iniciando scraping de {len(auctioneers)} leiloeiros")
        
        for i, auctioneer in enumerate(auctioneers):
            name = auctioneer.get('name', 'Unknown')
            auctioneer_id = auctioneer.get('id')
            
            logger.info(f"[{i+1}/{len(auctioneers)}] Processando {name}...")
            
            try:
                # Scraping
                properties = await universal_scraper.scrape_auctioneer(auctioneer)
                
                if not properties:
                    self._update_auctioneer_status(auctioneer_id, 'error', 'Nenhum imóvel encontrado')
                    self.stats["failed"] += 1
                    continue
                
                # Normalização
                logger.info(f"Normalizando {len(properties)} imóveis de {name}...")
                normalized = await ai_normalizer.normalize_batch(properties)
                
                # Geocoding (opcional)
                if not skip_geocoding:
                    logger.info(f"Geocodificando {len(normalized)} imóveis de {name}...")
                    normalized = await geocoding_service.geocode_batch(normalized, delay=0.5)
                
                # Salvar no banco
                new_count, updated_count = self._save_properties(normalized, auctioneer_id, name)
                
                self.stats["total_properties"] += len(normalized)
                self.stats["new_properties"] += new_count
                self.stats["updated_properties"] += updated_count
                self.stats["successful"] += 1
                
                # Atualizar status do leiloeiro
                self._update_auctioneer_status(
                    auctioneer_id, 
                    'success', 
                    None, 
                    len(normalized)
                )
                
                logger.info(f"✓ {name}: {new_count} novos, {updated_count} atualizados")
                
                # Pequena pausa entre leiloeiros para não sobrecarregar
                await asyncio.sleep(2)
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"✗ Erro em {name}: {error_msg}")
                self.stats["failed"] += 1
                self.stats["errors"].append({"auctioneer": name, "error": error_msg})
                self._update_auctioneer_status(auctioneer_id, 'error', error_msg)
        
        self.stats["finished_at"] = datetime.now().isoformat()
        
        logger.info(f"Scraping finalizado: {self.stats['successful']} sucesso, {self.stats['failed']} falhas")
        
        return self.stats
    
    async def run_single(self, auctioneer_id: str, skip_geocoding: bool = False) -> Dict:
        """Executa scraping de um único leiloeiro"""
        
        auctioneer = self._get_auctioneer_by_id(auctioneer_id)
        
        if not auctioneer:
            return {"error": "Leiloeiro não encontrado"}
        
        name = auctioneer.get('name', 'Unknown')
        
        try:
            # Scraping
            properties = await universal_scraper.scrape_auctioneer(auctioneer)
            
            if not properties:
                self._update_auctioneer_status(auctioneer_id, 'error', 'Nenhum imóvel encontrado')
                return {"error": "Nenhum imóvel encontrado", "auctioneer": name}
            
            # Normalização
            normalized = await ai_normalizer.normalize_batch(properties)
            
            # Geocoding
            if not skip_geocoding:
                normalized = await geocoding_service.geocode_batch(normalized, delay=0.5)
            
            # Salvar
            new_count, updated_count = self._save_properties(normalized, auctioneer_id, name)
            
            self._update_auctioneer_status(auctioneer_id, 'success', None, len(normalized))
            
            return {
                "success": True,
                "auctioneer": name,
                "total": len(normalized),
                "new": new_count,
                "updated": updated_count
            }
            
        except Exception as e:
            error_msg = str(e)
            self._update_auctioneer_status(auctioneer_id, 'error', error_msg)
            return {"error": error_msg, "auctioneer": name}
    
    def _get_active_auctioneers(self, limit: Optional[int] = None) -> List[Dict]:
        """Busca leiloeiros ativos do banco"""
        
        query = """
            SELECT id, name, website, scrape_status, property_count
            FROM auctioneers
            WHERE is_active = true
            ORDER BY 
                CASE WHEN scrape_status = 'success' THEN 0 ELSE 1 END,
                property_count DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                # Rows are already dicts due to dict_row factory, so return directly
                return list(cur.fetchall())
    
    def _get_auctioneer_by_id(self, auctioneer_id: str) -> Optional[Dict]:
        """Busca um leiloeiro pelo ID"""
        
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, website, scrape_status
                    FROM auctioneers
                    WHERE id = %s
                """, (auctioneer_id,))
                row = cur.fetchone()
                if row:
                    # Row is already a dict due to dict_row factory, so return directly
                    return row
        return None
    
    def _update_auctioneer_status(
        self, 
        auctioneer_id: str, 
        status: str, 
        error: Optional[str] = None,
        property_count: Optional[int] = None
    ):
        """Atualiza status do leiloeiro"""
        
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                if property_count is not None:
                    cur.execute("""
                        UPDATE auctioneers SET
                            scrape_status = %s,
                            scrape_error = %s,
                            property_count = %s,
                            last_scrape = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                    """, (status, error, property_count, auctioneer_id))
                else:
                    cur.execute("""
                        UPDATE auctioneers SET
                            scrape_status = %s,
                            scrape_error = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (status, error, auctioneer_id))
            conn.commit()
    
    def _save_properties(self, properties: List[Dict], auctioneer_id: str, source: str) -> tuple:
        """Salva imóveis no banco com upsert"""
        
        new_count = 0
        updated_count = 0
        
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                for prop in properties:
                    # Usar external_id como id do banco, ou gerar um
                    external_id = prop.get('external_id', f"{source}_{hash(str(prop))}")
                    property_id = external_id
                    
                    # Mapear campos do scraper para o schema do banco
                    title = prop.get('title', 'Sem título')
                    description = prop.get('description', '')
                    category = prop.get('category', 'Outro')
                    state = prop.get('state', '')
                    city = prop.get('city', '')
                    address = prop.get('address', '')
                    area_total = prop.get('area')
                    evaluation_value = prop.get('evaluated_price')
                    first_auction_value = prop.get('price')
                    discount_percentage = prop.get('discount')
                    image_url = prop.get('image_url')
                    source_url = prop.get('url', '')
                    latitude = prop.get('latitude')
                    longitude = prop.get('longitude')
                    auction_date = prop.get('auction_date')
                    
                    # Converter datas brasileiras para formato PostgreSQL se necessário
                    if auction_date:
                        auction_date = parse_brazilian_date(auction_date)
                    
                    # Também verificar campos first_auction_date e second_auction_date diretamente
                    first_auction_date = prop.get('first_auction_date')
                    if first_auction_date:
                        first_auction_date = parse_brazilian_date(first_auction_date)
                    # Se não tiver first_auction_date mas tiver auction_date, usar auction_date
                    if not first_auction_date and auction_date:
                        first_auction_date = auction_date
                    
                    second_auction_date = prop.get('second_auction_date')
                    if second_auction_date:
                        second_auction_date = parse_brazilian_date(second_auction_date)
                    
                    # Verificar se já existe (usando source_url como chave alternativa)
                    if source_url:
                        cur.execute("""
                            SELECT id FROM properties WHERE source_url = %s
                        """, (source_url,))
                    else:
                        cur.execute("""
                            SELECT id FROM properties WHERE id = %s
                        """, (property_id,))
                    
                    existing = cur.fetchone()
                    
                    if existing:
                        # Atualizar
                        property_id = existing['id']
                        cur.execute("""
                            UPDATE properties SET
                                title = COALESCE(%s, title),
                                description = COALESCE(%s, description),
                                first_auction_value = COALESCE(%s, first_auction_value),
                                evaluation_value = COALESCE(%s, evaluation_value),
                                discount_percentage = COALESCE(%s, discount_percentage),
                                address = COALESCE(%s, address),
                                city = COALESCE(%s, city),
                                state = COALESCE(%s, state),
                                category = COALESCE(%s, category),
                                area_total = COALESCE(%s, area_total),
                                latitude = COALESCE(%s, latitude),
                                longitude = COALESCE(%s, longitude),
                                first_auction_date = COALESCE(%s, first_auction_date),
                                second_auction_date = COALESCE(%s, second_auction_date),
                                image_url = COALESCE(%s, image_url),
                                source_url = COALESCE(%s, source_url),
                                auctioneer_id = %s,
                                auctioneer_name = %s,
                                source = COALESCE(%s, source),
                                updated_at = NOW(),
                                last_seen_at = NOW()
                            WHERE id = %s
                        """, (
                            title,
                            description,
                            first_auction_value,
                            evaluation_value,
                            discount_percentage,
                            address,
                            city,
                            state,
                            category,
                            area_total,
                            latitude,
                            longitude,
                            first_auction_date,
                            second_auction_date,
                            image_url,
                            source_url,
                            auctioneer_id,
                            source,
                            prop.get('source', source),
                            property_id
                        ))
                        updated_count += 1
                    else:
                        # Inserir novo
                        cur.execute("""
                            INSERT INTO properties (
                                id, title, description, category, auction_type, state, city,
                                address, area_total, evaluation_value, first_auction_value,
                                discount_percentage, image_url, source_url, auctioneer_id,
                                auctioneer_name, source, latitude, longitude, first_auction_date, second_auction_date,
                                created_at, updated_at, last_seen_at, is_active
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s,
                                NOW(), NOW(), NOW(), TRUE
                            )
                        """, (
                            property_id,
                            title,
                            description,
                            category,
                            'judicial',  # Default auction type
                            state,
                            city,
                            address,
                            area_total,
                            evaluation_value,
                            first_auction_value,
                            discount_percentage,
                            image_url,
                            source_url,
                            auctioneer_id,
                            source,  # auctioneer_name
                            prop.get('source', source),  # source field
                            latitude,
                            longitude,
                            first_auction_date,
                            second_auction_date
                        ))
                        new_count += 1
                
                conn.commit()
        
        return new_count, updated_count


# Instância global
scraper_orchestrator = ScraperOrchestrator()

