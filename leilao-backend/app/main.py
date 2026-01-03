from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime
import json
import logging
import traceback
import os
from dotenv import load_dotenv

# Carregar .env ANTES de qualquer outra coisa
load_dotenv()

from app.models import (
    Property,
    PropertyCreate,
    PropertyFilter,
    Auctioneer,
    AuctioneerCreate,
)
from app.models.property import PropertyCategory, AuctionType
from app.services import db, DeduplicationService
from app.services.scraper_monitor import get_scraper_monitor, ScraperStatus
from app.services.autonomous_scheduler import get_autonomous_scheduler
from app.services.asaas_service import asaas_service
from app.services.scraper_pipeline import scraper_pipeline
from app.services.ai_normalizer import ai_normalizer
from app.services.geocoding_service import geocoding_service
from app.services.scraper_orchestrator import scraper_orchestrator
from app.services.discovery_orchestrator import discovery_orchestrator
from app.services.structure_validator import structure_validator
from app.api.properties import router as properties_router
from app.api.sync import router as sync_router
from app.api.geocoding import router as geocoding_router
from app.services.background_geocoding import (
    init_geocoding_service,
    get_geocoding_service,
    BackgroundGeocodingService
)
from app.utils.quality_auditor import get_quality_auditor
from app.utils.image_blacklist import get_image_blacklist

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Leilão Aggregator API",
    description="API para agregação de imóveis de leilão de múltiplos leiloeiros brasileiros",
    version="1.0.0",
)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

dedup_service = DeduplicationService()

# Inicializar serviço de geocoding em background
init_geocoding_service(db)

# Registrar router de properties (Sprint 3 - API melhorada)
app.include_router(properties_router)

# Registrar router de sync (Sprint 4 - Sincronização)
app.include_router(sync_router)

