"""
API de sincronização.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Optional
import logging

from app.services.sync_service import get_sync_service, SyncReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])

# Estado da sincronização
_sync_status = {
    'is_running': False,
    'last_report': None
}

@router.post("/start")
async def start_sync(
    background_tasks: BackgroundTasks,
    include_caixa: bool = True,
    include_auctioneers: bool = True,
    auctioneer_limit: Optional[int] = None
):
    """
    Inicia sincronização em background.
    """
    if _sync_status['is_running']:
        raise HTTPException(
            status_code=409,
            detail="Sincronização já está em andamento"
        )
    
    async def run_sync():
        global _sync_status
        _sync_status['is_running'] = True
        
        try:
            service = get_sync_service()
            report = await service.sync_all(
                include_caixa=include_caixa,
                include_auctioneers=include_auctioneers,
                auctioneer_limit=auctioneer_limit
            )
            _sync_status['last_report'] = report.to_dict()
        except Exception as e:
            logger.error(f"Erro na sincronização: {e}")
            _sync_status['last_report'] = {'error': str(e)}
        finally:
            _sync_status['is_running'] = False
    
    background_tasks.add_task(run_sync)
    
    return {"status": "started", "message": "Sincronização iniciada em background"}

@router.post("/caixa")
async def sync_caixa_only(background_tasks: BackgroundTasks):
    """
    Sincroniza apenas dados da Caixa.
    """
    if _sync_status['is_running']:
        raise HTTPException(
            status_code=409,
            detail="Sincronização já está em andamento"
        )
    
    async def run_caixa_sync():
        global _sync_status
        _sync_status['is_running'] = True
        
        try:
            service = get_sync_service()
            report = await service.sync_caixa_only()
            _sync_status['last_report'] = report.to_dict()
        except Exception as e:
            logger.error(f"Erro na sincronização Caixa: {e}")
            _sync_status['last_report'] = {'error': str(e)}
        finally:
            _sync_status['is_running'] = False
    
    background_tasks.add_task(run_caixa_sync)
    
    return {"status": "started", "message": "Sincronização da Caixa iniciada"}

@router.get("/status")
async def get_sync_status():
    """
    Retorna status da sincronização.
    """
    return {
        "is_running": _sync_status['is_running'],
        "last_report": _sync_status['last_report']
    }

