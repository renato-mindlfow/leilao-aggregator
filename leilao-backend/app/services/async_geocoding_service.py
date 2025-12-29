"""
Serviço de Geocoding Assíncrono.

Este serviço processa geocoding em background, sem bloquear requisições HTTP.

Estratégia:
1. Imóveis são salvos com geocoding_status='pending'
2. Um job em background processa em lotes de 50
3. Rate limiting de 1 req/segundo (limite do Nominatim)
4. Retry automático com backoff exponencial
"""

import asyncio
import logging
import os
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass
import httpx

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Configuração
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

# Nominatim (OpenStreetMap) - GRATUITO
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Configurações de rate limiting
REQUESTS_PER_SECOND = 1  # Limite do Nominatim
BATCH_SIZE = 50  # Imóveis por lote
MAX_RETRIES = 3  # Tentativas por imóvel
RETRY_DELAY = 5  # Segundos entre retries

# Padrões que indicam endereço inválido
ENDERECO_BLACKLIST = [
    'ENTRE EM CONTATO',
    'WHATSAPP',
    'WWW.',
    '.COM.BR',
    'DENTRE OUTRAS',
    'MAIS INFORMAÇÕES',
    'GRUPOLANCE',
]

# Endereços de escritórios conhecidos (não são imóveis)
ESCRITORIOS_LEILOEIROS = [
    'rua serra de botucatu, 880',
    'sala 1208, vila gomes cardim',
]

@dataclass
class GeocodingResult:
    """Resultado de uma operação de geocoding."""
    success: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    error: Optional[str] = None
    source: str = "nominatim"
    status: Optional[str] = None  # 'invalid_address' para endereços inválidos


def validar_endereco_para_geocoding(endereco: str) -> tuple[bool, str]:
    """
    Valida se endereço é adequado para geocoding.
    Retorna (is_valid, motivo_se_invalido)
    """
    if not endereco or len(endereco.strip()) < 10:
        return False, "Endereço muito curto ou vazio"
    
    endereco_upper = endereco.upper()
    
    # Verificar blacklist
    for pattern in ENDERECO_BLACKLIST:
        if pattern in endereco_upper:
            return False, f"Contém texto promocional: {pattern}"
    
    # Verificar escritórios de leiloeiros
    endereco_lower = endereco.lower()
    for escritorio in ESCRITORIOS_LEILOEIROS:
        if escritorio in endereco_lower:
            return False, "Endereço de escritório de leiloeiro"
    
    return True, ""


def limpar_endereco(endereco: str) -> str:
    """
    Limpa formato do endereço antes de enviar ao Nominatim.
    """
    # Remover " - - -" e variações
    endereco = re.sub(r'\s*-\s*-\s*-\s*', ' ', endereco)
    
    # Remover "/UF" no final (ex: /SP, /RJ)
    endereco = re.sub(r'\s*/[A-Z]{2}\s*$', '', endereco)
    
    # Remover CEP do meio do texto (já vai no query)
    endereco = re.sub(r'\s*-?\s*CEP:?\s*[\d.-]+', '', endereco)
    
    # Remover espaços múltiplos
    endereco = re.sub(r'\s+', ' ', endereco).strip()
    
    return endereco


