from fastapi import APIRouter
from datetime import datetime
from app.services import db

router = APIRouter(prefix="/api", tags=["dashboard"])

@router.get("/dashboard")
async def get_dashboard():
    """Retorna metricas do dashboard"""
    
    # Total de imoveis
    total_properties = await db.count_properties()
    
    # Total de leiloeiros
    total_auctioneers = await db.count_auctioneers()
    
    # Scrapers ativos
    active_scrapers = await db.count_active_scrapers()
    
    # Imoveis ultimas 24h
    properties_last_24h = await db.count_new_properties(hours=24)
    
    # Taxa de erro
    error_rate = await db.calculate_error_rate()
    
    # Top leiloeiros
    top_auctioneers = await db.get_top_auctioneers(limit=20)
    
    # Percentual Caixa
    caixa_percentage = await db.calculate_caixa_percentage()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "total_properties": total_properties,
        "total_auctioneers": total_auctioneers,
        "active_scrapers": active_scrapers,
        "properties_last_24h": properties_last_24h,
        "error_rate": error_rate,
        "top_auctioneers": top_auctioneers,
        "caixa_percentage": caixa_percentage,
    }

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
