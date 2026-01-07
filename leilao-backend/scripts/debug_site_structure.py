#!/usr/bin/env python3
"""
DEBUG: Inspeciona estrutura HTML dos sites
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def inspect_site(url, site_name):
    """Inspeciona estrutura de um site."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Inspecionando: {site_name}")
    logger.info(f"URL: {url}")
    logger.info(f"{'='*60}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(5)
            
            # Scroll
            await page.evaluate("""
                () => {
                    window.scrollBy(0, 1000);
                }
            """)
            await asyncio.sleep(2)
            
            # Salvar HTML
            html = await page.content()
            filename = f"debug_{site_name.lower().replace(' ', '_')}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"✅ HTML salvo em: {filename}")
            
            # Tentar encontrar cards comuns
            selectors_to_test = [
                "div.card",
                "div[class*='card']",
                "div[class*='leilao']",
                "div[class*='auction']",
                "div[class*='item']",
                "div[class*='lote']",
                "div[class*='property']",
                "div[class*='imovel']",
                "article",
                ".grid > div",
                ".list > div",
            ]
            
            logger.info("\nTestando seletores comuns:")
            for selector in selectors_to_test:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        logger.info(f"  ✅ {selector}: {len(elements)} elementos")
                        
                        # Pegar HTML do primeiro elemento
                        first_html = await elements[0].inner_html()
                        if len(first_html) < 500:
                            logger.info(f"     Exemplo: {first_html[:200]}")
                except:
                    pass
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
        finally:
            await browser.close()

async def main():
    """Inspeciona todos os sites."""
    sites = [
        ("https://www.sold.com.br/leiloes", "Sold"),
        ("https://www.lancejudicial.com.br/leiloes", "LanceJudicial"),
        ("https://www.flexleiloes.com.br/imoveis", "FlexLeiloes"),
    ]
    
    for url, name in sites:
        await inspect_site(url, name)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())

