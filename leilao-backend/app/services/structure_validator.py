"""
Structure Validator Service
Valida se a estrutura do site mudou e decide quando re-descobrir.
"""

import hashlib
import logging
import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import httpx
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


class StructureValidator:
    """Valida estrutura de sites e decide quando re-descobrir"""
    
    # Configurações de validação
    CONFIG_EXPIRY_DAYS = 30  # Config expira após 30 dias
    CONFIG_EXPIRY_DAYS_LARGE = 7  # Leiloeiros grandes: 7 dias
    LARGE_AUCTIONEER_THRESHOLD = 100  # >100 imóveis = grande
    MAX_CONSECUTIVE_FAILURES = 3  # Re-descoberta após 3 falhas
    MIN_SUCCESS_RATE = 0.5  # Taxa mínima de sucesso (50%)
    HASH_CHANGE_THRESHOLD = 0.3  # 30% de mudança = re-descoberta
    
    def __init__(self):
        pass
    
    def needs_rediscovery(self, auctioneer: Dict) -> Tuple[bool, str]:
        """
        Verifica se um leiloeiro precisa de re-descoberta.
        
        Args:
            auctioneer: Dict com dados do leiloeiro incluindo scrape_config
            
        Returns:
            Tuple (needs_rediscovery: bool, reason: str)
        """
        config = auctioneer.get("scrape_config")
        property_count = auctioneer.get("property_count", 0)
        validation_metrics = auctioneer.get("validation_metrics", {})
        
        # Parsear JSON se necessário
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except:
                config = None
        
        if isinstance(validation_metrics, str):
            try:
                validation_metrics = json.loads(validation_metrics)
            except:
                validation_metrics = {}
        
        # 1. Sem configuração = precisa descoberta
        if not config:
            return True, "no_config"
        
        # 2. Config expirada
        expires_at = config.get("expires_at")
        if expires_at:
            try:
                expiry_date = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.now(expiry_date.tzinfo) > expiry_date:
                    return True, "config_expired"
            except:
                pass
        
        # 3. Verificar por data de descoberta (fallback se não tiver expires_at)
        discovered_at = config.get("discovered_at")
        if discovered_at:
            try:
                discovery_date = datetime.fromisoformat(discovered_at.replace("Z", "+00:00"))
                days_since = (datetime.now(discovery_date.tzinfo) - discovery_date).days
                
                # Leiloeiros grandes expiram mais rápido
                expiry_days = self.CONFIG_EXPIRY_DAYS_LARGE if property_count > self.LARGE_AUCTIONEER_THRESHOLD else self.CONFIG_EXPIRY_DAYS
                
                if days_since > expiry_days:
                    return True, f"config_old_{days_since}_days"
            except:
                pass
        
        # 4. Muitas falhas consecutivas
        consecutive_failures = validation_metrics.get("consecutive_failures", 0)
        if consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            return True, f"consecutive_failures_{consecutive_failures}"
        
        # 5. Taxa de sucesso baixa
        total = validation_metrics.get("total_extractions", 0)
        successful = validation_metrics.get("successful_extractions", 0)
        if total >= 5:  # Mínimo 5 extrações para avaliar
            success_rate = successful / total
            if success_rate < self.MIN_SUCCESS_RATE:
                return True, f"low_success_rate_{success_rate:.0%}"
        
        # 6. Discovery status indica necessidade
        if auctioneer.get("discovery_status") == "needs_rediscovery":
            return True, "marked_for_rediscovery"
        
        return False, "config_valid"
    
    async def check_structure_changed(self, website: str, stored_hash: Optional[str]) -> Tuple[bool, str]:
        """
        Verifica se a estrutura do site mudou comparando hashes.
        
        Args:
            website: URL do site
            stored_hash: Hash armazenado da última descoberta
            
        Returns:
            Tuple (changed: bool, new_hash: str)
        """
        if not stored_hash:
            return True, ""
        
        try:
            # Baixar homepage
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(website, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                
                if response.status_code != 200:
                    return False, stored_hash  # Não conseguiu verificar, manter atual
                
                html = response.text
            
            # Extrair estrutura relevante (links de navegação, menus, filtros)
            structure = self._extract_structure_signature(html)
            
            # Calcular hash da estrutura
            new_hash = hashlib.md5(structure.encode()).hexdigest()
            
            # Comparar
            if new_hash != stored_hash:
                # Calcular diferença (simplificado)
                logger.info(f"Hash mudou: {stored_hash[:8]}... -> {new_hash[:8]}...")
                return True, new_hash
            
            return False, new_hash
            
        except Exception as e:
            logger.warning(f"Erro ao verificar estrutura: {e}")
            return False, stored_hash or ""
    
    def _extract_structure_signature(self, html: str) -> str:
        """
        Extrai uma "assinatura" da estrutura do site.
        Foca em elementos de navegação que indicam a estrutura.
        """
        # Extrair links de navegação (menus, filtros)
        nav_links = re.findall(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>', html, re.IGNORECASE)
        
        # Filtrar apenas links internos relevantes
        relevant_patterns = ['imovel', 'imoveis', 'lote', 'lotes', 'busca', 'catalogo', 
                           'categoria', 'filtro', 'tipo', 'apartamento', 'casa', 'terreno']
        
        relevant_links = []
        for link in nav_links:
            link_lower = link.lower()
            if any(p in link_lower for p in relevant_patterns):
                relevant_links.append(link)
        
        # Extrair classes de containers principais
        main_classes = re.findall(r'class=["\']([^"\']*(?:lista|grid|cards|imoveis|lotes)[^"\']*)["\']', 
                                  html, re.IGNORECASE)
        
        # Combinar em uma string para hash
        signature = "|".join(sorted(set(relevant_links[:50]))) + "||" + "|".join(sorted(set(main_classes[:20])))
        
        return signature
    
    def update_validation_metrics(self, auctioneer_id: str, success: bool, properties_count: int):
        """
        Atualiza métricas de validação após uma extração.
        
        Args:
            auctioneer_id: ID do leiloeiro
            success: Se a extração foi bem-sucedida
            properties_count: Número de imóveis extraídos
        """
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL não configurada")
            return
        
        conn = psycopg.connect(database_url, row_factory=dict_row)
        conn.autocommit = True
        
        try:
            with conn.cursor() as cur:
                # Buscar métricas atuais
                cur.execute(
                    "SELECT validation_metrics, scrape_config FROM auctioneers WHERE id = %s",
                    (auctioneer_id,)
                )
                row = cur.fetchone()
                
                # row é um dict devido ao dict_row factory
                metrics = row.get('validation_metrics') if row else None
                if not metrics:
                    metrics = {
                        "consecutive_failures": 0,
                        "total_extractions": 0,
                        "successful_extractions": 0,
                        "avg_properties_per_extraction": 0
                    }
                
                config = row.get('scrape_config') if row else {}
                
                # Parsear JSON se necessário
                if isinstance(metrics, str):
                    try:
                        metrics = json.loads(metrics)
                    except:
                        metrics = {
                            "consecutive_failures": 0,
                            "total_extractions": 0,
                            "successful_extractions": 0,
                            "avg_properties_per_extraction": 0
                        }
                
                if isinstance(config, str):
                    try:
                        config = json.loads(config)
                    except:
                        config = {}
                
                # Atualizar métricas
                metrics["total_extractions"] = metrics.get("total_extractions", 0) + 1
                
                if success and properties_count > 0:
                    metrics["successful_extractions"] = metrics.get("successful_extractions", 0) + 1
                    metrics["consecutive_failures"] = 0
                    
                    # Atualizar média de imóveis
                    total_successful = metrics["successful_extractions"]
                    current_avg = metrics.get("avg_properties_per_extraction", 0)
                    metrics["avg_properties_per_extraction"] = (
                        (current_avg * (total_successful - 1) + properties_count) / total_successful
                    )
                else:
                    metrics["consecutive_failures"] = metrics.get("consecutive_failures", 0) + 1
                
                metrics["last_extraction_at"] = datetime.utcnow().isoformat() + "Z"
                
                # Atualizar também no config.validation se existir
                if config:
                    if "validation" not in config:
                        config["validation"] = {}
                    config["validation"]["last_validated_at"] = datetime.utcnow().isoformat() + "Z"
                    config["validation"]["consecutive_failures"] = metrics["consecutive_failures"]
                    config["validation"]["total_extractions"] = metrics["total_extractions"]
                    config["validation"]["successful_extractions"] = metrics["successful_extractions"]
                
                # Verificar se precisa marcar para re-descoberta
                needs_rediscovery = False
                if metrics["consecutive_failures"] >= self.MAX_CONSECUTIVE_FAILURES:
                    needs_rediscovery = True
                    logger.warning(f"Leiloeiro {auctioneer_id} marcado para re-descoberta (falhas consecutivas)")
                
                # Salvar
                cur.execute("""
                    UPDATE auctioneers SET
                        validation_metrics = %s,
                        scrape_config = %s,
                        discovery_status = CASE WHEN %s THEN 'needs_rediscovery' ELSE discovery_status END,
                        updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(metrics), json.dumps(config) if config else None, needs_rediscovery, auctioneer_id))
                
        finally:
            conn.close()
    
    def calculate_config_expiry(self, property_count: int) -> str:
        """Calcula data de expiração baseada no tamanho do leiloeiro"""
        
        if property_count > self.LARGE_AUCTIONEER_THRESHOLD:
            days = self.CONFIG_EXPIRY_DAYS_LARGE
        else:
            days = self.CONFIG_EXPIRY_DAYS
        
        expiry = datetime.utcnow() + timedelta(days=days)
        return expiry.isoformat() + "Z"


# Instância global
structure_validator = StructureValidator()

