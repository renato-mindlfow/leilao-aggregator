#!/usr/bin/env python3
"""
TESTE DOS SCRAPERS VERIFICADOS VISUALMENTE
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    results = []
    
    logger.info("=" * 70)
    logger.info("TESTE DOS SCRAPERS VERIFICADOS VISUALMENTE")
    logger.info("=" * 70)
    
    # Teste 1: Sodré Santoro (HTTP simples)
    logger.info("\n" + "─" * 50)
    logger.info("1. SODRÉ SANTORO (HTTP)")
    logger.info("─" * 50)
    
    try:
        from app.scrapers.sodresantoro_verified import SodreSantoroScraper
        scraper = SodreSantoroScraper()
        props = scraper.scrape(max_properties=10, max_pages=2)
        
        results.append({
            "name": "Sodré Santoro",
            "status": "success" if props else "no_data",
            "count": len(props),
            "sample": props[:2] if props else []
        })
        
        if props:
            logger.info(f"✅ {len(props)} imóveis")
            for p in props[:2]:
                logger.info(f"   - {p.get('title', 'N/A')[:50]}")
                logger.info(f"     Preço: R$ {p.get('first_auction_value', 'N/A')}")
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        results.append({"name": "Sodré Santoro", "status": "error", "error": str(e)})
    
    # Teste 2: Mega Leilões (Playwright)
    logger.info("\n" + "─" * 50)
    logger.info("2. MEGA LEILÕES (Playwright)")
    logger.info("─" * 50)
    
    try:
        from app.scrapers.megaleiloes_playwright import MegaLeiloesPlaywrightScraper
        scraper = MegaLeiloesPlaywrightScraper(headless=True)
        props = scraper.scrape(max_properties=10)
        
        results.append({
            "name": "Mega Leilões",
            "status": "success" if props else "no_data",
            "count": len(props),
            "sample": props[:2] if props else []
        })
        
        if props:
            logger.info(f"✅ {len(props)} imóveis")
            for p in props[:2]:
                logger.info(f"   - {p.get('title', 'N/A')[:50]}")
                logger.info(f"     Preço: R$ {p.get('first_auction_value', 'N/A')}")
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        results.append({"name": "Mega Leilões", "status": "error", "error": str(e)})
    
    # Teste 3: Flex Leilões (Playwright - já implementado)
    logger.info("\n" + "─" * 50)
    logger.info("3. FLEX LEILÕES (Playwright)")
    logger.info("─" * 50)
    
    try:
        from app.scrapers.flexleiloes_playwright import FlexLeiloesPlaywrightScraper
        scraper = FlexLeiloesPlaywrightScraper(headless=True)
        props = scraper.scrape(max_properties=10)
        
        results.append({
            "name": "Flex Leilões",
            "status": "success" if props else "no_data",
            "count": len(props),
        })
        
        if props:
            logger.info(f"✅ {len(props)} imóveis")
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        results.append({"name": "Flex Leilões", "status": "error", "error": str(e)})
    
    # Resumo
    logger.info("\n" + "=" * 70)
    logger.info("RESUMO")
    logger.info("=" * 70)
    
    success = sum(1 for r in results if r.get("status") == "success")
    total = len(results)
    
    for r in results:
        status = "✅" if r.get("status") == "success" else "❌"
        count = r.get("count", 0)
        logger.info(f"{status} {r['name']}: {count} imóveis")
    
    logger.info(f"\nTaxa de sucesso: {success}/{total}")
    
    return results

if __name__ == "__main__":
    main()

