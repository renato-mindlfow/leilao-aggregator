"""
Serviço de Geocoding em Background
Processa imóveis sem coordenadas de forma assíncrona
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from app.services.postgres_database import PostgresDatabase

logger = logging.getLogger(__name__)

class BackgroundGeocodingService:
    """
    Serviço que processa geocoding em background, sem bloquear requisições HTTP.
    """
    
    def __init__(self, db: PostgresDatabase):
        self.db = db
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
        self.start_time: Optional[datetime] = None
        
    async def get_pending_properties(self, limit: int = 100) -> List[dict]:
        """
        Busca imóveis que precisam de geocoding.
        Retorna apenas imóveis com latitude/longitude NULL ou 0.
        """
        query = """
            SELECT id, address, city, state, neighborhood
            FROM properties
            WHERE (latitude IS NULL OR latitude = 0 OR longitude IS NULL OR longitude = 0)
            AND state != 'XX'
            AND is_active = true
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        try:
            with self.db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (limit,))
                    rows = cur.fetchall()
                    return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Erro ao buscar imóveis pendentes: {e}")
            return []
    
    async def geocode_single(self, property_data: dict) -> Optional[dict]:
        """
        Geocodifica um único imóvel usando Nominatim.
        Respeita rate limit de 1 req/segundo.
        """
        import httpx
        
        # Monta o endereço completo
        parts = []
        if property_data.get('address'):
            parts.append(property_data['address'])
        if property_data.get('neighborhood'):
            parts.append(property_data['neighborhood'])
        if property_data.get('city'):
            parts.append(property_data['city'])
        if property_data.get('state'):
            parts.append(property_data['state'])
        parts.append('Brasil')
        
        full_address = ', '.join(filter(None, parts))
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    'https://nominatim.openstreetmap.org/search',
                    params={
                        'q': full_address,
                        'format': 'json',
                        'limit': 1,
                        'countrycodes': 'br'
                    },
                    headers={
                        'User-Agent': 'LeiloHub/1.0 (contato@leilohub.com.br)'
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return {
                            'latitude': float(data[0]['lat']),
                            'longitude': float(data[0]['lon'])
                        }
                        
        except Exception as e:
            logger.error(f"Erro no geocoding de '{full_address}': {e}")
            
        return None
    
    async def update_coordinates(self, property_id: str, lat: float, lon: float) -> bool:
        """
        Atualiza as coordenadas de um imóvel no banco.
        """
        query = """
            UPDATE properties
            SET latitude = %s, longitude = %s, updated_at = NOW()
            WHERE id = %s
        """
        
        try:
            with self.db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (lat, lon, property_id))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar coordenadas do imóvel {property_id}: {e}")
            return False
    
    async def process_batch(self, batch_size: int = 50, delay: float = 1.1) -> dict:
        """
        Processa um lote de imóveis pendentes.
        
        Args:
            batch_size: Número de imóveis a processar
            delay: Delay entre requisições (Nominatim exige 1 req/seg)
            
        Returns:
            Dict com estatísticas do processamento
        """
        if self.is_running:
            return {"status": "already_running", "message": "Já existe um processo em execução"}
        
        self.is_running = True
        self.start_time = datetime.now()
        self.processed_count = 0
        self.error_count = 0
        
        try:
            properties = await self.get_pending_properties(batch_size)
            
            if not properties:
                return {
                    "status": "completed",
                    "message": "Nenhum imóvel pendente de geocoding",
                    "processed": 0,
                    "errors": 0
                }
            
            logger.info(f"Iniciando geocoding de {len(properties)} imóveis")
            
            for prop in properties:
                try:
                    coords = await self.geocode_single(prop)
                    
                    if coords:
                        success = await self.update_coordinates(
                            prop['id'],
                            coords['latitude'],
                            coords['longitude']
                        )
                        if success:
                            self.processed_count += 1
                            logger.debug(f"Geocoding OK: {prop['id']}")
                        else:
                            self.error_count += 1
                    else:
                        self.error_count += 1
                        logger.warning(f"Geocoding falhou: {prop['id']}")
                    
                    # Respeita rate limit do Nominatim
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Erro ao processar {prop['id']}: {e}")
            
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            return {
                "status": "completed",
                "processed": self.processed_count,
                "errors": self.error_count,
                "total": len(properties),
                "elapsed_seconds": round(elapsed, 2)
            }
            
        finally:
            self.is_running = False
    
    def get_status(self) -> dict:
        """
        Retorna o status atual do processamento.
        """
        return {
            "is_running": self.is_running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "start_time": self.start_time.isoformat() if self.start_time else None
        }


# Instância global do serviço (será inicializada no main.py)
background_geocoding_service: Optional[BackgroundGeocodingService] = None

def get_geocoding_service() -> BackgroundGeocodingService:
    """Retorna a instância do serviço de geocoding."""
    global background_geocoding_service
    if background_geocoding_service is None:
        raise RuntimeError("BackgroundGeocodingService não foi inicializado")
    return background_geocoding_service

def init_geocoding_service(db: PostgresDatabase):
    """Inicializa o serviço de geocoding."""
    global background_geocoding_service
    background_geocoding_service = BackgroundGeocodingService(db)
    logger.info("BackgroundGeocodingService inicializado")