# Registrar router de geocoding (Geocoding assíncrono)
app.include_router(geocoding_router)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/health")
async def health_check():
    """Health check endpoint para monitoramento."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


# ==================== Properties Endpoints ====================
# NOTA: Os endpoints GET abaixo foram substituídos pelo router em app/api/properties.py
# que oferece funcionalidades aprimoradas (ordenação, filtros, estatísticas)
# Mantidos temporariamente para compatibilidade - podem ser removidos após validação

# @app.get("/api/properties", response_model=dict)
# async def list_properties(
#     page: int = Query(1, ge=1, description="Número da página"),
#     limit: int = Query(18, ge=1, le=100, description="Itens por página"),
#     state: Optional[str] = Query(None, description="Filtrar por estado (UF)"),
#     city: Optional[str] = Query(None, description="Filtrar por cidade"),
#     neighborhood: Optional[str] = Query(None, description="Filtrar por bairro"),
#     category: Optional[PropertyCategory] = Query(None, description="Filtrar por categoria"),
#     auction_type: Optional[AuctionType] = Query(None, description="Filtrar por tipo de leilão"),
#     min_value: Optional[float] = Query(None, description="Valor mínimo"),
#     max_value: Optional[float] = Query(None, description="Valor máximo"),
#     min_discount: Optional[float] = Query(None, description="Desconto mínimo (%)"),
#     auctioneer_id: Optional[str] = Query(None, description="Filtrar por leiloeiro"),
#     search: Optional[str] = Query(None, description="Termo de busca"),
#     include_duplicates: bool = Query(False, description="Incluir duplicatas"),
#     sort: Optional[str] = Query(None, description="Ordenação: price_asc, price_desc, discount, recent"),
#     sort_by: Optional[str] = Query("created_at", description="Ordenar por: created_at, second_auction_value, discount_percentage"),
#     sort_order: Optional[str] = Query("desc", description="Ordem: asc ou desc"),
# ):
#     """Lista imóveis com filtros e paginação."""
#     filters = PropertyFilter(
#         state=state,
#         city=city,
#         neighborhood=neighborhood,
#         category=category,
#         auction_type=auction_type,
#         min_value=min_value,
#         max_value=max_value,
#         min_discount=min_discount,
#         auctioneer_id=auctioneer_id,
#         search_term=search,
#         include_duplicates=include_duplicates,
#     )
#     
#     skip = (page - 1) * limit
#     
#     # Mapear parâmetro sort do frontend para sort_by e sort_order
#     if sort:
#         sort_mapping = {
#             "price_asc": ("second_auction_value", "asc"),
#             "price_desc": ("second_auction_value", "desc"),
#             "discount": ("discount_percentage", "desc"),
#             "discount_desc": ("discount_percentage", "desc"),
#             "recent": ("created_at", "desc"),
#         }
#         if sort in sort_mapping:
#             sort_by, sort_order = sort_mapping[sort]
#     
#     properties, total = db.get_properties(filters=filters, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order)
#     
#     total_pages = (total + limit - 1) // limit
#     
#     return {
#         "items": [p.model_dump() for p in properties],
#         "total": total,
#         "page": page,
#         "limit": limit,
#         "total_pages": total_pages,
#         "has_next": page < total_pages,
#         "has_prev": page > 1,
#     }


# @app.get("/api/properties/{property_id}", response_model=Property)
# async def get_property(property_id: str):
#     """Obtém detalhes de um imóvel específico."""
#     property_obj = db.get_property(property_id)
#     if not property_obj:
#         raise HTTPException(status_code=404, detail="Imóvel não encontrado")
#     return property_obj


@app.post("/api/properties", response_model=Property)
async def create_property(property_data: PropertyCreate):
    """Cria um novo imóvel (usado pelos scrapers)."""
    # Check for duplicates
    existing_properties = list(db.properties.values())
    original_id = dedup_service.is_duplicate(property_data.model_dump(), existing_properties)
    
    property_obj = db.create_property(property_data)
    
    if original_id:
        property_obj.is_duplicate = True
        property_obj.original_id = original_id
    
    return property_obj


@app.delete("/api/properties/{property_id}")
async def delete_property(property_id: str):
    """Remove um imóvel."""
    if not db.delete_property(property_id):
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    return {"message": "Imóvel removido com sucesso"}


# ==================== Auctioneers Endpoints ====================

@app.get("/api/auctioneers", response_model=List[Auctioneer])
async def list_auctioneers():
    """Lista todos os leiloeiros."""
    return db.get_auctioneers()


@app.get("/api/auctioneers/{auctioneer_id}", response_model=Auctioneer)
async def get_auctioneer(auctioneer_id: str):
    """Obtém detalhes de um leiloeiro específico."""
    auctioneer = db.get_auctioneer(auctioneer_id)
    if not auctioneer:
        raise HTTPException(status_code=404, detail="Leiloeiro não encontrado")
    return auctioneer


@app.post("/api/auctioneers", response_model=Auctioneer)
async def create_auctioneer(auctioneer_data: AuctioneerCreate):
    """Cria um novo leiloeiro."""
    # Check if already exists
    existing = db.get_auctioneer_by_website(auctioneer_data.website)
    if existing:
        raise HTTPException(status_code=400, detail="Leiloeiro com este website já existe")
    return db.create_auctioneer(auctioneer_data)


# ==================== Statistics Endpoints ====================

@app.get("/api/stats")
async def get_stats():
    """Obtém estatísticas gerais do sistema."""
    return db.get_stats()


@app.get("/api/stats/deduplication")
async def get_deduplication_stats():
    """Obtém estatísticas de deduplicação."""
    return dedup_service.get_deduplication_stats(db.properties)


# ==================== Filter Options Endpoints ====================

@app.get("/api/filters/states")
async def get_states():
    """Lista estados disponíveis."""
    if hasattr(db, 'get_unique_states'):
        return db.get_unique_states()
    states = set()
    for prop in db.properties.values():
        if not prop.is_duplicate:
            states.add(prop.state)
    return sorted(list(states))


@app.get("/api/filters/cities")
async def get_cities(state: Optional[str] = None):
    """Lista cidades disponíveis, opcionalmente filtradas por estado."""
    if hasattr(db, 'get_unique_cities'):
        return db.get_unique_cities(state)
    cities = set()
    for prop in db.properties.values():
        if not prop.is_duplicate:
            if state is None or prop.state.lower() == state.lower():
                cities.add(prop.city)
    return sorted(list(cities))


@app.get("/api/filters/neighborhoods")
async def get_neighborhoods(state: Optional[str] = None, city: Optional[str] = None):
    """Lista bairros disponíveis, opcionalmente filtrados por estado e cidade."""
    if hasattr(db, 'get_unique_neighborhoods'):
        return db.get_unique_neighborhoods(state, city)
    neighborhoods = set()
    for prop in db.properties.values():
        if not prop.is_duplicate and prop.neighborhood:
            if state is None or prop.state.lower() == state.lower():
                if city is None or prop.city.lower() == city.lower():
                    neighborhoods.add(prop.neighborhood)
    return sorted(list(neighborhoods))


@app.get("/api/filters/categories")
async def get_categories():
    """Lista categorias disponíveis."""
    return [cat.value for cat in PropertyCategory]


@app.get("/api/filters/auction-types")
async def get_auction_types():
    """Lista tipos de leilão disponíveis."""
    return [at.value for at in AuctionType]


# ==================== Scraper Control Endpoints ====================

@app.post("/api/scrapers/run/{auctioneer_id}")
async def run_scraper(auctioneer_id: str):
    """Inicia o scraper para um leiloeiro específico."""
    auctioneer = db.get_auctioneer(auctioneer_id)
    if not auctioneer:
        raise HTTPException(status_code=404, detail="Leiloeiro não encontrado")
    
    # Update status to running
    db.update_auctioneer_scrape_status(auctioneer_id, "running")
    
    # Note: In production, this would trigger an async task
    # For MVP, we'll just return a message
    return {
        "message": f"Scraper iniciado para {auctioneer.name}",
        "auctioneer_id": auctioneer_id,
        "status": "running"
    }


@app.post("/api/scrapers/run-all")
async def run_all_scrapers():
    """
    Inicia scrapers para TODOS os leiloeiros ativos do banco de dados.
    Usa scrapers específicos quando disponível, caso contrário usa scraper genérico.
    Garante que TODAS as páginas sejam raspadas (sem limite artificial).
    """
    from app.services.universal_scraper_service import get_universal_scraper_service
    
    scraper_service = get_universal_scraper_service()
    results = scraper_service.scrape_all_auctioneers(max_retries=3)
    
    return {
        "message": f"Scraping concluído para {results['auctioneers_processed']} leiloeiros",
        "results": results
    }


@app.post("/api/scrapers/bulk-import")
async def bulk_import_all_auctioneers(max_per_auctioneer: int = 20):
    """
    Executa importação em massa de todos os leiloeiros integrados.
    Roda scrapers SEQUENCIALMENTE para evitar problemas de memória.
    
    Args:
        max_per_auctioneer: Máximo de imóveis por leiloeiro (default: 20)
    """
    import gc
    import logging
    logger = logging.getLogger(__name__)
    from app.scrapers.portalzuk_scraper import PortalZukScraper
    from app.scrapers.superbid_scraper import SuperbidScraper
    from app.scrapers.megaleiloes_scraper import MegaleiloesScraper
    from app.scrapers.leilaovip_scraper import LeilaoVipScraper
    from app.scrapers.inovaleilao_scraper import InovaLeilaoScraper
    from app.scrapers.pestana_scraper import PestanaScraper
    
    results = {
        "started_at": datetime.now().isoformat(),
        "auctioneers_processed": 0,
        "total_properties_imported": 0,
        "properties_by_auctioneer": {},
        "errors": [],
    }
    
    # Define scrapers with their configurations - run sequentially to save memory
    scrapers_config = [
        {"name": "Portal Zuk", "scraper": PortalZukScraper, "method": "scrape_listings", "kwargs": {"max_properties": max_per_auctioneer}},
        {"name": "Superbid", "scraper": SuperbidScraper, "method": "scrape_properties", "kwargs": {"max_properties": max_per_auctioneer}},
        {"name": "Mega Leilões", "scraper": MegaleiloesScraper, "method": "scrape_properties", "kwargs": {"max_properties": max_per_auctioneer}},
        {"name": "Leilão VIP", "scraper": LeilaoVipScraper, "method": "scrape_properties", "kwargs": {"max_properties": max_per_auctioneer}},
        {"name": "Inova Leilão", "scraper": InovaLeilaoScraper, "method": "scrape_properties", "kwargs": {"max_properties": max_per_auctioneer}},
        {"name": "Pestana Leilões", "scraper": PestanaScraper, "method": "scrape_properties", "kwargs": {"max_properties": max_per_auctioneer}},
    ]
    
    # Run scrapers SEQUENTIALLY to avoid OOM
    for config in scrapers_config:
        try:
            logger.info(f"Starting scraper: {config['name']}")
            scraper = config["scraper"]()
            method = getattr(scraper, config["method"])
            result = method(**config["kwargs"])
            
            # Handle different return types
            if hasattr(result, 'complete_properties'):
                properties = result.complete_properties
            elif isinstance(result, list):
                properties = result
            else:
                properties = []
            
            # Add properties to database
            for prop in properties:
                db.add_property(prop)
            
            results["properties_by_auctioneer"][config["name"]] = len(properties)
            results["total_properties_imported"] += len(properties)
            results["auctioneers_processed"] += 1
            logger.info(f"Completed {config['name']}: {len(properties)} properties")
            
            # Clean up to free memory
            del scraper
            del result
            del properties
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error in {config['name']}: {str(e)}")
            results["errors"].append(f"{config['name']}: {str(e)}")
            results["properties_by_auctioneer"][config["name"]] = 0
            results["auctioneers_processed"] += 1
    
    results["completed_at"] = datetime.now().isoformat()
    results["duration_seconds"] = (datetime.fromisoformat(results["completed_at"]) - datetime.fromisoformat(results["started_at"])).total_seconds()
    
    return results


@app.post("/api/deduplication/run")
async def run_deduplication():
    """Executa o processo de deduplicação em todos os imóveis."""
    duplicate_count = dedup_service.mark_duplicates(db.properties)
    return {
        "message": f"Deduplicação concluída. {duplicate_count} duplicatas identificadas.",
        "duplicates_found": duplicate_count
    }


# ==================== Scraper Execution Endpoints ====================

@app.post("/scrape/all")
async def scrape_all(background_tasks: BackgroundTasks):
    """
    Executa todos os scrapers automaticamente em background.
    Retorna imediatamente - scraping acontece em background.
    """
    from app.scrapers.scraper_manager import run_all_scrapers
    
    # Add task to background
    background_tasks.add_task(run_all_scrapers)
    
    return {
        "message": "Scraping iniciado em background",
        "status": "running",
        "note": "Use GET /scrape/status para verificar o progresso"
    }


@app.get("/scrape/status")
async def get_scrape_status():
    """
    Retorna estatísticas atuais do banco de dados.
    Inclui total de imóveis, por leiloeiro, por estado, etc.
    """
    stats = db.get_stats()
    return {
        "status": "ok",
        "database_stats": stats,
        "timestamp": datetime.now().isoformat()
    }


# ==================== Scraper Monitoring Endpoints ====================

@app.get("/api/scrapers/health")
async def get_all_scrapers_health():
    """
    Obtém relatório de saúde de todos os scrapers monitorados.
    Retorna status, métricas e recomendações para cada scraper.
    """
    monitor = get_scraper_monitor()
    reports = monitor.get_all_health_reports()
    
    # Add Portal Zuk if not in history (always show it)
    scraper_names = [r.scraper_name for r in reports]
    if "Portal Zuk" not in scraper_names:
        from app.services.scraper_monitor import ScraperHealthReport
        reports.append(ScraperHealthReport(
            scraper_name="Portal Zuk",
            status=ScraperStatus.UNKNOWN,
            issues=["No run history available"],
            recommendations=["Run the scraper to collect baseline metrics"]
        ))
    
    return {
        "scrapers": [r.to_dict() for r in reports],
        "total_scrapers": len(reports),
        "healthy_count": sum(1 for r in reports if r.status == ScraperStatus.HEALTHY),
        "degraded_count": sum(1 for r in reports if r.status == ScraperStatus.DEGRADED),
        "failing_count": sum(1 for r in reports if r.status == ScraperStatus.FAILING),
        "unknown_count": sum(1 for r in reports if r.status == ScraperStatus.UNKNOWN),
    }


@app.get("/api/scrapers/health/{scraper_name}")
async def get_scraper_health(scraper_name: str):
    """
    Obtém relatório de saúde detalhado de um scraper específico.
    Inclui status, métricas históricas, problemas identificados e recomendações.
    """
    monitor = get_scraper_monitor()
    report = monitor.get_health_report(scraper_name)
    return report.to_dict()


@app.get("/api/scrapers/metrics/{scraper_name}")
async def get_scraper_metrics(
    scraper_name: str,
    limit: int = Query(10, ge=1, le=100, description="Número de execuções recentes")
):
    """
    Obtém histórico de métricas de um scraper.
    Útil para análise de tendências e diagnóstico de problemas.
    """
    monitor = get_scraper_monitor()
    metrics = monitor.get_metrics_history(scraper_name, limit=limit)
    return {
        "scraper_name": scraper_name,
        "metrics": metrics,
        "total_runs": len(metrics),
    }


@app.post("/api/scrapers/check/{scraper_name}")
async def check_scraper_website(scraper_name: str):
    """
    Executa verificação de saúde rápida no website alvo de um scraper.
    Verifica se o site está acessível e responde corretamente.
    """
    monitor = get_scraper_monitor()
    
    # Map scraper names to their base URLs
    scraper_urls = {
        "Portal Zuk": "https://www.portalzuk.com.br",
        "portal_zuk": "https://www.portalzuk.com.br",
        "Superbid": "https://www.superbid.net",
        "superbid": "https://www.superbid.net",
        "Mega Leilões": "https://www.megaleiloes.com.br",
        "megaleiloes": "https://www.megaleiloes.com.br",
    }
    
    base_url = scraper_urls.get(scraper_name)
    if not base_url:
        raise HTTPException(
            status_code=404, 
            detail=f"Scraper '{scraper_name}' não encontrado ou URL não configurada"
        )
    
    result = monitor.check_scraper_health(scraper_name, base_url)
    return result


@app.get("/api/admin/quality-report")
async def get_quality_report(auctioneer_name: Optional[str] = None):
    """
    Obtém relatório de qualidade dos imóveis.
    
    Args:
        auctioneer_name: Nome opcional do leiloeiro para filtrar
        
    Returns:
        Relatório com métricas de qualidade
    """
    from app.services.quality_report import get_quality_report_service
    
    report_service = get_quality_report_service()
    return report_service.generate_report(auctioneer_name=auctioneer_name)


@app.get("/api/scrapers/summary")
async def get_scrapers_summary():
    """
    Obtém resumo geral do sistema de scrapers.
    Inclui estatísticas agregadas e alertas ativos.
    """
    monitor = get_scraper_monitor()
    reports = monitor.get_all_health_reports()
    
    # Calculate aggregate stats
    total_properties = sum(r.total_properties for r in reports)
    total_runs = sum(r.total_runs for r in reports)
    
    # Collect all active issues
    active_issues = []
    for report in reports:
        if report.status in (ScraperStatus.FAILING, ScraperStatus.DEGRADED):
            for issue in report.issues[:3]:  # Top 3 issues per scraper
                active_issues.append({
                    "scraper": report.scraper_name,
                    "status": report.status.value,
                    "issue": issue,
                })
    
    # Determine overall system health
    if any(r.status == ScraperStatus.FAILING for r in reports):
        overall_status = "critical"
    elif any(r.status == ScraperStatus.DEGRADED for r in reports):
        overall_status = "warning"
    elif all(r.status == ScraperStatus.HEALTHY for r in reports):
        overall_status = "healthy"
    else:
        overall_status = "unknown"
    
    return {
        "overall_status": overall_status,
        "total_scrapers": len(reports),
        "total_runs": total_runs,
        "total_properties_collected": total_properties,
        "active_issues": active_issues,
        "scrapers_by_status": {
            "healthy": sum(1 for r in reports if r.status == ScraperStatus.HEALTHY),
            "degraded": sum(1 for r in reports if r.status == ScraperStatus.DEGRADED),
            "failing": sum(1 for r in reports if r.status == ScraperStatus.FAILING),
            "unknown": sum(1 for r in reports if r.status == ScraperStatus.UNKNOWN),
        },
    }


# ==================== Map Endpoints ====================

@app.get("/api/map/properties")
async def get_map_properties(
    state: Optional[str] = Query(None, description="Filtrar por estado (UF)"),
    city: Optional[str] = Query(None, description="Filtrar por cidade"),
    category: Optional[PropertyCategory] = Query(None, description="Filtrar por categoria"),
    min_value: Optional[float] = Query(None, description="Valor mínimo"),
    max_value: Optional[float] = Query(None, description="Valor máximo"),
    min_discount: Optional[float] = Query(None, description="Desconto mínimo (%)"),
    limit: int = Query(500, ge=1, le=1000, description="Máximo de propriedades"),
):
    """
    Retorna propriedades com coordenadas para exibição no mapa.
    Retorna apenas propriedades únicas (não duplicatas) com coordenadas válidas.
    """
    filters = PropertyFilter(
        state=state,
        city=city,
        category=category,
        min_value=min_value,
        max_value=max_value,
        min_discount=min_discount,
        include_duplicates=False,
    )
    
    properties, _ = db.get_properties(filters=filters, skip=0, limit=limit)
    
    # Filter only properties with valid coordinates
    map_properties = []
    for prop in properties:
        if prop.latitude and prop.longitude:
            map_properties.append({
                "id": prop.id,
                "title": prop.title,
                "category": prop.category.value if prop.category else None,
                "city": prop.city,
                "state": prop.state,
                "latitude": prop.latitude,
                "longitude": prop.longitude,
                "second_auction_value": prop.second_auction_value,
                "discount_percentage": prop.discount_percentage,
                "image_url": prop.image_url,
            })
    
    return {
        "properties": map_properties,
        "total": len(map_properties),
    }


@app.get("/api/map/bounds")
async def get_map_bounds():
    """
    Retorna os limites geográficos de todas as propriedades.
    Útil para centralizar o mapa automaticamente.
    """
    min_lat, max_lat = float('inf'), float('-inf')
    min_lng, max_lng = float('inf'), float('-inf')
    count = 0
    
    for prop in db.properties.values():
        if not prop.is_duplicate and prop.latitude and prop.longitude:
            min_lat = min(min_lat, prop.latitude)
            max_lat = max(max_lat, prop.latitude)
            min_lng = min(min_lng, prop.longitude)
            max_lng = max(max_lng, prop.longitude)
            count += 1
    
    if count == 0:
        # Default to Brazil center
        return {
            "center": {"lat": -14.235, "lng": -51.9253},
            "bounds": None,
            "zoom": 4,
        }
    
    center_lat = (min_lat + max_lat) / 2
    center_lng = (min_lng + max_lng) / 2
    
    return {
        "center": {"lat": center_lat, "lng": center_lng},
        "bounds": {
            "north": max_lat,
            "south": min_lat,
            "east": max_lng,
            "west": min_lng,
        },
        "zoom": 5,
        "property_count": count,
    }


# ==================== Autonomous Scheduler Endpoints ====================

@app.on_event("startup")
async def startup_event():
    """Start the autonomous scheduler on application startup."""
    scheduler = get_autonomous_scheduler()
    scheduler.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the autonomous scheduler on application shutdown."""
    scheduler = get_autonomous_scheduler()
    scheduler.stop()


