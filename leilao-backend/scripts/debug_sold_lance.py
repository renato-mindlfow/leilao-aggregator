#!/usr/bin/env python3
"""
DEBUG AVANÇADO: Sold e LanceJudicial
Tenta encontrar os seletores corretos para estes sites.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import logging
from playwright.async_api import async_playwright
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_sold():
    """Debug detalhado do site Sold."""
    logger.info("\n" + "="*60)
    logger.info("DEBUG: SOLD LEILÕES")
    logger.info("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visível para debug
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            logger.info("Navegando para Sold...")
            await page.goto("https://www.sold.com.br/leiloes", wait_until='networkidle', timeout=60000)
            await asyncio.sleep(5)
            
            # Aguardar possíveis elementos carregarem
            logger.info("Aguardando 10 segundos para SPA carregar...")
            await asyncio.sleep(10)
            
            # Scroll
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(3)
            
            # Tentar encontrar estruturas de dados
            logger.info("\nProcurando por dados em window...")
            data_check = await page.evaluate("""
                () => {
                    const keys = Object.keys(window);
                    const relevantKeys = keys.filter(k => 
                        k.toLowerCase().includes('state') || 
                        k.toLowerCase().includes('data') ||
                        k.toLowerCase().includes('auction') ||
                        k.toLowerCase().includes('leilao') ||
                        k.toLowerCase().includes('event')
                    );
                    return {
                        relevantKeys: relevantKeys,
                        hasReactRoot: !!document.getElementById('root')
                    };
                }
            """)
            logger.info(f"Chaves relevantes: {data_check['relevantKeys']}")
            logger.info(f"Tem React root: {data_check['hasReactRoot']}")
            
            # Tentar interceptar requisições da API
            logger.info("\nRequests de rede capturados:")
            requests = []
            
            page.on("response", lambda response: requests.append({
                "url": response.url,
                "status": response.status
            }))
            
            # Recarregar para capturar requests
            await page.reload(wait_until='networkidle')
            await asyncio.sleep(5)
            
            api_requests = [r for r in requests if 'api' in r['url'].lower() or 'leilao' in r['url'].lower() or 'auction' in r['url'].lower()]
            for req in api_requests[:10]:
                logger.info(f"  - {req['url']} ({req['status']})")
            
            logger.info("\nSalvando screenshot para inspeção manual...")
            await page.screenshot(path="debug_sold_screenshot.png", full_page=True)
            logger.info("✅ Screenshot salvo: debug_sold_screenshot.png")
            
            # Aguardar para inspeção manual
            logger.info("\nBrowser permanecerá aberto por 30 segundos para inspeção manual...")
            logger.info("Verifique o browser para ver o que foi carregado!")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
        finally:
            await browser.close()

async def debug_lance():
    """Debug detalhado do Grupo Lance."""
    logger.info("\n" + "="*60)
    logger.info("DEBUG: GRUPO LANCE")
    logger.info("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            logger.info("Navegando para Grupo Lance...")
            await page.goto("https://www.grupolance.com.br/buscar?category=imoveis", wait_until='networkidle', timeout=60000)
            await asyncio.sleep(5)
            
            # Scroll
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(3)
            
            # Tentar seletores diversos
            selectors = [
                "div.card",
                "div[class*='card']",
                "div[class*='item']",
                "div[class*='lote']",
                "div[class*='produto']",
                "div[class*='imovel']",
                ".row > div",
                ".container > div",
                "article",
            ]
            
            logger.info("\nTestando seletores:")
            for sel in selectors:
                elements = await page.query_selector_all(sel)
                if len(elements) > 0:
                    logger.info(f"  ✅ {sel}: {len(elements)} elementos")
                    
                    # Pegar atributos do primeiro
                    if elements:
                        first = elements[0]
                        classes = await first.get_attribute("class")
                        logger.info(f"     Classes: {classes}")
            
            logger.info("\nSalvando screenshot...")
            await page.screenshot(path="debug_lance_screenshot.png", full_page=True)
            logger.info("✅ Screenshot salvo: debug_lance_screenshot.png")
            
            # Salvar HTML
            html = await page.content()
            with open("debug_lance_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            logger.info("✅ HTML salvo: debug_lance_page.html")
            
            logger.info("\nBrowser permanecerá aberto por 30 segundos...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
        finally:
            await browser.close()

async def main():
    """Executa debug de ambos os sites."""
    # await debug_sold()
    await debug_lance()

if __name__ == "__main__":
    asyncio.run(main())

