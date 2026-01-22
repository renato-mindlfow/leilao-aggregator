"""
API endpoints para diagnóstico de scrapers
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List
import logging
import psycopg
from psycopg.rows import dict_row
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])

def execute_diagnostic_query(query: str) -> List[Dict]:
    """Executa uma query de diagnóstico e retorna os resultados"""
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não configurada")
    
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                results = cur.fetchall()
                return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Erro ao executar query de diagnóstico: {e}")
        raise

@router.get("/scrapers/status-summary")
async def get_status_summary():
    """Retorna resumo geral de status dos leiloeiros"""
    query = """
    SELECT 
        scrape_status,
        COUNT(*) as total
    FROM auctioneers
    GROUP BY scrape_status
    ORDER BY total DESC
    """
    
    try:
        results = execute_diagnostic_query(query)
        return {"success": True, "data": results}
    except Exception as e:
        logger.error(f"Erro ao consultar status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scrapers/errors")
async def get_scrapers_with_errors(limit: int = 50):
    """Retorna leiloeiros com erro"""
    query = f"""
    SELECT id, name, website, scrape_status, scrape_error
    FROM auctioneers
    WHERE scrape_status = 'error'
    ORDER BY name
    LIMIT {limit}
    """
    
    try:
        results = execute_diagnostic_query(query)
        return {"success": True, "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"Erro ao consultar erros: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scrapers/pending")
async def get_pending_scrapers(limit: int = 50):
    """Retorna leiloeiros pendentes"""
    query = f"""
    SELECT id, name, website, scrape_status
    FROM auctioneers
    WHERE scrape_status = 'pending' OR scrape_status IS NULL
    ORDER BY name
    LIMIT {limit}
    """
    
    try:
        results = execute_diagnostic_query(query)
        return {"success": True, "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"Erro ao consultar pendentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scrapers/success")
async def get_successful_scrapers():
    """Retorna leiloeiros funcionando"""
    query = """
    SELECT id, name, website, property_count, last_scrape
    FROM auctioneers
    WHERE scrape_status = 'success'
    ORDER BY property_count DESC
    """
    
    try:
        results = execute_diagnostic_query(query)
        return {"success": True, "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"Erro ao consultar sucessos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/properties/distribution")
async def get_properties_distribution(limit: int = 20):
    """Retorna distribuição de imóveis por leiloeiro"""
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
        results = execute_diagnostic_query(query)
        return {"success": True, "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"Erro ao consultar distribuição: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/errors/types")
async def get_error_types(limit: int = 20):
    """Retorna tipos de erros mais comuns"""
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
        results = execute_diagnostic_query(query)
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

@router.post("/fix-duplicate-keys")
async def fix_duplicate_keys():
    """Remove propriedades com IDs duplicados que causam erro e reseta status dos leiloeiros"""
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL não configurada")
    
    # IDs problemáticos identificados
    duplicate_property_ids = [
        'Correaleiloes_Lote 1',
        'Centraljudicial_352',
        'Marangonileiloes_Lote 1',
        'Lancenoleilao_24090'
    ]
    
    # IDs dos leiloeiros para resetar status
    auctioneer_ids_to_reset = ['117', '62', '226', '25']
    
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                deleted_count = 0
                
                # Deletar propriedades duplicadas
                for prop_id in duplicate_property_ids:
                    cur.execute("DELETE FROM properties WHERE id = %s", (prop_id,))
                    deleted_count += cur.rowcount
                    logger.info(f"Deletado: {prop_id} ({cur.rowcount} rows)")
                
                # Resetar status dos leiloeiros para permitir re-scraping
                for auc_id in auctioneer_ids_to_reset:
                    cur.execute("""
                        UPDATE auctioneers 
                        SET scrape_status = 'pending', 
                            scrape_error = NULL,
                            last_scrape = NULL
                        WHERE id = %s
                    """, (auc_id,))
                    logger.info(f"Reset status do leiloeiro ID: {auc_id}")
                
                conn.commit()
                
                return {
                    "success": True,
                    "deleted_properties": deleted_count,
                    "reset_auctioneers": len(auctioneer_ids_to_reset),
                    "message": f"Removidas {deleted_count} propriedades duplicadas e resetados {len(auctioneer_ids_to_reset)} leiloeiros"
                }
    
    except Exception as e:
        logger.error(f"Erro ao corrigir duplicate keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))