@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """
    Obtém o status atual do scheduler autônomo.
    Inclui informações sobre jobs agendados, última execução, etc.
    """
    scheduler = get_autonomous_scheduler()
    return scheduler.get_status()


@app.post("/api/scheduler/start")
async def start_scheduler():
    """Inicia o scheduler autônomo."""
    scheduler = get_autonomous_scheduler()
    scheduler.start()
    return {"message": "Scheduler iniciado", "status": scheduler.get_status()}


@app.post("/api/scheduler/stop")
async def stop_scheduler():
    """Para o scheduler autônomo."""
    scheduler = get_autonomous_scheduler()
    scheduler.stop()
    return {"message": "Scheduler parado", "status": scheduler.get_status()}


@app.post("/api/scheduler/analyze-80-20")
async def trigger_80_20_analysis():
    """
    Dispara manualmente a análise 80/20 dos leiloeiros.
    Varre todos os leiloeiros, conta imóveis e atribui prioridades.
    """
    scheduler = get_autonomous_scheduler()
    result = scheduler.trigger_80_20_analysis()
    return result


@app.get("/api/scheduler/catalog")
async def get_auctioneer_catalog():
    """
    Obtém o catálogo completo de leiloeiros.
    Ordenado por número de imóveis (maior para menor).
    """
    scheduler = get_autonomous_scheduler()
    return {
        "auctioneers": scheduler.get_catalog(),
        "total": len(scheduler.catalog),
    }


