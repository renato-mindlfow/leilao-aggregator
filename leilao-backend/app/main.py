from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime

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


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# ==================== Properties Endpoints ====================

@app.get("/api/properties", response_model=dict)
async def list_properties(
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(18, ge=1, le=100, description="Itens por página"),
    state: Optional[str] = Query(None, description="Filtrar por estado (UF)"),
    city: Optional[str] = Query(None, description="Filtrar por cidade"),
    neighborhood: Optional[str] = Query(None, description="Filtrar por bairro"),
    category: Optional[PropertyCategory] = Query(None, description="Filtrar por categoria"),
    auction_type: Optional[AuctionType] = Query(None, description="Filtrar por tipo de leilão"),
    min_value: Optional[float] = Query(None, description="Valor mínimo"),
    max_value: Optional[float] = Query(None, description="Valor máximo"),
    min_discount: Optional[float] = Query(None, description="Desconto mínimo (%)"),
    auctioneer_id: Optional[str] = Query(None, description="Filtrar por leiloeiro"),
    search: Optional[str] = Query(None, description="Termo de busca"),
    include_duplicates: bool = Query(False, description="Incluir duplicatas"),
):
    """Lista imóveis com filtros e paginação."""
    filters = PropertyFilter(
        state=state,
        city=city,
        neighborhood=neighborhood,
        category=category,
        auction_type=auction_type,
        min_value=min_value,
        max_value=max_value,
        min_discount=min_discount,
        auctioneer_id=auctioneer_id,
        search_term=search,
        include_duplicates=include_duplicates,
    )
    
    skip = (page - 1) * limit
    properties, total = db.get_properties(filters=filters, skip=skip, limit=limit)
    
    total_pages = (total + limit - 1) // limit
    
    return {
        "items": [p.model_dump() for p in properties],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


@app.get("/api/properties/{property_id}", response_model=Property)
async def get_property(property_id: str):
    """Obtém detalhes de um imóvel específico."""
    property_obj = db.get_property(property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    return property_obj


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
    """Inicia scrapers para todos os leiloeiros ativos."""
    active_auctioneers = [a for a in db.get_auctioneers() if a.is_active]
    
    for auctioneer in active_auctioneers:
        db.update_auctioneer_scrape_status(auctioneer.id, "queued")
    
    return {
        "message": f"Scrapers enfileirados para {len(active_auctioneers)} leiloeiros",
        "count": len(active_auctioneers)
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
async def sync_caixa_properties(properties: List[dict]):
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
    
    # Coordenadas aproximadas por estado (geocoding rápido)
    STATE_COORDS = {
        "AC": (-9.97499, -67.8243), "AL": (-9.66599, -35.735),
        "AP": (0.034934, -51.0694), "AM": (-3.11903, -60.0217),
        "BA": (-12.9714, -38.5014), "CE": (-3.71722, -38.5434),
        "DF": (-15.7801, -47.9292), "ES": (-20.2976, -40.2958),
        "GO": (-16.6869, -49.2648), "MA": (-2.52972, -44.3028),
        "MT": (-15.601, -56.0974), "MS": (-20.4697, -54.6201),
        "MG": (-19.9167, -43.9345), "PA": (-1.45502, -48.4902),
        "PB": (-7.11509, -34.8641), "PR": (-25.4284, -49.2733),
        "PE": (-8.04756, -34.877), "PI": (-5.08921, -42.8016),
        "RJ": (-22.9068, -43.1729), "RN": (-5.79448, -35.211),
        "RS": (-30.0346, -51.2177), "RO": (-8.76077, -63.8999),
        "RR": (2.81954, -60.6714), "SC": (-27.5954, -48.548),
        "SP": (-23.5505, -46.6333), "SE": (-10.9472, -37.0731),
        "TO": (-10.1689, -48.3317),
    }
    
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
            
            # Get coordinates from state (FAST - no API call)
            city = caixa_data.get('cidade', 'Não informado')
            state = caixa_data.get('estado', 'SP')
            coords = STATE_COORDS.get(state, (-15.7801, -47.9292))
            latitude, longitude = coords
            
            # Create unique ID based on numero_imovel
            numero_imovel = caixa_data.get('numero_imovel', str(uuid.uuid4()))
            prop_id = f"caixa-{numero_imovel}"
            
            # Create Property object
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
                latitude=latitude,
                longitude=longitude,
                accepts_financing=True,
                accepts_fgts=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            # Use add_property method (works with both in-memory and SQLite)
            existing = db.get_property(prop_id)
            if existing:
                db.add_property(prop, upsert=True)
                updated += 1
            else:
                db.add_property(prop, upsert=False)
                imported += 1
                
        except Exception as e:
            skipped += 1
    
    # Save to disk (no-op for SQLite, saves JSON for in-memory)
    db.save_to_disk()
    
    # NOTE: Geocoding e deduplicação rodam em background jobs separados
    # Use POST /api/admin/geocode-missing para geocoding
    # Use POST /api/deduplication/run para deduplicação
    
    return {
        "success": True,
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "total_properties_now": len(db.properties),
        "message": "Sync rápido concluído. Geocoding e deduplicação rodam em background.",
    }


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
