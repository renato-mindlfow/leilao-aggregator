"""
API de Geocoding Assíncrono.

Endpoints para controle do geocoding em background.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Optional
import logging

from app.services.async_geocoding_service import (
    get_geocoding_service,
    process_geocoding_background
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geocoding", tags=["geocoding"])

# Estado do processamento
_geocoding_state = {
    "is_running": False,
    "last_stats": None
}

@router.post("/start")
async def start_geocoding(
    background_tasks: BackgroundTasks,
    batch_size: int = 50,
    max_batches: int = 100
):
    """
    Inicia geocoding em background.
    
    NÃO BLOQUEIA a requisição HTTP.
    """
    if _geocoding_state["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Geocoding já está em andamento"
        )
    
    async def run_geocoding():
        global _geocoding_state
        _geocoding_state["is_running"] = True
        
        try:
            stats = await process_geocoding_background()
            _geocoding_state["last_stats"] = stats
        except Exception as e:
            logger.error(f"Erro no geocoding: {e}")
            _geocoding_state["last_stats"] = {"error": str(e)}
        finally:
            _geocoding_state["is_running"] = False
    
    background_tasks.add_task(run_geocoding)
    
    return {
        "status": "started",
        "message": "Geocoding iniciado em background"
    }

@router.post("/process-batch")
async def process_single_batch(batch_size: int = 50):
    """
    Processa um único lote de geocoding.
    
    Útil para testes ou processamento gradual.
    """
    service = get_geocoding_service()
    stats = await service.process_pending_batch(batch_size)
    return stats

@router.get("/status")
async def get_geocoding_status():
    """
    Retorna status do geocoding.
    """
    service = get_geocoding_service()
    
    return {
        "is_running": _geocoding_state["is_running"],
        "pending_count": service.get_pending_count(),
        "stats_by_status": service.get_stats(),
        "last_run_stats": _geocoding_state["last_stats"]
    }

@router.get("/stats")
async def get_geocoding_stats():
    """
    Retorna estatísticas detalhadas de geocoding.
    """
    service = get_geocoding_service()
    return service.get_stats()

