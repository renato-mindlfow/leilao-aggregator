"""
Discovery Orchestrator
Gerencia o processo de descoberta de estrutura para todos os leiloeiros.
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import psycopg
from psycopg.rows import dict_row

from .site_discovery import site_discovery
from .structure_validator import structure_validator

logger = logging.getLogger(__name__)


class DiscoveryOrchestrator:
    """Orquestra o processo de descoberta de estrutura dos sites"""
    
    def __init__(self):
        self.database_url = os.environ.get("DATABASE_URL")
    
    def _get_connection(self):
        """Cria conexão isolada com o banco"""
        conn = psycopg.connect(self.database_url, row_factory=dict_row)
        conn.autocommit = True
        return conn
    
    async def run_discovery(self, limit: Optional[int] = None, force: bool = False) -> Dict:
        """
        Executa descoberta para leiloeiros pendentes.
        
        Args:
            limit: Número máximo de leiloeiros para processar
            force: Se True, reprocessa mesmo os já descobertos
            
        Returns:
            Dict com estatísticas da execução
        """
        stats = {
            "started_at": datetime.now().isoformat(),
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        # Buscar leiloeiros para descoberta
        auctioneers = self._get_pending_auctioneers(limit, force)
        stats["total"] = len(auctioneers)
        
        logger.info(f"🔍 Iniciando descoberta para {len(auctioneers)} leiloeiros")
        
        for i, auctioneer in enumerate(auctioneers, 1):
            auc_id = auctioneer["id"]
            auc_name = auctioneer["name"]
            
            logger.info(f"[{i}/{len(auctioneers)}] Descobrindo {auc_name}...")
            
            try:
                # Executar descoberta
                result = await site_discovery.discover_site_structure(auctioneer)
                
                if result.get("success"):
                    # Salvar configuração
                    self._save_config(auc_id, result["config"])
                    stats["success"] += 1
                    logger.info(f"✅ {auc_name}: {result['config'].get('site_type')}")
                else:
                    # Marcar como falha
                    self._mark_failed(auc_id, result.get("error", "Unknown error"))
                    stats["failed"] += 1
                    stats["errors"].append({"name": auc_name, "error": result.get("error")})
                    logger.warning(f"❌ {auc_name}: {result.get('error')}")
                    
            except Exception as e:
                self._mark_failed(auc_id, str(e))
                stats["failed"] += 1
                stats["errors"].append({"name": auc_name, "error": str(e)})
                logger.error(f"❌ {auc_name}: {e}")
        
        stats["finished_at"] = datetime.now().isoformat()
        
        logger.info(f"🏁 Descoberta finalizada: {stats['success']} sucesso, {stats['failed']} falhas")
        
        return stats
    
    async def run_single_discovery(self, auctioneer_id: str) -> Dict:
        """Executa descoberta para um único leiloeiro"""
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, website FROM auctioneers WHERE id = %s",
                    (auctioneer_id,)
                )
                auctioneer = cur.fetchone()
        finally:
            conn.close()
        
        if not auctioneer:
            return {"success": False, "error": "Leiloeiro não encontrado"}
        
        result = await site_discovery.discover_site_structure(dict(auctioneer))
        
        if result.get("success"):
            self._save_config(auctioneer_id, result["config"])
        else:
            self._mark_failed(auctioneer_id, result.get("error", "Unknown"))
        
        return result
    
    async def run_rediscovery(self, limit: Optional[int] = None) -> Dict:
        """
        Executa re-descoberta para leiloeiros que precisam atualização.
        Verifica: config expirada, falhas consecutivas, estrutura mudou.
        """
        stats = {
            "started_at": datetime.now().isoformat(),
            "checked": 0,
            "needs_rediscovery": 0,
            "rediscovered": 0,
            "failed": 0,
            "reasons": {}
        }
        
        # Buscar todos com config (para verificar se precisam atualizar)
        auctioneers = self._get_auctioneers_for_validation(limit)
        stats["checked"] = len(auctioneers)
        
        logger.info(f"🔍 Verificando {len(auctioneers)} leiloeiros para re-descoberta")
        
        for auctioneer in auctioneers:
            needs, reason = structure_validator.needs_rediscovery(auctioneer)
            
            if needs:
                stats["needs_rediscovery"] += 1
                stats["reasons"][reason] = stats["reasons"].get(reason, 0) + 1
                
                logger.info(f"Re-descobrindo {auctioneer['name']} ({reason})")
                
                # Executar re-descoberta
                result = await site_discovery.discover_site_structure(auctioneer)
                
                if result.get("success"):
                    self._save_config(auctioneer["id"], result["config"])
                    stats["rediscovered"] += 1
                else:
                    self._mark_failed(auctioneer["id"], result.get("error", "Unknown"))
                    stats["failed"] += 1
        
        stats["finished_at"] = datetime.now().isoformat()
        
        logger.info(f"🏁 Re-descoberta: {stats['rediscovered']} atualizados, {stats['failed']} falhas")
        
        return stats
    
    def _get_pending_auctioneers(self, limit: Optional[int], force: bool) -> List[Dict]:
        """Busca leiloeiros que precisam de descoberta"""
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if force:
                    query = """
                        SELECT id, name, website 
                        FROM auctioneers 
                        WHERE website IS NOT NULL AND website != ''
                        ORDER BY property_count DESC NULLS LAST
                    """
                else:
                    query = """
                        SELECT id, name, website 
                        FROM auctioneers 
                        WHERE website IS NOT NULL AND website != ''
                        AND (discovery_status = 'pending' OR discovery_status IS NULL)
                        ORDER BY property_count DESC NULLS LAST
                    """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cur.execute(query)
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()
    
    def _get_auctioneers_for_validation(self, limit: Optional[int]) -> List[Dict]:
        """Busca leiloeiros que podem precisar de re-descoberta"""
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT id, name, website, scrape_config, property_count, 
                           validation_metrics, discovery_status
                    FROM auctioneers 
                    WHERE website IS NOT NULL AND website != ''
                    AND (
                        -- Sem config
                        scrape_config IS NULL
                        -- Ou marcado para re-descoberta
                        OR discovery_status = 'needs_rediscovery'
                        -- Ou config antiga (>30 dias)
                        OR last_discovery_at < NOW() - INTERVAL '30 days'
                        OR last_discovery_at IS NULL
                        -- Ou muitas falhas consecutivas
                        OR (validation_metrics->>'consecutive_failures')::int >= 3
                    )
                    ORDER BY property_count DESC NULLS LAST
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cur.execute(query)
                
                results = []
                for row in cur.fetchall():
                    auc = dict(row)
                    # Parsear JSON se necessário
                    if auc.get("scrape_config") and isinstance(auc["scrape_config"], str):
                        try:
                            auc["scrape_config"] = json.loads(auc["scrape_config"])
                        except:
                            auc["scrape_config"] = None
                    if auc.get("validation_metrics") and isinstance(auc["validation_metrics"], str):
                        try:
                            auc["validation_metrics"] = json.loads(auc["validation_metrics"])
                        except:
                            auc["validation_metrics"] = {}
                    results.append(auc)
                
                return results
        finally:
            conn.close()
    
    def _save_config(self, auctioneer_id: str, config: Dict):
        """Salva configuração descoberta no banco"""
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Extrair hash da estrutura se existir
                structure_hash = None
                if config.get("validation") and config["validation"].get("structure_hash"):
                    structure_hash = config["validation"]["structure_hash"]
                
                cur.execute("""
                    UPDATE auctioneers SET
                        scrape_config = %s,
                        discovery_status = 'completed',
                        last_discovery_at = NOW(),
                        structure_hash = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(config), structure_hash, auctioneer_id))
        finally:
            conn.close()
    
    def _mark_failed(self, auctioneer_id: str, error: str):
        """Marca leiloeiro como falha na descoberta"""
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE auctioneers SET
                        discovery_status = 'failed',
                        scrape_error = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (f"Discovery failed: {error}", auctioneer_id))
        finally:
            conn.close()
    
    def get_discovery_stats(self) -> Dict:
        """Retorna estatísticas de descoberta"""
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COALESCE(discovery_status, 'pending') as discovery_status,
                        COUNT(*) as count
                    FROM auctioneers
                    GROUP BY discovery_status
                """)
                
                stats = {row["discovery_status"]: row["count"] for row in cur.fetchall()}
                
                # Site types
                cur.execute("""
                    SELECT 
                        scrape_config->>'site_type' as site_type,
                        COUNT(*) as count
                    FROM auctioneers
                    WHERE scrape_config IS NOT NULL
                    GROUP BY scrape_config->>'site_type'
                """)
                
                site_types = {row["site_type"]: row["count"] for row in cur.fetchall() if row["site_type"]}
                
                return {
                    "discovery_status": stats,
                    "site_types": site_types
                }
        finally:
            conn.close()


# Instância global
discovery_orchestrator = DiscoveryOrchestrator()