@app.get("/api/scheduler/ranking")
async def get_80_20_ranking():
    """
    Obtém o ranking 80/20 dos leiloeiros.
    Mostra quais leiloeiros representam 80% do volume de imóveis.
    """
    scheduler = get_autonomous_scheduler()
    return scheduler.get_80_20_ranking()


@app.get("/api/scheduler/platforms")
async def get_platform_groups():
    """
    Obtém leiloeiros agrupados por tipo de plataforma (white-label).
    Útil para identificar quais leiloeiros podem compartilhar o mesmo scraper.
    """
    scheduler = get_autonomous_scheduler()
    return {
        "platforms": scheduler.get_platform_groups(),
        "distribution": scheduler._get_platform_distribution(),
    }


@app.post("/api/scheduler/add-auctioneer")
async def add_auctioneer_to_catalog(
    id: str,
    name: str,
    url: str,
):
    """Adiciona um novo leiloeiro ao catálogo."""
    scheduler = get_autonomous_scheduler()
    auctioneer = scheduler.add_auctioneer(id, name, url)
    return {"message": f"Leiloeiro {name} adicionado", "auctioneer": auctioneer.to_dict()}


# ==================== Background Job Endpoints ====================

@app.post("/api/scheduler/start-background-scraping")
async def start_background_scraping(max_per_scraper: Optional[int] = Query(None, ge=1)):
    """
    Inicia scraping em background de todos os leiloeiros integrados.
    Retorna imediatamente com job_id - scraping acontece em thread separada.
    
    Args:
        max_per_scraper: Máximo de imóveis por leiloeiro (None = sem limite, coleta TODOS)
    """
    scheduler = get_autonomous_scheduler()
    result = scheduler.start_background_scraping(max_per_scraper=max_per_scraper)
    return result


@app.get("/api/scheduler/job-status/{job_id}")
async def get_background_job_status(job_id: str):
    """
    Obtém status de um job de scraping em background.
    Mostra progresso de cada scraper e total de imóveis coletados.
    """
    scheduler = get_autonomous_scheduler()
    return scheduler.get_job_status(job_id)


@app.get("/api/scheduler/jobs")
async def get_all_background_jobs():
    """
    Lista todos os jobs de scraping em background.
    Útil para ver histórico de execuções.
    """
    scheduler = get_autonomous_scheduler()
    return {"jobs": scheduler.get_all_jobs()}


@app.post("/api/scheduler/reset-background-job")
async def reset_background_job():
    """
    Reseta o status do job de background.
    Use após reinício do servidor para limpar jobs travados.
    """
    scheduler = get_autonomous_scheduler()
    return scheduler.reset_background_job()


@app.post("/api/admin/save-data")
async def save_data_to_disk():
    """
    Manually save all data to disk.
    Use this after bulk imports or scraping to persist data.
    """
    success = db.save_to_disk()
    return {
        "success": success,
        "properties_saved": len(db.properties),
        "auctioneers_saved": len(db.auctioneers),
    }


@app.post("/api/admin/cleanup-duplicates")
async def cleanup_duplicates():
    """
    Clean up duplicate properties in the database.
    Groups properties by normalized (auctioneer_id, source_url) key,
    keeps the canonical record (most complete data), and marks others as duplicates.
    """
    result = db.cleanup_duplicates()
    return {
        "success": True,
        **result,
    }


@app.post("/api/admin/reclassify-properties")
async def reclassify_properties():
    """
    Reclassify properties based on title keywords.
    Fixes miscategorized properties where title clearly indicates a different category.
    For example, a property with "Casa" in the title but categorized as "Apartamento"
    will be reclassified as "Casa".
    """
    result = db.reclassify_properties()
    return {
        "success": True,
        **result,
    }


@app.post("/api/admin/full-cleanup")
async def full_cleanup():
    """
    Run full data cleanup: deduplicate and reclassify properties.
    This is a convenience endpoint that runs both cleanup operations.
    """
    dedup_result = db.cleanup_duplicates()
    reclassify_result = db.reclassify_properties()
    
    return {
        "success": True,
        "deduplication": dedup_result,
        "reclassification": reclassify_result,
    }


@app.post("/api/admin/geocode-missing")
async def geocode_missing_properties():
    """
    Geocode all properties that are missing latitude/longitude.
    Uses local lookup table - safe to call in bulk.
    """
    from app.services.geocoding import get_geocoding_service
    
    geocoding = get_geocoding_service()
    updated = 0
    failed = 0
    
    for prop in db.properties.values():
        if prop.latitude is None or prop.longitude is None:
            coords = geocoding.geocode(prop.city, prop.state)
            if coords:
                prop.latitude = coords[0]
                prop.longitude = coords[1]
                updated += 1
            else:
                failed += 1
    
    return {
        "success": True,
        "updated": updated,
        "failed": failed,
        "total_properties": len(db.properties),
    }


@app.post("/api/admin/geocode-batch")
async def geocode_batch(limit: int = 100):
    """
    Geocode properties without coordinates in batch using Nominatim.
    
    Args:
        limit: Maximum number of properties to geocode (default: 100)
    
    Returns:
        Dictionary with updated count and total processed
    """
    from app.services.geocoding import get_geocoding_service
    from app.services.postgres_database import PostgresDatabase
    
    if not isinstance(db, PostgresDatabase):
        raise HTTPException(status_code=400, detail="Geocoding batch only works with PostgreSQL database")
    
    geocoding = get_geocoding_service(use_nominatim=True)
    updated = 0
    failed = 0
    
    # Get properties without coordinates from database
    try:
        # Query properties without coordinates
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, city, state, address FROM properties WHERE (latitude IS NULL OR longitude IS NULL) AND is_duplicate = FALSE LIMIT %s",
                    (limit,)
                )
                rows = cur.fetchall()
        
        for row in rows:
            prop_id = row['id']
            city = row.get('city')
            state = row.get('state')
            address = row.get('address')
            
            if not city or not state:
                failed += 1
                continue
            
            # Try geocoding with full address first, then fallback to city only
            coords = geocoding.geocode(city=city, state=state, address=address, add_offset=False)
            
            if not coords:
                # Fallback: geocode by city only
                coords = geocoding.geocode_by_city(city, state)
            
            if coords:
                lat, lon = coords
                # Update property coordinates
                with db._get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE properties SET latitude = %s, longitude = %s WHERE id = %s",
                            (lat, lon, prop_id)
                        )
                    conn.commit()
                updated += 1
                logger.info(f"Geocoded property {prop_id}: {city}, {state} -> ({lat}, {lon})")
            else:
                failed += 1
                logger.warning(f"Failed to geocode property {prop_id}: {city}, {state}")
        
        return {
            "success": True,
            "updated": updated,
            "failed": failed,
            "total_processed": len(rows),
        }
        
    except Exception as e:
        logger.error(f"Error in geocode_batch: {e}")
        raise HTTPException(status_code=500, detail=f"Error geocoding properties: {str(e)}")


