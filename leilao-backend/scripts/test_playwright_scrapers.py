#!/usr/bin/env python3
"""
TESTE DOS SCRAPERS PLAYWRIGHT
Testa os 3 scrapers para sites com Cloudflare.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_scrapers():
    """Testa todos os scrapers Playwright."""
    
    results = {}
    
    # Importar scrapers
    from app.scrapers.sold_playwright import SoldPlaywrightScraper
    from app.scrapers.lancejudicial_playwright import LanceJudicialPlaywrightScraper
    from app.scrapers.flexleiloes_playwright import FlexLeiloesPlaywrightScraper
    
    scrapers = [
        SoldPlaywrightScraper(headless=True),
        LanceJudicialPlaywrightScraper(headless=True),
        FlexLeiloesPlaywrightScraper(headless=True),
    ]
    
    for scraper in scrapers:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testando: {scraper.AUCTIONEER_NAME}")
        logger.info(f"{'='*60}")
        
        try:
            properties = await scraper.scrape_async(max_properties=5)
            
            results[scraper.AUCTIONEER_ID] = {
                "name": scraper.AUCTIONEER_NAME,
                "status": "success" if properties else "no_data",
                "count": len(properties),
                "sample": properties[:2] if properties else []
            }
            
            if properties:
                logger.info(f"✅ {len(properties)} propriedades encontradas")
                for p in properties[:2]:
                    logger.info(f"   - {p.get('title', 'N/A')[:50]}")
                    logger.info(f"     Preço: R$ {p.get('first_auction_value', 'N/A')}")
                    logger.info(f"     Cidade: {p.get('city', 'N/A')}")
            else:
                logger.warning(f"⚠️ Nenhuma propriedade encontrada")
                
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            results[scraper.AUCTIONEER_ID] = {
                "name": scraper.AUCTIONEER_NAME,
                "status": "error",
                "error": str(e)
            }
    
    # Resumo
    logger.info(f"\n{'='*60}")
    logger.info("RESUMO DOS TESTES")
    logger.info(f"{'='*60}")
    
    for scraper_id, result in results.items():
        status = "✅" if result["status"] == "success" else "❌"
        count = result.get("count", 0)
        logger.info(f"{status} {result['name']}: {count} propriedades")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_scrapers())

