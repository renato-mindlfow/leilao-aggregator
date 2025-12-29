import os
import httpx
import logging
import re
from typing import Dict, List, Optional, Tuple
import asyncio

logger = logging.getLogger(__name__)

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

class GeocodingService:
    """Serviço de geocoding usando OpenStreetMap Nominatim (gratuito)"""
    
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    
    def __init__(self):
        self.user_agent = "LeiloHub/1.0 (contato@leilohub.com.br)"
        self.cache = {}  # Cache simples em memória
    
    async def geocode_address(self, address: str, city: str = "", state: str = "") -> Optional[Tuple[float, float]]:
        """Converte endereço em coordenadas (lat, lng)"""
        
        if not address and not city:
            return None
        
        # VALIDAR ANTES DE CHAMAR API
        if address:
            is_valid, motivo = validar_endereco_para_geocoding(address)
            if not is_valid:
                logger.warning(f"Endereço inválido para geocoding: {motivo}")
                return None
        
        # LIMPAR ENDEREÇO
        address_limpo = limpar_endereco(address) if address else ""
        
        # Monta query de busca
        query_parts = []
        if address_limpo:
            query_parts.append(address_limpo)
        if city:
            query_parts.append(city)
        if state:
            query_parts.append(state)
        query_parts.append("Brasil")
        
        query = ", ".join(query_parts)
        
        # Verifica cache
        cache_key = query.lower().strip()
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.NOMINATIM_URL,
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "countrycodes": "br"
                    },
                    headers={"User-Agent": self.user_agent},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    results = response.json()
                    if results:
                        lat = float(results[0]["lat"])
                        lng = float(results[0]["lon"])
                        
                        # Armazena no cache
                        self.cache[cache_key] = (lat, lng)
                        
                        return (lat, lng)
        
        except Exception as e:
            logger.error(f"Erro no geocoding de '{query}': {e}")
        
        # Tenta busca simplificada só com cidade e estado
        if address and city:
            return await self.geocode_address("", city, state)
        
        return None
    
    async def geocode_batch(self, properties: List[Dict], delay: float = 1.0) -> List[Dict]:
        """Geocodifica um lote de imóveis respeitando rate limit"""
        
        for i, prop in enumerate(properties):
            # Pula se já tem coordenadas
            if prop.get('latitude') and prop.get('longitude'):
                continue
            
            coords = await self.geocode_address(
                prop.get('address', ''),
                prop.get('city', ''),
                prop.get('state', '')
            )
            
            if coords:
                prop['latitude'] = coords[0]
                prop['longitude'] = coords[1]
            
            # Rate limiting (Nominatim pede 1 req/seg)
            if i < len(properties) - 1:
                await asyncio.sleep(delay)
            
            if (i + 1) % 10 == 0:
                logger.info(f"Geocodificados {i + 1}/{len(properties)} imóveis")
        
        return properties
    
    async def geocode_property(self, property_data: Dict) -> Dict:
        """Geocodifica um único imóvel"""
        
        if property_data.get('latitude') and property_data.get('longitude'):
            return property_data
        
        address = property_data.get('address', '')
        
        # Validar endereço antes de tentar geocoding
        if address:
            is_valid, motivo = validar_endereco_para_geocoding(address)
            if not is_valid:
                logger.warning(f"Endereço inválido para geocoding: {motivo}")
                property_data['geocoding_error'] = motivo
                property_data['geocoding_status'] = 'invalid_address'
                return property_data
        
        coords = await self.geocode_address(
            address,
            property_data.get('city', ''),
            property_data.get('state', '')
        )
        
        if coords:
            property_data['latitude'] = coords[0]
            property_data['longitude'] = coords[1]
            property_data['geocoding_status'] = 'done'
        else:
            property_data['geocoding_status'] = 'failed'
        
        return property_data


# Instância global
geocoding_service = GeocodingService()


