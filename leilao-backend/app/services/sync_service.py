"""
Serviço de sincronização de dados.

Responsável por:
1. Coordenar scraping de múltiplas fontes
2. Aplicar deduplicação
3. Atualizar/inserir dados no banco
4. Gerar relatórios de execução
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import os

from supabase import create_client, Client

from app.scrapers.caixa_scraper import scrape_caixa
from app.scrapers.generic_scraper import GenericScraper
from app.utils.normalizer import normalize_category, normalize_state, normalize_city

logger = logging.getLogger(__name__)

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

@dataclass
class SyncReport:
    """Relatório de sincronização."""
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Contadores
    total_scraped: int = 0
    total_inserted: int = 0
    total_updated: int = 0
    total_skipped: int = 0
    total_errors: int = 0
    
    # Por fonte
    by_source: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Erros
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': (self.end_time - self.start_time).total_seconds() if self.end_time else None,
            'total_scraped': self.total_scraped,
            'total_inserted': self.total_inserted,
            'total_updated': self.total_updated,
            'total_skipped': self.total_skipped,
            'total_errors': self.total_errors,
            'by_source': self.by_source,
            'errors': self.errors[:10],  # Limita a 10 erros
        }


class SyncService:
    """
    Serviço de sincronização de dados de múltiplas fontes.
    """
    
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL e SUPABASE_KEY são obrigatórios")
        
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.generic_scraper = GenericScraper()
    
    async def sync_all(
        self,
        include_caixa: bool = True,
        include_auctioneers: bool = True,
        auctioneer_limit: Optional[int] = None
    ) -> SyncReport:
        """
        Sincroniza dados de todas as fontes.
        
        Args:
            include_caixa: Se True, inclui dados da Caixa
            include_auctioneers: Se True, inclui dados dos leiloeiros
            auctioneer_limit: Limite de leiloeiros a processar (None = todos)
            
        Returns:
            Relatório de sincronização
        """
        report = SyncReport(start_time=datetime.utcnow())
        
        try:
            # 1. Sincroniza Caixa (prioridade máxima)
            if include_caixa:
                await self._sync_caixa(report)
            
            # 2. Sincroniza leiloeiros
            if include_auctioneers:
                await self._sync_auctioneers(report, limit=auctioneer_limit)
            
            # 3. Aplica deduplicação global
            await self._deduplicate(report)
            
            # 4. Desativa imóveis antigos
            await self._deactivate_old_properties(report)
            
        except Exception as e:
            logger.error(f"Erro crítico na sincronização: {e}")
            report.errors.append(f"Erro crítico: {str(e)}")
            report.total_errors += 1
        
        report.end_time = datetime.utcnow()
        
        logger.info(f"Sincronização concluída: {report.to_dict()}")
        
        return report
    
    async def sync_caixa_only(self) -> SyncReport:
        """
        Sincroniza apenas dados da Caixa.
        """
        report = SyncReport(start_time=datetime.utcnow())
        
        await self._sync_caixa(report)
        
        report.end_time = datetime.utcnow()
        return report
    
    async def _sync_caixa(self, report: SyncReport):
        """
        Sincroniza dados da Caixa.
        """
        logger.info("Iniciando sincronização da Caixa")
        
        source_stats = {'scraped': 0, 'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        try:
            # Scrape
            properties = await scrape_caixa()
            source_stats['scraped'] = len(properties)
            report.total_scraped += len(properties)
            
            logger.info(f"Caixa: {len(properties)} imóveis extraídos")
            
            # Upsert no banco
            for prop in properties:
                try:
                    result = await self._upsert_property(prop, source='caixa')
                    
                    if result == 'inserted':
                        source_stats['inserted'] += 1
                        report.total_inserted += 1
                    elif result == 'updated':
                        source_stats['updated'] += 1
                        report.total_updated += 1
                    else:
                        source_stats['skipped'] += 1
                        report.total_skipped += 1
                        
                except Exception as e:
                    source_stats['errors'] += 1
                    report.total_errors += 1
                    report.errors.append(f"Caixa {prop.get('id')}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar Caixa: {e}")
            report.errors.append(f"Caixa: {str(e)}")
            report.total_errors += 1
        
        report.by_source['caixa'] = source_stats
        logger.info(f"Caixa sincronizada: {source_stats}")
    
    async def _sync_auctioneers(self, report: SyncReport, limit: Optional[int] = None):
        """
        Sincroniza dados dos leiloeiros.
        """
        logger.info("Iniciando sincronização de leiloeiros")
        
        # Busca leiloeiros ativos
        response = self.supabase.table('auctioneers') \
            .select('id, name, website') \
            .eq('is_active', True) \
            .execute()
        
        auctioneers = response.data or []
        
        if limit:
            auctioneers = auctioneers[:limit]
        
        logger.info(f"Processando {len(auctioneers)} leiloeiros")
        
        for auctioneer in auctioneers:
            auctioneer_id = auctioneer['id']
            website = auctioneer.get('website')
            
            if not website:
                continue
            
            source_stats = {'scraped': 0, 'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
            
            try:
                # Scrape do leiloeiro
                properties = await self.generic_scraper.scrape(website, use_pagination=True)
                source_stats['scraped'] = len(properties)
                report.total_scraped += len(properties)
                
                logger.info(f"{auctioneer['name']}: {len(properties)} imóveis")
                
                # Upsert no banco
                for prop in properties:
                    try:
                        # Adiciona referência ao leiloeiro
                        prop['auctioneer_id'] = auctioneer_id
                        prop['auctioneer_name'] = auctioneer['name']
                        prop['source'] = 'leiloeiro'
                        
                        result = await self._upsert_property(prop, source='leiloeiro')
                        
                        if result == 'inserted':
                            source_stats['inserted'] += 1
                            report.total_inserted += 1
                        elif result == 'updated':
                            source_stats['updated'] += 1
                            report.total_updated += 1
                        else:
                            source_stats['skipped'] += 1
                            report.total_skipped += 1
                            
                    except Exception as e:
                        source_stats['errors'] += 1
                        report.total_errors += 1
                
                # Atualiza status do leiloeiro
                self.supabase.table('auctioneers').update({
                    'scrape_status': 'success',
                    'last_scrape': datetime.utcnow().isoformat(),
                    'property_count': source_stats['scraped'],
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', auctioneer_id).execute()
                
            except Exception as e:
                logger.error(f"Erro no leiloeiro {auctioneer['name']}: {e}")
                source_stats['errors'] += 1
                report.total_errors += 1
                
                # Atualiza status de erro
                self.supabase.table('auctioneers').update({
                    'scrape_status': 'error',
                    'scrape_error': str(e)[:500],
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', auctioneer_id).execute()
            
            report.by_source[auctioneer_id] = source_stats
    
    async def _upsert_property(self, prop: Dict[str, Any], source: str) -> str:
        """
        Insere ou atualiza um imóvel.
        
        Returns:
            'inserted', 'updated', ou 'skipped'
        """
        # TODO: Implementar Layer de Auditoria de Qualidade IA antes do commit final
        # Ver documentação: ESTRATEGIA_AUDITORIA_QUALIDADE_IA.md
        # Validações necessárias:
        # - Datas de leilão lógicas e cronológicas
        # - Valores de 1ª e 2ª praça respeitando regra de desconto
        # - Campo 'Estado' não pode ser 'XX' ou inválido
        
        prop_id = prop.get('id')
        
        if not prop_id:
            return 'skipped'
        
        # Garante que campos obrigatórios existem
        if not prop.get('title'):
            prop['title'] = 'Imóvel sem título'
        if not prop.get('category'):
            prop['category'] = 'Outros'
        if not prop.get('auction_type'):
            prop['auction_type'] = 'Outros'
        if not prop.get('state'):
            return 'skipped'  # Estado é obrigatório
        if not prop.get('city'):
            prop['city'] = 'Não informado'
        if not prop.get('source_url'):
            prop['source_url'] = ''
        if not prop.get('auctioneer_id'):
            prop['auctioneer_id'] = source
        
        # Verifica se já existe
        existing = self.supabase.table('properties') \
            .select('id, source, updated_at') \
            .eq('id', prop_id) \
            .execute()
        
        if existing.data:
            existing_record = existing.data[0]
            
            # Caixa tem prioridade - não sobrescreve dados da Caixa
            if existing_record.get('source') == 'caixa' and source != 'caixa':
                return 'skipped'
            
            # Atualiza
            prop['updated_at'] = datetime.utcnow().isoformat()
            self.supabase.table('properties').update(prop).eq('id', prop_id).execute()
            return 'updated'
        
        else:
            # Insere novo
            prop['created_at'] = datetime.utcnow().isoformat()
            prop['updated_at'] = datetime.utcnow().isoformat()
            self.supabase.table('properties').insert(prop).execute()
            return 'inserted'
    
    async def _deduplicate(self, report: SyncReport):
        """
        Aplica deduplicação baseada em endereço e características.
        """
        logger.info("Iniciando deduplicação")
        
        # A deduplicação é feita através da coluna dedup_key
        # Propriedades com a mesma dedup_key são consideradas duplicatas
        # A Caixa sempre tem prioridade
        
        # Busca propriedades sem dedup_key
        response = self.supabase.table('properties') \
            .select('id, state, city, address, first_auction_value') \
            .is_('dedup_key', 'null') \
            .limit(1000) \
            .execute()
        
        for prop in response.data or []:
            # Gera dedup_key
            dedup_key = self._generate_dedup_key(prop)
            
            if dedup_key:
                self.supabase.table('properties').update({
                    'dedup_key': dedup_key
                }).eq('id', prop['id']).execute()
        
        logger.info("Deduplicação concluída")
    
    def _generate_dedup_key(self, prop: Dict[str, Any]) -> Optional[str]:
        """
        Gera chave de deduplicação baseada em características do imóvel.
        """
        parts = []
        
        if prop.get('state'):
            parts.append(prop['state'].upper())
        
        if prop.get('city'):
            # Normaliza cidade removendo acentos e espaços
            city = prop['city'].lower().replace(' ', '')
            parts.append(city[:20])
        
        if prop.get('address'):
            # Normaliza endereço
            address = prop['address'].lower()
            # Remove números de apartamento/bloco
            address = re.sub(r'(apt|apto|bloco|bl|sala|sl|loja)[\s\.\-]*\d+', '', address)
            # Pega primeiras palavras significativas
            words = [w for w in address.split() if len(w) > 2][:5]
            parts.append(''.join(words)[:30])
        
        if not parts:
            return None
        
        return '_'.join(parts)
    
    async def _deactivate_old_properties(self, report: SyncReport):
        """
        Desativa imóveis que não foram atualizados recentemente.
        """
        logger.info("Desativando imóveis antigos")
        
        # Imóveis não atualizados há mais de 7 dias são desativados
        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
        
        self.supabase.table('properties').update({
            'is_active': False,
            'deactivated_at': datetime.utcnow().isoformat()
        }).lt('updated_at', cutoff).eq('is_active', True).execute()
        
        logger.info("Imóveis antigos desativados")


# Instância global
_sync_service: Optional[SyncService] = None

def get_sync_service() -> SyncService:
    """Obtém a instância global do serviço de sincronização."""
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncService()
    return _sync_service


async def run_full_sync() -> Dict[str, Any]:
    """
    Executa sincronização completa.
    
    Função de conveniência para uso em scripts/cron.
    """
    service = get_sync_service()
    report = await service.sync_all()
    return report.to_dict()

