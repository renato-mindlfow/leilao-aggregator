#!/usr/bin/env python3
"""
EXECUTA SCRAPERS VERIFICADOS E SALVA NO SUPABASE
Scrapers com paginação completa e filtro de imóveis.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import json
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

# Importar normalizador
from app.utils.normalizer import normalize_property as normalize_property_fields, normalize_state, normalize_category, normalize_city

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar Supabase
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL e SUPABASE_KEY devem estar configurados no .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def generate_dedup_key(auctioneer_id: str, source_url: str) -> str:
    """Gera chave de deduplicação."""
    import hashlib
    key = f"{auctioneer_id}:{source_url}"
    return hashlib.md5(key.encode()).hexdigest()


def normalize_property(prop: Dict, auctioneer_id: str) -> Dict:
    """Normaliza propriedade para formato do banco."""
    
    # PRIMEIRO: Aplicar normalização de campos (estado, categoria, cidade)
    prop = normalize_property_fields(prop)
    
    # Gerar ID único
    source_url = prop.get("source_url", prop.get("url", ""))
    dedup_key = generate_dedup_key(auctioneer_id, source_url)
    
    return {
        "id": dedup_key,
        "dedup_key": dedup_key,
        "title": prop.get("title", "Imóvel")[:500],
        "category": prop.get("category", "Outro"),  # Já normalizado
        "auction_type": prop.get("auction_type", "Extrajudicial"),
        "state": prop.get("state", "XX"),  # Já normalizado
        "city": prop.get("city", "Não informada"),  # Já normalizado
        "address": prop.get("address", ""),
        "description": prop.get("description", ""),
        "evaluation_value": prop.get("evaluation_value"),
        "first_auction_value": prop.get("first_auction_value"),
        "second_auction_value": prop.get("second_auction_value"),
        "discount_percentage": prop.get("discount_percentage"),
        "first_auction_date": prop.get("first_auction_date"),
        "second_auction_date": prop.get("second_auction_date"),
        "image_url": prop.get("image_url", ""),
        "source_url": source_url,
        "auctioneer_id": auctioneer_id,
        "auctioneer_name": prop.get("auctioneer_name", ""),
        "auctioneer_url": prop.get("auctioneer_url", ""),
        "source": auctioneer_id,
        "is_active": True,
        "is_duplicate": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "last_seen_at": datetime.now().isoformat(),
    }


def save_properties_to_supabase(properties: List[Dict], auctioneer_id: str) -> Dict:
    """Salva propriedades no Supabase com upsert."""
    
    stats = {
        "total": len(properties),
        "inserted": 0,
        "updated": 0,
        "errors": 0,
    }
    
    if not properties:
        return stats
    
    # Normalizar todas as propriedades
    normalized = []
    for prop in properties:
        try:
            norm = normalize_property(prop, auctioneer_id)
            normalized.append(norm)
        except Exception as e:
            logger.error(f"Erro ao normalizar: {e}")
            stats["errors"] += 1
    
    # Upsert em lotes de 100
    batch_size = 100
    for i in range(0, len(normalized), batch_size):
        batch = normalized[i:i+batch_size]
        
        try:
            # Upsert usando dedup_key como chave
            result = supabase.table("properties").upsert(
                batch,
                on_conflict="id"
            ).execute()
            
            if result.data:
                stats["inserted"] += len(result.data)
                logger.info(f"  💾 Lote {i//batch_size + 1}: {len(result.data)} salvos")
            
        except Exception as e:
            logger.error(f"  ❌ Erro no lote {i//batch_size + 1}: {e}")
            stats["errors"] += len(batch)
    
    return stats


def update_auctioneer_status(auctioneer_id: str, success: bool, count: int):
    """Atualiza status do leiloeiro no banco."""
    try:
        update_data = {
            "last_scrape": datetime.now().isoformat(),
            "scrape_status": "success" if success else "error",
            "property_count": count,
            "updated_at": datetime.now().isoformat(),
        }
        
        supabase.table("auctioneers").update(update_data).eq("id", auctioneer_id).execute()
        logger.info(f"  📊 Status do leiloeiro atualizado")
        
    except Exception as e:
        logger.warning(f"  ⚠️ Erro ao atualizar status: {e}")


def run_scraper(scraper_class, auctioneer_id: str, name: str, max_pages: int = 50) -> Dict:
    """Executa um scraper e salva resultados."""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🔍 {name}")
    logger.info(f"{'='*60}")
    
    result = {
        "auctioneer_id": auctioneer_id,
        "name": name,
        "status": "error",
        "scraped": 0,
        "saved": 0,
        "errors": 0,
    }
    
    try:
        # Executar scraper
        logger.info(f"  ⏳ Executando scraper...")
        scraper = scraper_class(headless=True)
        properties = scraper.scrape(max_properties=None, max_pages=max_pages)
        
        result["scraped"] = len(properties)
        logger.info(f"  📦 {len(properties)} imóveis extraídos")
        
        if not properties:
            logger.warning(f"  ⚠️ Nenhum imóvel extraído")
            result["status"] = "no_data"
            update_auctioneer_status(auctioneer_id, False, 0)
            return result
        
        # Salvar no Supabase
        logger.info(f"  💾 Salvando no Supabase...")
        save_stats = save_properties_to_supabase(properties, auctioneer_id)
        
        result["saved"] = save_stats["inserted"]
        result["errors"] = save_stats["errors"]
        result["status"] = "success"
        
        logger.info(f"  ✅ {save_stats['inserted']} salvos, {save_stats['errors']} erros")
        
        # Atualizar status do leiloeiro
        update_auctioneer_status(auctioneer_id, True, len(properties))
        
    except Exception as e:
        logger.error(f"  ❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        result["status"] = "error"
        result["error"] = str(e)
        update_auctioneer_status(auctioneer_id, False, 0)
    
    return result


def main():
    """Executa todos os scrapers verificados."""
    
    logger.info("="*70)
    logger.info("EXECUÇÃO DE SCRAPERS VERIFICADOS - PRODUÇÃO")
    logger.info(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)
    
    results = []
    
    # 1. Mega Leilões (Playwright com paginação)
    try:
        from app.scrapers.megaleiloes_playwright import MegaLeiloesPlaywrightScraper
        result = run_scraper(
            MegaLeiloesPlaywrightScraper,
            "megaleiloes",
            "Mega Leilões",
            max_pages=20
        )
        results.append(result)
    except ImportError as e:
        logger.error(f"❌ Erro ao importar MegaLeiloesPlaywrightScraper: {e}")
    
    # 2. Sodré Santoro (HTTP)
    try:
        from app.scrapers.sodresantoro_verified import SodreSantoroScraper
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 Sodré Santoro")
        logger.info(f"{'='*60}")
        
        scraper = SodreSantoroScraper()
        properties = scraper.scrape(max_properties=None, max_pages=20)
        
        result = {
            "auctioneer_id": "sodresantoro",
            "name": "Sodré Santoro",
            "scraped": len(properties),
        }
        
        if properties:
            save_stats = save_properties_to_supabase(properties, "sodresantoro")
            result["saved"] = save_stats["inserted"]
            result["status"] = "success"
            update_auctioneer_status("sodresantoro", True, len(properties))
        else:
            result["status"] = "no_data"
            result["saved"] = 0
        
        results.append(result)
        
    except ImportError as e:
        logger.error(f"❌ Erro ao importar SodreSantoroScraper: {e}")
    
    # 3. Flex Leilões (Playwright)
    try:
        from app.scrapers.flexleiloes_playwright import FlexLeiloesPlaywrightScraper
        result = run_scraper(
            FlexLeiloesPlaywrightScraper,
            "flexleiloes",
            "Flex Leilões",
            max_pages=10
        )
        results.append(result)
    except ImportError as e:
        logger.error(f"❌ Erro ao importar FlexLeiloesPlaywrightScraper: {e}")
    
    # Resumo final
    logger.info(f"\n{'='*70}")
    logger.info("RESUMO FINAL")
    logger.info(f"{'='*70}")
    
    total_scraped = 0
    total_saved = 0
    
    for r in results:
        status = "✅" if r.get("status") == "success" else "❌"
        scraped = r.get("scraped", 0)
        saved = r.get("saved", 0)
        
        logger.info(f"{status} {r['name']}: {scraped} extraídos, {saved} salvos")
        
        total_scraped += scraped
        total_saved += saved
    
    logger.info(f"\n📊 TOTAL: {total_scraped} extraídos, {total_saved} salvos no Supabase")
    
    # Salvar relatório
    report = {
        "execution_date": datetime.now().isoformat(),
        "results": results,
        "totals": {
            "scraped": total_scraped,
            "saved": total_saved,
        }
    }
    
    report_file = f"scraper_execution_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n📄 Relatório salvo em: {report_file}")
    
    return results


if __name__ == "__main__":
    main()