@app.post("/api/admin/import-properties")
async def import_properties_from_json(properties: List[dict]):
    """
    Importa propriedades de uma lista JSON.
    Usado para importar dados coletados localmente para a plataforma.
    Deduplica automaticamente por property_url.
    """
    from app.models.property import Property, PropertyCategory, AuctionType
    import uuid
    
    imported = 0
    skipped = 0
    errors = []
    
    for prop_data in properties:
        try:
            # Convert category and auction_type strings to enums
            category = None
            if prop_data.get('category'):
                try:
                    category = PropertyCategory(prop_data['category'])
                except ValueError:
                    category = PropertyCategory.OUTRO
            
            auction_type = None
            if prop_data.get('auction_type'):
                try:
                    auction_type = AuctionType(prop_data['auction_type'])
                except ValueError:
                    auction_type = AuctionType.OUTROS
            
            # Parse dates
            first_auction_date = None
            if prop_data.get('first_auction_date'):
                try:
                    first_auction_date = datetime.fromisoformat(prop_data['first_auction_date'].replace('Z', '+00:00'))
                except:
                    pass
            
            second_auction_date = None
            if prop_data.get('second_auction_date'):
                try:
                    second_auction_date = datetime.fromisoformat(prop_data['second_auction_date'].replace('Z', '+00:00'))
                except:
                    pass
            
            # Get property_url - use property_url field or fall back to auctioneer_url
            property_url = prop_data.get('property_url') or prop_data.get('auctioneer_url') or ''
            
            # Geocode the property
            from app.services.geocoding import get_geocoding_service
            geocoding = get_geocoding_service()
            coords = geocoding.geocode(prop_data.get('city', ''), prop_data.get('state', ''))
            latitude = coords[0] if coords else None
            longitude = coords[1] if coords else None
            
            # Create Property object
            prop = Property(
                id=prop_data.get('id') or str(uuid.uuid4()),
                title=prop_data.get('title', 'Imóvel em Leilão'),
                address=prop_data.get('address'),
                city=prop_data.get('city', 'Não informado'),
                state=prop_data.get('state', 'SP'),
                neighborhood=prop_data.get('neighborhood'),
                category=category,
                auction_type=auction_type,
                evaluation_value=prop_data.get('evaluation_value'),
                minimum_bid=prop_data.get('minimum_bid'),
                first_auction_value=prop_data.get('first_auction_value'),
                second_auction_value=prop_data.get('second_auction_value'),
                discount_percentage=prop_data.get('discount_percentage'),
                area=prop_data.get('area'),
                bedrooms=prop_data.get('bedrooms'),
                bathrooms=prop_data.get('bathrooms'),
                parking_spaces=prop_data.get('parking_spaces'),
                first_auction_date=first_auction_date,
                second_auction_date=second_auction_date,
                image_url=prop_data.get('image_url'),
                property_url=property_url,
                source_url=property_url,
                auctioneer_name=prop_data.get('auctioneer_name', 'Portal Zuk'),
                auctioneer_url=prop_data.get('auctioneer_url'),
                auctioneer_id=prop_data.get('auctioneer_id', 'portal_zuk'),
                latitude=latitude,
                longitude=longitude,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            # Let the DB handle deduplication using the URL index (O(1) lookup)
            # add_property returns the existing property if duplicate, or the new property if inserted
            result = db.add_property(prop)
            if result.id == prop.id:
                # New property was inserted
                imported += 1
            else:
                # Duplicate detected, existing property was returned
                skipped += 1
                
        except Exception as e:
            errors.append(f"Error importing property: {str(e)}")
    
    # Save to disk after import
    db.save_to_disk()
    
    return {
        "success": True,
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:10],  # Limit errors to first 10
        "total_properties_now": len(db.properties),
        "data_saved": True,
    }


# ==================== Caixa Sync Endpoints ====================