class AsyncGeocodingService:
    """
    Serviço de geocoding assíncrono usando Nominatim (OpenStreetMap).
    
    Características:
    - Rate limiting automático (1 req/segundo)
    - Processamento em lotes
    - Retry com backoff exponencial
    - Não bloqueia requisições HTTP
    """
    
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL e SUPABASE_KEY são obrigatórios")
        
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self._is_processing = False
        self._last_request_time = 0
    
    async def geocode_address(self, address: str, city: str, state: str) -> GeocodingResult:
        """
        Geocodifica um endereço usando Nominatim.
        
        Args:
            address: Endereço (rua, número)
            city: Cidade
            state: Estado (sigla)
            
        Returns:
            GeocodingResult com coordenadas ou erro
        """
        # VALIDAR ANTES DE CHAMAR API
        is_valid, motivo = validar_endereco_para_geocoding(address)
        if not is_valid:
            logger.warning(f"Endereço inválido para geocoding: {motivo}")
            return GeocodingResult(
                success=False,
                status='invalid_address',
                error=motivo
            )
        
        # LIMPAR ENDEREÇO
        address_limpo = limpar_endereco(address)
        
        # Monta query de busca
        query_parts = []
        if address_limpo:
            query_parts.append(address_limpo)
        if city:
            query_parts.append(city)
        if state:
            query_parts.append(state)
        query_parts.append("Brasil")
        
        query = ", ".join(filter(None, query_parts))
        
        if not query or query == "Brasil":
            return GeocodingResult(success=False, error="Endereço vazio")
        
        # Rate limiting
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "br",
                    "addressdetails": 1
                }
                
                headers = {
                    "User-Agent": "LeiloHub/1.0 (https://leilohub.com.br)"
                }
                
                response = await client.get(NOMINATIM_URL, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data and len(data) > 0:
                        result = data[0]
                        return GeocodingResult(
                            success=True,
                            latitude=float(result["lat"]),
                            longitude=float(result["lon"]),
                            source="nominatim"
                        )
                    else:
                        return GeocodingResult(success=False, error="Endereço não encontrado")
                
                elif response.status_code == 429:
                    return GeocodingResult(success=False, error="Rate limit exceeded")
                
                else:
                    return GeocodingResult(
                        success=False, 
                        error=f"HTTP {response.status_code}"
                    )
                    
        except Exception as e:
            logger.error(f"Erro no geocoding: {e}")
            return GeocodingResult(success=False, error=str(e))
    
    async def _rate_limit(self):
        """Aplica rate limiting de 1 requisição por segundo."""
        import time
        
        now = time.time()
        elapsed = now - self._last_request_time
        
        if elapsed < 1.0 / REQUESTS_PER_SECOND:
            wait_time = (1.0 / REQUESTS_PER_SECOND) - elapsed
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    async def process_pending_batch(self, batch_size: int = BATCH_SIZE) -> Dict[str, int]:
        """
        Processa um lote de imóveis pendentes de geocoding.
        
        Args:
            batch_size: Número de imóveis a processar
            
        Returns:
            Estatísticas do processamento
        """
        stats = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0
        }
        
        # Busca imóveis pendentes
        response = self.supabase.table("properties") \
            .select("id, address, city, state, neighborhood, geocoding_attempts") \
            .eq("geocoding_status", "pending") \
            .lt("geocoding_attempts", MAX_RETRIES) \
            .limit(batch_size) \
            .execute()
        
        properties = response.data or []
        
        if not properties:
            logger.info("Nenhum imóvel pendente de geocoding")
            return stats
        
        logger.info(f"Processando {len(properties)} imóveis para geocoding")
        
        for prop in properties:
            stats["processed"] += 1
            
            # Monta endereço completo
            address = prop.get("address", "")
            neighborhood = prop.get("neighborhood", "")
            city = prop.get("city", "")
            state = prop.get("state", "")
            
            # Se não tem endereço suficiente, pula
            if not city and not address:
                self._update_property_geocoding(
                    prop["id"], 
                    status="skipped",
                    error="Endereço insuficiente"
                )
                stats["skipped"] += 1
                continue
            
            # Tenta geocodificar
            full_address = f"{address}, {neighborhood}".strip(", ") if neighborhood else address
            result = await self.geocode_address(full_address, city, state)
            
            if result.success:
                self._update_property_geocoding(
                    prop["id"],
                    status="done",
                    latitude=result.latitude,
                    longitude=result.longitude
                )
                stats["success"] += 1
                logger.debug(f"Geocoding OK: {prop['id']} -> {result.latitude}, {result.longitude}")
            elif result.status == 'invalid_address':
                # Marca como inválido imediatamente (não tenta retry)
                self._update_property_geocoding(
                    prop["id"],
                    status="invalid_address",
                    error=result.error
                )
                stats["skipped"] += 1
                logger.debug(f"Endereço inválido: {prop['id']} - {result.error}")
            else:
                attempts = prop.get("geocoding_attempts", 0) + 1
                
                if attempts >= MAX_RETRIES:
                    status = "failed"
                else:
                    status = "pending"  # Mantém pendente para retry
                
                self._update_property_geocoding(
                    prop["id"],
                    status=status,
                    error=result.error,
                    attempts=attempts
                )
                stats["failed"] += 1
                logger.debug(f"Geocoding falhou: {prop['id']} - {result.error}")
        
        logger.info(f"Geocoding batch: {stats}")
        return stats
    
    def _update_property_geocoding(
        self,
        property_id: str,
        status: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        error: Optional[str] = None,
        attempts: Optional[int] = None
    ):
        """Atualiza status de geocoding de um imóvel."""
        update_data = {
            "geocoding_status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if latitude is not None:
            update_data["latitude"] = latitude
        if longitude is not None:
            update_data["longitude"] = longitude
        if error is not None:
            update_data["geocoding_error"] = error[:500]  # Limita tamanho
        if attempts is not None:
            update_data["geocoding_attempts"] = attempts
        if status == "done":
            update_data["geocoded_at"] = datetime.utcnow().isoformat()
        
        self.supabase.table("properties") \
            .update(update_data) \
            .eq("id", property_id) \
            .execute()
    
    async def process_all_pending(self, max_batches: int = 100) -> Dict[str, int]:
        """
        Processa TODOS os imóveis pendentes de geocoding.
        
        Args:
            max_batches: Número máximo de lotes a processar
            
        Returns:
            Estatísticas totais
        """
        if self._is_processing:
            logger.warning("Geocoding já está em andamento")
            return {"error": "already_processing"}
        
        self._is_processing = True
        
        total_stats = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "batches": 0
        }
        
        try:
            for batch_num in range(max_batches):
                stats = await self.process_pending_batch()
                
                if stats["processed"] == 0:
                    break  # Não há mais pendentes
                
                total_stats["processed"] += stats["processed"]
                total_stats["success"] += stats["success"]
                total_stats["failed"] += stats["failed"]
                total_stats["skipped"] += stats["skipped"]
                total_stats["batches"] += 1
                
                logger.info(f"Batch {batch_num + 1}: {stats['processed']} processados")
                
        finally:
            self._is_processing = False
        
        logger.info(f"Geocoding completo: {total_stats}")
        return total_stats
    
    def get_pending_count(self) -> int:
        """Retorna número de imóveis pendentes de geocoding."""
        response = self.supabase.table("properties") \
            .select("id", count="exact") \
            .eq("geocoding_status", "pending") \
            .execute()
        
        return response.count or 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de geocoding."""
        response = self.supabase.table("properties") \
            .select("geocoding_status") \
            .execute()
        
        stats = {}
        for row in response.data or []:
            status = row.get("geocoding_status", "unknown")
            stats[status] = stats.get(status, 0) + 1
        
        return stats


# Instância global
_geocoding_service: Optional[AsyncGeocodingService] = None

def get_geocoding_service() -> AsyncGeocodingService:
    """Obtém instância global do serviço de geocoding."""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = AsyncGeocodingService()
    return _geocoding_service


async def process_geocoding_background():
    """
    Função para executar geocoding em background.
    Pode ser chamada por um cron job ou endpoint.
    """
    service = get_geocoding_service()
    return await service.process_all_pending()

