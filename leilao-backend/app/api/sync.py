"""
API de sincronizacao.

IMPORTANTE: Endpoints de INSERT estao DESABILITADOS.
Este servico e apenas de LEITURA.
Use leilohub-scraper-final para inserir dados (possui validacao completa).
"""

from fastapi import APIRouter, HTTPException
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])

# Estado da sincronizacao (mantido para compatibilidade)
_sync_status = {
    'is_running': False,
    'last_report': {"message": "Sync desabilitado - use leilohub-scraper-final"}
}


@router.post("/start")
async def start_sync():
    """
    DESABILITADO - Use leilohub-scraper-final para sincronizacao.

    Este endpoint foi desabilitado porque o aggregator nao possui
    validacao completa de qualidade de dados.
    """
    logger.warning("Tentativa de usar endpoint /api/sync/start (DESABILITADO)")
    raise HTTPException(
        status_code=501,
        detail="Endpoint desabilitado. Use leilohub-scraper-final para sincronizacao (possui validacao completa)."
    )


@router.post("/caixa")
async def sync_caixa_only():
    """
    DESABILITADO - Use leilohub-scraper-final para sincronizacao da Caixa.
    """
    logger.warning("Tentativa de usar endpoint /api/sync/caixa (DESABILITADO)")
    raise HTTPException(
        status_code=501,
        detail="Endpoint desabilitado. Use leilohub-scraper-final para sincronizacao (possui validacao completa)."
    )


@router.get("/status")
async def get_sync_status():
    """
    Retorna status da sincronizacao.

    NOTA: Sincronizacao esta desabilitada neste servico.
    """
    return {
        "is_running": False,
        "last_report": _sync_status['last_report'],
        "message": "Sincronizacao desabilitada neste servico. Use leilohub-scraper-final."
    }