@app.post("/api/sync/caixa")
async def sync_caixa_properties(properties: List[dict], background_tasks: BackgroundTasks):
    """
    Endpoint OTIMIZADO para receber dados da API Caixa.
    
    FLUXO RÁPIDO:
    1. Converte dados do formato Caixa para Property
    2. Salva diretamente no banco (SEM geocoding, SEM deduplicação)
    3. Geocoding e deduplicação rodam em background jobs separados
    
    Isso permite sincronizar 28k+ imóveis em minutos ao invés de horas.
    """
    from app.models.property import Property, PropertyCategory, AuctionType
    import uuid
    
    imported = 0
    updated = 0
    skipped = 0
    
    # Geocoding agora é feito em background (assíncrono)
    # Imóveis são salvos com geocoding_status='pending' e serão processados posteriormente
    # via POST /api/geocoding/start
    
    for caixa_data in properties:
        try:
            # Map Caixa category to PropertyCategory
            caixa_categoria = caixa_data.get('categoria', '').lower()
            if 'apartamento' in caixa_categoria:
                category = PropertyCategory.APARTAMENTO
            elif 'casa' in caixa_categoria:
                category = PropertyCategory.CASA
            elif 'terreno' in caixa_categoria:
                category = PropertyCategory.TERRENO
            elif 'comercial' in caixa_categoria or 'loja' in caixa_categoria:
                category = PropertyCategory.COMERCIAL
            else:
                category = PropertyCategory.OUTRO
            
            # Map Caixa modalidade to AuctionType
            modalidade = caixa_data.get('modalidade', '').lower()
            if 'extrajudicial' in modalidade:
                auction_type = AuctionType.EXTRAJUDICIAL
            elif 'judicial' in modalidade:
                auction_type = AuctionType.JUDICIAL
            elif 'venda direta' in modalidade:
                auction_type = AuctionType.VENDA_DIRETA
            else:
                auction_type = AuctionType.EXTRAJUDICIAL
            
            # Convert values from centavos to reais
            valor_primeira_praca = caixa_data.get('valor_primeira_praca')
            if valor_primeira_praca:
                valor_primeira_praca = valor_primeira_praca / 100
            
            valor_avaliacao = caixa_data.get('valor_avaliacao')
            if valor_avaliacao:
                valor_avaliacao = valor_avaliacao / 100
            
            # Calculate discount
            desconto = caixa_data.get('desconto_percentual')
            if not desconto and valor_avaliacao and valor_primeira_praca:
                desconto = round((1 - valor_primeira_praca / valor_avaliacao) * 100, 2)
            
            # Build address
            endereco = caixa_data.get('endereco', '')
            if not endereco:
                parts = []
                if caixa_data.get('logradouro'):
                    parts.append(caixa_data['logradouro'])
                if caixa_data.get('numero'):
                    parts.append(caixa_data['numero'])
                if caixa_data.get('complemento'):
                    parts.append(caixa_data['complemento'])
                endereco = ', '.join(parts) if parts else 'Endereço não informado'
            
            # Get location info
            city = caixa_data.get('cidade', 'Não informado')
            state = caixa_data.get('estado', 'SP')
            
            # Create unique ID based on numero_imovel
            numero_imovel = caixa_data.get('numero_imovel', str(uuid.uuid4()))
            prop_id = f"caixa-{numero_imovel}"
            
            # Create Property object (sem coordenadas - geocoding será feito em background)
            prop = Property(
                id=prop_id,
                title=endereco[:100] if endereco else 'Imóvel Caixa',
                address=endereco,
                city=city,
                state=state,
                neighborhood=caixa_data.get('bairro'),
                category=category,
                auction_type=auction_type,
                evaluation_value=valor_avaliacao,
                first_auction_value=valor_primeira_praca,
                second_auction_value=valor_primeira_praca,
                discount_percentage=desconto,
                area_total=caixa_data.get('area_total'),
                area_privativa=caixa_data.get('area_construida'),
                image_url=None,
                source_url=caixa_data.get('url', ''),
                auctioneer_id='caixa',
                auctioneer_name=caixa_data.get('leiloeiro_nome', 'Caixa Econômica Federal'),
                auctioneer_url=caixa_data.get('url', ''),
                source='caixa',
                latitude=None,  # Será preenchido pelo geocoding assíncrono
                longitude=None,  # Será preenchido pelo geocoding assíncrono
                accepts_financing=True,
                accepts_fgts=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            # Salva o imóvel usando o método padrão
            existing = db.get_property(prop_id)
            if existing:
                db.add_property(prop, upsert=True)
                updated += 1
            else:
                db.add_property(prop, upsert=False)
                imported += 1
            
            # Marca como pendente de geocoding usando Supabase diretamente (se disponível)
            # Isso permite adicionar campos que não estão no modelo Property
            # Nota: Isso só funciona com PostgreSQL/Supabase. Para SQLite/in-memory, 
            # os campos de geocoding não serão salvos (mas isso é aceitável).
            try:
                from app.services.postgres_database import PostgresDatabase
                # Só tenta atualizar se for PostgresDatabase (Supabase)
                if isinstance(db, PostgresDatabase):
                    import os
                    from supabase import create_client, Client
                    SUPABASE_URL = os.getenv("SUPABASE_URL")
                    SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
                    
                    if SUPABASE_URL and SUPABASE_KEY:
                        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                        supabase_client.table("properties").update({
                            "geocoding_status": "pending",
                            "geocoding_attempts": 0,
                            "latitude": None,
                            "longitude": None,
                        }).eq("id", prop_id).execute()
            except Exception as e:
                # Se não conseguir usar Supabase diretamente, continua normalmente
                # O SQL script add_geocoding_columns.sql deve ser executado primeiro
                logger.debug(f"Não foi possível atualizar geocoding_status (normal se SQL ainda não foi executado ou se não for Supabase): {e}")
                
        except Exception as e:
            skipped += 1
    
    # Save to disk (no-op for SQLite, saves JSON for in-memory)
    db.save_to_disk()
    
    # Agendar geocoding em background
    try:
        geocoding_service = get_geocoding_service()
        background_tasks.add_task(geocoding_service.process_batch, batch_size=100, delay=1.1)
    except Exception as e:
        logger.warning(f"Não foi possível agendar geocoding em background: {e}")
    
    return {
        "success": True,
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "total_properties_now": len(db.properties) if hasattr(db, 'properties') else 0,
        "message": "Sync rápido concluído. Imóveis salvos. Geocoding em processamento em background.",
        "geocoding_status": "scheduled"
    }


@app.get("/api/admin/geocoding/status")
async def geocoding_status():
    """
    Retorna o status do processamento de geocoding em background.
    """
    try:
        service = get_geocoding_service()
        return service.get_status()
    except Exception as e:
        return {"error": str(e), "is_running": False}


@app.post("/api/admin/geocoding/start")
async def start_geocoding(
    background_tasks: BackgroundTasks,
    batch_size: int = 100
):
    """
    Inicia manualmente o processamento de geocoding em background.
    Útil para processar imóveis pendentes.
    """
    try:
        service = get_geocoding_service()
        
        if service.is_running:
            return {
                "status": "already_running",
                "message": "Geocoding já está em execução"
            }
        
        background_tasks.add_task(service.process_batch, batch_size=batch_size, delay=1.1)
        
        return {
            "status": "started",
            "message": f"Geocoding iniciado para {batch_size} imóveis",
            "batch_size": batch_size
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/audit/stats")
async def audit_stats():
    """
    Retorna estatísticas da auditoria de qualidade.
    """
    auditor = get_quality_auditor()
    return auditor.get_stats()


@app.post("/api/admin/audit/reset")
async def reset_audit_stats():
    """
    Reseta as estatísticas de auditoria.
    """
    auditor = get_quality_auditor()
    auditor.reset_stats()
    return {"status": "ok", "message": "Estatísticas resetadas"}


@app.post("/api/admin/audit-data")
async def audit_and_fix_data(fix: bool = False):
    """
    Audita qualidade dos dados e opcionalmente corrige problemas.
    
    Args:
        fix: Se True, corrige os problemas encontrados
    """
    import psycopg2
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "issues": {},
        "fixed": {} if fix else None
    }
    
    # 1. Cidades em maiúsculas
    cur.execute('''
        SELECT COUNT(*) FROM properties 
        WHERE city = UPPER(city) AND city IS NOT NULL AND LENGTH(city) > 2
    ''')
    uppercase_cities = cur.fetchone()[0]
    report["issues"]["uppercase_cities"] = uppercase_cities
    
    if fix and uppercase_cities > 0:
        cur.execute('''
            UPDATE properties SET city = INITCAP(city)
            WHERE city = UPPER(city) AND city IS NOT NULL
        ''')
        report["fixed"]["uppercase_cities"] = cur.rowcount
    
    # 2. Bairros em maiúsculas
    cur.execute('''
        SELECT COUNT(*) FROM properties 
        WHERE neighborhood = UPPER(neighborhood) AND neighborhood IS NOT NULL AND LENGTH(neighborhood) > 2
    ''')
    uppercase_neighborhoods = cur.fetchone()[0]
    report["issues"]["uppercase_neighborhoods"] = uppercase_neighborhoods
    
    if fix and uppercase_neighborhoods > 0:
        cur.execute('''
            UPDATE properties SET neighborhood = INITCAP(neighborhood)
            WHERE neighborhood = UPPER(neighborhood) AND neighborhood IS NOT NULL
        ''')
        report["fixed"]["uppercase_neighborhoods"] = cur.rowcount
    
    # 3. Imagens inválidas
    cur.execute('''
        SELECT COUNT(*) FROM properties 
        WHERE image_url LIKE '%%facebook%%'
           OR image_url LIKE '%%logo%%'
           OR image_url LIKE '%%placeholder%%'
           OR image_url LIKE '%%no-image%%'
    ''')
    invalid_images = cur.fetchone()[0]
    report["issues"]["invalid_images"] = invalid_images
    
    if fix and invalid_images > 0:
        cur.execute('''
            UPDATE properties SET image_url = NULL
            WHERE image_url LIKE '%%facebook%%'
               OR image_url LIKE '%%logo%%'
               OR image_url LIKE '%%placeholder%%'
               OR image_url LIKE '%%no-image%%'
        ''')
        report["fixed"]["invalid_images"] = cur.rowcount
    
    # 4. URLs vazias da Caixa
    cur.execute('''
        SELECT COUNT(*) FROM properties 
        WHERE id LIKE 'caixa-%%'
          AND (source_url IS NULL OR source_url = '')
    ''')
    missing_caixa_urls = cur.fetchone()[0]
    report["issues"]["missing_caixa_urls"] = missing_caixa_urls
    
    if fix and missing_caixa_urls > 0:
        cur.execute('''
            UPDATE properties 
            SET source_url = CONCAT('https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=', REPLACE(id, 'caixa-', ''))
            WHERE id LIKE 'caixa-%%'
              AND (source_url IS NULL OR source_url = '')
        ''')
        report["fixed"]["missing_caixa_urls"] = cur.rowcount
    
    # 5. Imóveis sem source_url (exceto Caixa já tratada)
    cur.execute('''
        SELECT COUNT(*) FROM properties 
        WHERE (source_url IS NULL OR source_url = '')
          AND id NOT LIKE 'caixa-%%'
    ''')
    report["issues"]["missing_source_urls_other"] = cur.fetchone()[0]
    
    # 6. Estatísticas gerais
    cur.execute('SELECT COUNT(*) FROM properties')
    report["total_properties"] = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM properties WHERE image_url IS NOT NULL AND image_url != \'\'')
    report["properties_with_image"] = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM properties WHERE source_url IS NOT NULL AND source_url != \'\'')
    report["properties_with_url"] = cur.fetchone()[0]
    
    if fix:
        conn.commit()
    
    cur.close()
    conn.close()
    
    return report


@app.post("/api/admin/run-maintenance")
async def run_maintenance(background_tasks: BackgroundTasks):
    """
    Executa manutenção em background.
    """
    from scripts.audit_data_quality import audit_data_quality
    
    def run_task():
        audit_data_quality(fix=True)
        # Tentar buscar imagens da Caixa também
        try:
            from scripts.fetch_caixa_images import fetch_and_update_images
            fetch_and_update_images(limit=50)
        except ImportError:
            pass
    
    background_tasks.add_task(run_task)
    
    return {"status": "started", "message": "Manutenção iniciada em background"}


@app.get("/api/admin/images/stats")
async def image_filter_stats():
    """
    Retorna estatísticas do filtro de imagens.
    """
    blacklist = get_image_blacklist()
    return blacklist.get_stats()


@app.post("/api/admin/images/blacklist/add")
async def add_to_image_blacklist(url: str, is_pattern: bool = False):
    """
    Adiciona uma URL ou padrão à blacklist de imagens.
    """
    blacklist = get_image_blacklist()
    blacklist.add_to_blacklist(url, is_pattern)
    return {"status": "ok", "message": f"Adicionado à blacklist: {url}"}


@app.get("/api/stats/sources")
async def get_stats_by_source():
    """
    Obtém estatísticas separadas por fonte (Caixa vs Leiloeiros).
    """
    caixa_props = [p for p in db.properties.values() if p.source == 'caixa' and not p.is_duplicate]
    leiloeiros_props = [p for p in db.properties.values() if p.source != 'caixa' and not p.is_duplicate]
    
    return {
        "total_properties": len(db.properties),
        "unique_properties": len(caixa_props) + len(leiloeiros_props),
        "sources": {
            "caixa": {
                "total": len(caixa_props),
                "by_state": _count_by_field(caixa_props, 'state'),
                "by_category": _count_by_field(caixa_props, 'category'),
            },
            "leiloeiros": {
                "total": len(leiloeiros_props),
                "by_auctioneer": _count_by_field(leiloeiros_props, 'auctioneer_id'),
                "by_state": _count_by_field(leiloeiros_props, 'state'),
                "by_category": _count_by_field(leiloeiros_props, 'category'),
            }
        }
    }




