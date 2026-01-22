"""
API endpoints para diagnóstico de scrapers
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List
import logging

from app.services.postgres_database import get_postgres_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])

@router.get("/scrapers/status-summary")
async def get_status_summary():
    """Retorna resumo geral de status dos leiloeiros"""
    db = get_postgres_database()
    
    query = """
    SELECT 
        scrape_status,
        COUNT(*) as total
    FROM auctioneers
    GROUP BY scrape_status
    ORDER BY total DESC
    """
    
    try:
        results = db.execute_query(query)
        return {"success": True, "data": results}
    except Exception as e:
        logger.error(f"Erro ao consultar status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scrapers/errors")
async def get_scrapers_with_errors(limit: int = 50):
    """Retorna leiloeiros com erro"""
    db = get_postgres_database()
    
    query = f"""
    SELECT id, name, website, scrape_status, scrape_error
    FROM auctioneers
    WHERE scrape_status = 'error'
    ORDER BY name
    LIMIT {limit}
    """
    
    try:
        results = db.execute_query(query)
        return {"success": True, "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"Erro ao consultar erros: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scrapers/pending")
async def get_pending_scrapers(limit: int = 50):
    """Retorna leiloeiros pendentes"""
    db = get_postgres_database()
    
    query = f"""
    SELECT id, name, website, scrape_status
    FROM auctioneers
    WHERE scrape_status = 'pending' OR scrape_status IS NULL
    ORDER BY name
    LIMIT {limit}
    """
    
    try:
        results = db.execute_query(query)
        return {"success": True, "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"Erro ao consultar pendentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scrapers/success")
async def get_successful_scrapers():
    """Retorna leiloeiros funcionando"""
    db = get_postgres_database()
    
    query = """
    SELECT id, name, website, property_count, last_scrape
    FROM auctioneers
    WHERE scrape_status = 'success'
    ORDER BY property_count DESC
    """
    
    try:
        results = db.execute_query(query)
        return {"success": True, "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"Erro ao consultar sucessos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/properties/distribution")
async def get_properties_distribution(limit: int = 20):
    """Retorna distribuição de imóveis por leiloeiro"""
    db = get_postgres_database()
    
    query = f"""
    SELECT 
        a.name as leiloeiro,
        a.id as auctioneer_id,
        COUNT(p.id) as total_imoveis
    FROM properties p
    JOIN auctioneers a ON p.auctioneer_id = a.id
    GROUP BY a.name, a.id
    ORDER BY total_imoveis DESC
    LIMIT {limit}
    """
    
    try:
        results = db.execute_query(query)
        return {"success": True, "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"Erro ao consultar distribuição: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/errors/types")
async def get_error_types(limit: int = 20):
    """Retorna tipos de erros mais comuns"""
    db = get_postgres_database()
    
    query = f"""
    SELECT 
        scrape_error,
        COUNT(*) as total
    FROM auctioneers
    WHERE scrape_status = 'error'
    GROUP BY scrape_error
    ORDER BY total DESC
    LIMIT {limit}
    """
    
    try:
        results = db.execute_query(query)
        return {"success": True, "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"Erro ao consultar tipos de erros: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/full-report")
async def get_full_diagnostic_report():
    """Retorna relatório completo de diagnóstico"""
    try:
        status_summary = await get_status_summary()
        errors = await get_scrapers_with_errors(limit=100)
        pending = await get_pending_scrapers(limit=100)
        success = await get_successful_scrapers()
        distribution = await get_properties_distribution(limit=30)
        error_types = await get_error_types(limit=30)
        
        return {
            "success": True,
            "report": {
                "status_summary": status_summary["data"],
                "scrapers_with_errors": errors["data"],
                "pending_scrapers": pending["data"],
                "successful_scrapers": success["data"],
                "properties_distribution": distribution["data"],
                "error_types": error_types["data"]
            }
        }
    except Exception as e:
        logger.error(f"Erro ao gerar relatório completo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
