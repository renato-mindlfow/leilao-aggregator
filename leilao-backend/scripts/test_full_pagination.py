#!/usr/bin/env python3
"""
TESTE DE PAGINAÇÃO COMPLETA
Verifica se scrapers estão extraindo todas as páginas.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_scraper(scraper_class, expected_min: int, name: str):
    """Testa um scraper e verifica se atingiu mínimo esperado."""
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTANDO: {name}")
    logger.info(f"Mínimo esperado: {expected_min} imóveis")
    logger.info(f"{'='*60}")
    
    try:
        scraper = scraper_class(headless=True)
        properties = scraper.scrape(max_properties=None, max_pages=30)
        
        # Estatísticas
        with_price = sum(1 for p in properties if p.get('first_auction_value'))
        with_city = sum(1 for p in properties if p.get('city'))
        
        logger.info(f"\n📊 Resultado:")
        logger.info(f"   Total extraído: {len(properties)}")
        logger.info(f"   Com preço: {with_price} ({with_price*100//max(len(properties),1)}%)")
        logger.info(f"   Com cidade: {with_city} ({with_city*100//max(len(properties),1)}%)")
        
        if len(properties) >= expected_min * 0.8:
            logger.info(f"   ✅ SUCESSO! Atingiu {len(properties)}/{expected_min} ({len(properties)*100//expected_min}%)")
            return True, len(properties)
        else:
            logger.warning(f"   ⚠️ ABAIXO DO ESPERADO: {len(properties)}/{expected_min}")
            return False, len(properties)
            
    except Exception as e:
        logger.error(f"   ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def main():
    results = []
    
    # Mega Leilões - esperado ~756
    from app.scrapers.megaleiloes_playwright import MegaLeiloesPlaywrightScraper
    success, count = test_scraper(MegaLeiloesPlaywrightScraper, 700, "Mega Leilões")
    results.append(("Mega Leilões", success, count, 756))
    
    # Flex Leilões
    from app.scrapers.flexleiloes_playwright import FlexLeiloesPlaywrightScraper
    success, count = test_scraper(FlexLeiloesPlaywrightScraper, 10, "Flex Leilões")
    results.append(("Flex Leilões", success, count, 50))
    
    # Resumo
    logger.info(f"\n{'='*60}")
    logger.info("RESUMO FINAL")
    logger.info(f"{'='*60}")
    
    for name, success, count, expected in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {name}: {count}/{expected} ({count*100//max(expected,1)}%)")
    
    success_count = sum(1 for _, s, _, _ in results if s)
    logger.info(f"\nTaxa de sucesso: {success_count}/{len(results)}")

if __name__ == "__main__":
    main()