def _count_by_field(properties: list, field: str) -> dict:
    """Helper to count properties by a field."""
    counts = {}
    for p in properties:
        value = getattr(p, field, None)
        if value:
            if hasattr(value, 'value'):  # Enum
                value = value.value
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


# ==================== ASAAS ENDPOINTS ====================

@app.post("/api/asaas/create-checkout")
async def create_asaas_checkout(
    user_id: str = Query(...),
    user_name: str = Query(...), 
    user_email: str = Query(...),
    plan: str = Query("monthly")
):
    """Cria link de checkout para assinatura"""
    result = await asaas_service.create_payment_link(user_id, user_name, user_email, plan)
    if result["success"]:
        return result
    raise HTTPException(status_code=400, detail=result.get("error"))

@app.post("/api/asaas/webhook")
async def asaas_webhook(request: Request):
    """Webhook do Asaas para processar pagamentos"""
    try:
        payload = await request.json()
        result = asaas_service.handle_webhook(payload, db)
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"Erro no webhook Asaas: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ==================== USER PROFILE ENDPOINTS ====================

@app.get("/api/user/profile/{user_id}")
async def get_user_profile(user_id: str):
    """Retorna perfil do usuário"""
    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, email, name, role, subscription_status, subscription_plan,
                           trial_end_date, trial_views_used, trial_views_limit,
                           subscription_end_date
                    FROM user_profiles WHERE id = %s::uuid
                """, (user_id,))
                result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar perfil: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/user/check-access/{user_id}")
async def check_user_access(user_id: str):
    """Verifica se usuário pode visualizar imóveis"""
    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT can_view_property(%s::uuid)", (user_id,))
                can_view = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT subscription_status, trial_views_used, trial_views_limit,
                           trial_end_date, subscription_end_date
                    FROM user_profiles WHERE id = %s::uuid
                """, (user_id,))
                profile = cur.fetchone()
        
        if not profile:
            return {"can_view": False, "reason": "user_not_found"}
        
        return {
            "can_view": can_view,
            "status": profile["subscription_status"],
            "trial_views_used": profile["trial_views_used"],
            "trial_views_limit": profile["trial_views_limit"],
            "trial_end_date": profile["trial_end_date"].isoformat() if profile["trial_end_date"] else None,
            "subscription_end_date": profile["subscription_end_date"].isoformat() if profile["subscription_end_date"] else None
        }
    except Exception as e:
        logger.error(f"Erro ao verificar acesso: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/user/increment-view/{user_id}")
async def increment_user_view(user_id: str, property_id: str = Query(...)):
    """Incrementa contador de views e registra visualização"""
    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                # Incrementar trial view
                cur.execute("SELECT increment_trial_view(%s::uuid)", (user_id,))
                
                # Registrar visualização
                cur.execute("""
                    INSERT INTO property_views (user_id, property_id, source)
                    VALUES (%s::uuid, %s, 'detail')
                """, (user_id, property_id))
            conn.commit()
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Erro ao incrementar view: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ANALYTICS ENDPOINTS ====================

@app.post("/api/analytics/search")
async def log_search(
    user_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    filters: Optional[str] = Query(None),  # JSON string
    results_count: int = Query(0)
):
    """Registra busca para analytics"""
    try:
        filters_dict = json.loads(filters) if filters else None
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO search_logs (user_id, session_id, search_filters, results_count)
                    VALUES (%s, %s, %s::jsonb, %s)
                """, (user_id, session_id, json.dumps(filters_dict) if filters_dict else None, results_count))
            conn.commit()
        return {"status": "logged"}
    except Exception as e:
        logger.error(f"Erro ao registrar busca: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/users")
async def get_all_users(limit: int = Query(100), offset: int = Query(0)):
    """Lista todos os usuários (admin)"""
    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, email, name, role, subscription_status, subscription_plan,
                           trial_views_used, trial_views_limit, created_at, last_login
                    FROM user_profiles
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (limit, offset))
                users = cur.fetchall()
                
                cur.execute("SELECT COUNT(*) FROM user_profiles")
                total = cur.fetchone()[0]
        
        return {"users": [dict(u) for u in users], "total": total}
    except Exception as e:
        logger.error(f"Erro ao buscar usuários: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/stats")
async def get_admin_stats():
    """Estatísticas gerais para admin"""
    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                # Total usuários
                cur.execute("SELECT COUNT(*) FROM user_profiles")
                total_users = cur.fetchone()[0]
                
                # Por status
                cur.execute("""
                    SELECT subscription_status, COUNT(*) 
                    FROM user_profiles 
                    GROUP BY subscription_status
                """)
                by_status = {row[0]: row[1] for row in cur.fetchall()}
                
                # Buscas hoje
                cur.execute("""
                    SELECT COUNT(*) FROM search_logs 
                    WHERE created_at >= CURRENT_DATE
                """)
                searches_today = cur.fetchone()[0]
                
                # Views hoje
                cur.execute("""
                    SELECT COUNT(*) FROM property_views 
                    WHERE created_at >= CURRENT_DATE
                """)
                views_today = cur.fetchone()[0]
        
        return {
            "total_users": total_users,
            "by_status": by_status,
            "searches_today": searches_today,
            "views_today": views_today
        }
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas admin: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/search-analytics")
async def get_search_analytics(days: int = Query(30), limit: int = Query(100)):
    """Analytics de buscas"""
    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                # Top estados
                cur.execute("""
                    SELECT search_filters->>'state' as state, COUNT(*) as count
                    FROM search_logs
                    WHERE search_filters->>'state' IS NOT NULL
                    AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY search_filters->>'state'
                    ORDER BY count DESC
                    LIMIT 10
                """, (days,))
                top_states = [{"state": r[0], "count": r[1]} for r in cur.fetchall()]
                
                # Top categorias
                cur.execute("""
                    SELECT search_filters->>'category' as category, COUNT(*) as count
                    FROM search_logs
                    WHERE search_filters->>'category' IS NOT NULL
                    AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY search_filters->>'category'
                    ORDER BY count DESC
                    LIMIT 10
                """, (days,))
                top_categories = [{"category": r[0], "count": r[1]} for r in cur.fetchall()]
                
                # Faixas de preço
                cur.execute("""
                    SELECT 
                        CASE 
                            WHEN (search_filters->>'max_value')::numeric <= 100000 THEN 'Até R$ 100k'
                            WHEN (search_filters->>'max_value')::numeric <= 300000 THEN 'R$ 100k - 300k'
                            WHEN (search_filters->>'max_value')::numeric <= 500000 THEN 'R$ 300k - 500k'
                            WHEN (search_filters->>'max_value')::numeric <= 1000000 THEN 'R$ 500k - 1M'
                            ELSE 'Acima de R$ 1M'
                        END as price_range,
                        COUNT(*) as count
                    FROM search_logs
                    WHERE search_filters->>'max_value' IS NOT NULL
                    AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY price_range
                    ORDER BY count DESC
                """, (days,))
                price_ranges = [{"range": r[0], "count": r[1]} for r in cur.fetchall()]
        
        return {
            "top_states": top_states,
            "top_categories": top_categories,
            "price_ranges": price_ranges
        }
    except Exception as e:
        logger.error(f"Erro ao buscar analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PIPELINE ENDPOINTS ====================

@app.post("/api/pipeline/run")
async def run_pipeline(
    source: str = Query("manual"),
    skip_geocoding: bool = Query(False)
):
    """Executa pipeline completo para todos os leiloeiros"""
    stats = await scraper_pipeline.run_all_auctioneers()
    return stats

@app.post("/api/pipeline/run-auctioneer/{slug}")
async def run_pipeline_for_auctioneer(slug: str, skip_geocoding: bool = Query(False)):
    """Executa pipeline para um leiloeiro específico"""
    stats = await scraper_pipeline.run_for_auctioneer(slug)
    return stats

@app.post("/api/pipeline/normalize")
async def normalize_properties(properties: List[dict]):
    """Normaliza uma lista de imóveis (teste)"""
    normalized = await ai_normalizer.normalize_batch(properties)
    return {"normalized": normalized}

@app.post("/api/pipeline/geocode")
async def geocode_properties(properties: List[dict]):
    """Geocodifica uma lista de imóveis (teste)"""
    geocoded = await geocoding_service.geocode_batch(properties)
    return {"geocoded": geocoded}

@app.post("/api/pipeline/normalize-existing")
async def normalize_existing_properties(limit: int = Query(100)):
    """Normaliza imóveis existentes no banco que têm categoria 'Outro'"""
    
    with db._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, description, address, city, state, category
                FROM properties
                WHERE category = 'Outro' OR category IS NULL OR city IS NULL
                LIMIT %s
            """, (limit,))
            
            rows = cur.fetchall()
            properties = [dict(row) for row in rows]
    
    if not properties:
        return {"message": "Nenhum imóvel para normalizar"}
    
    normalized = await ai_normalizer.normalize_batch(properties)
    
    # Atualizar no banco
    updated = 0
    with db._get_connection() as conn:
        with conn.cursor() as cur:
            for prop in normalized:
                cur.execute("""
                    UPDATE properties SET
                        category = %s,
                        city = %s,
                        state = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (prop.get('category'), prop.get('city'), prop.get('state'), prop['id']))
                updated += 1
            conn.commit()
    
    return {"normalized": updated, "total": len(properties)}

@app.post("/api/pipeline/geocode-existing")
async def geocode_existing_properties(limit: int = Query(50)):
    """Geocodifica imóveis existentes que não têm coordenadas"""
    
    with db._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, address, city, state
                FROM properties
                WHERE (latitude IS NULL OR longitude IS NULL)
                AND (city IS NOT NULL OR address IS NOT NULL)
                LIMIT %s
            """, (limit,))
            
            rows = cur.fetchall()
            properties = [dict(row) for row in rows]
    
    if not properties:
        return {"message": "Nenhum imóvel para geocodificar"}
    
    geocoded = await geocoding_service.geocode_batch(properties)
    
    # Atualizar no banco
    updated = 0
    with db._get_connection() as conn:
        with conn.cursor() as cur:
            for prop in geocoded:
                if prop.get('latitude') and prop.get('longitude'):
                    cur.execute("""
                        UPDATE properties SET
                            latitude = %s,
                            longitude = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (prop['latitude'], prop['longitude'], prop['id']))
                    updated += 1
            conn.commit()
    
    return {"geocoded": updated, "total": len(properties)}

# ==================== SCRAPER ENDPOINTS ====================

@app.post("/api/scraper/run-all")
async def run_all_scrapers(
    skip_geocoding: bool = False,
    limit: Optional[int] = None,
    background_tasks: BackgroundTasks = None
):
    """Executa scraping de todos os leiloeiros (pode demorar horas)"""
    
    if background_tasks:
        # Executar em background
        background_tasks.add_task(scraper_orchestrator.run_all, skip_geocoding, limit)
        return {"status": "started", "message": "Scraping iniciado em background"}
    
    # Executar sincrono (para testes com limit pequeno)
    stats = await scraper_orchestrator.run_all(skip_geocoding, limit)
    return stats


@app.post("/api/scraper/run-single/{auctioneer_id}")
async def run_single_scraper(auctioneer_id: str, skip_geocoding: bool = False):
    """Executa scraping de um único leiloeiro"""
    
    try:
        logger.info(f"Iniciando scraping do leiloeiro {auctioneer_id}")
        
        result = await scraper_orchestrator.run_single(auctioneer_id, skip_geocoding)
        
        logger.info(f"Resultado do scraping: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Erro no scraping do leiloeiro {auctioneer_id}: {e}")
        logger.error(traceback.format_exc())
        return {"error": str(e), "auctioneer_id": auctioneer_id}


@app.get("/api/scraper/status")
async def get_scraper_status():
    """Retorna status atual do scraper"""
    
    return scraper_orchestrator.stats


@app.get("/api/scraper/auctioneers")
async def list_auctioneers(status: Optional[str] = None, limit: int = 100):
    """Lista leiloeiros e seus status"""
    
    query = """
        SELECT id, name, website, is_active, property_count, 
               scrape_status, scrape_error, last_scrape
        FROM auctioneers
        WHERE 1=1
    """
    params = []
    
    if status:
        query += " AND scrape_status = %s"
        params.append(status)
    
    query += " ORDER BY property_count DESC LIMIT %s"
    params.append(limit)
    
    with db._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            # Rows are already dicts due to dict_row factory, so return directly
            auctioneers = list(cur.fetchall())
    
    return {"auctioneers": auctioneers, "total": len(auctioneers)}


# ==================== DISCOVERY ENDPOINTS ====================

@app.post("/api/discovery/run")
async def run_discovery(
    limit: Optional[int] = Query(None, description="Limite de leiloeiros"),
    force: bool = Query(False, description="Forçar redescoberta")
):
    """Executa descoberta de estrutura para leiloeiros pendentes"""
    try:
        result = await discovery_orchestrator.run_discovery(limit=limit, force=force)
        return result
    except Exception as e:
        logger.error(f"Erro na descoberta: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/discovery/single/{auctioneer_id}")
async def run_single_discovery(auctioneer_id: str):
    """Executa descoberta para um leiloeiro específico"""
    try:
        result = await discovery_orchestrator.run_single_discovery(auctioneer_id)
        return result
    except Exception as e:
        logger.error(f"Erro na descoberta única: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/discovery/stats")
async def get_discovery_stats():
    """Retorna estatísticas de descoberta"""
    try:
        return discovery_orchestrator.get_discovery_stats()
    except Exception as e:
        logger.error(f"Erro ao obter stats de descoberta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scraper/run-smart")
async def run_smart_scraper(
    limit: Optional[int] = Query(None),
    skip_geocoding: bool = Query(True)
):
    """Executa scraping inteligente usando configurações descobertas"""
    try:
        result = await scraper_orchestrator.run_all_smart(
            skip_geocoding=skip_geocoding,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Erro no scraping inteligente: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/discovery/rediscovery")
async def run_rediscovery(
    limit: Optional[int] = Query(None, description="Limite de leiloeiros")
):
    """Executa re-descoberta para leiloeiros que precisam atualização"""
    try:
        result = await discovery_orchestrator.run_rediscovery(limit=limit)
        return result
    except Exception as e:
        logger.error(f"Erro na re-descoberta: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/discovery/needs-rediscovery")
async def get_needs_rediscovery():
    """Lista leiloeiros que precisam de re-descoberta"""
    try:
        import psycopg
        from psycopg.rows import dict_row
        
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL não configurada")
        
        conn = psycopg.connect(database_url, row_factory=dict_row)
        conn.autocommit = True
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, website, property_count, 
                       last_discovery_at, discovery_status,
                       validation_metrics->>'consecutive_failures' as failures
                FROM auctioneers 
                WHERE website IS NOT NULL
                ORDER BY property_count DESC NULLS LAST
            """)
            
            results = []
            for row in cur.fetchall():
                auc = dict(row)
                needs, reason = structure_validator.needs_rediscovery(auc)
                if needs:
                    results.append({
                        "id": auc["id"],
                        "name": auc["name"],
                        "property_count": auc["property_count"],
                        "reason": reason,
                        "last_discovery": auc["last_discovery_at"]
                    })
        
        conn.close()
        return {"total": len(results), "auctioneers": results}
        
    except Exception as e:
        logger.error(f"Erro ao verificar re-descoberta: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/discovery/check-structure/{auctioneer_id}")
async def check_structure_changed(auctioneer_id: str):
    """Verifica se a estrutura de um site mudou"""
    try:
        import psycopg
        from psycopg.rows import dict_row
        
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL não configurada")
        
        conn = psycopg.connect(database_url, row_factory=dict_row)
        conn.autocommit = True
        
        with conn.cursor() as cur:
            cur.execute(
                "SELECT website, structure_hash, scrape_config FROM auctioneers WHERE id = %s",
                (auctioneer_id,)
            )
            row = cur.fetchone()
        
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Leiloeiro não encontrado")
        
        stored_hash = row["structure_hash"]
        if not stored_hash and row["scrape_config"]:
            config = row["scrape_config"]
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except:
                    config = {}
            if config.get("validation") and config["validation"].get("structure_hash"):
                stored_hash = config["validation"]["structure_hash"]
        
        changed, new_hash = await structure_validator.check_structure_changed(
            row["website"], stored_hash
        )
        
        return {
            "changed": changed,
            "old_hash": stored_hash[:8] + "..." if stored_hash else None,
            "new_hash": new_hash[:8] + "..." if new_hash else None
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar estrutura: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))