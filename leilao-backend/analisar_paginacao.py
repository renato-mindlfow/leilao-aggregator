#!/usr/bin/env python3
"""
Script para analisar paginação dos sites Portal Zukerman e Mega Leilões.
"""

import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
"""


async def analisar_portal_zuk():
    """Analisa paginação do Portal Zukerman."""
    
    print("="*70)
    print("1. PORTAL ZUKERMAN - Analisando Paginacao")
    print("="*70)
    
    result = {
        "site": "Portal Zukerman",
        "url": "https://www.portalzuk.com.br/leilao-de-imoveis",
        "pagination": {
            "found": False,
            "type": None,
            "selector": None,
            "url_pattern": None,
            "total_pages": None,
            "elements": []
        }
    }
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='pt-BR',
            )
            await context.add_init_script(STEALTH_SCRIPT)
            
            page = await context.new_page()
            
            print(f"\n[ACESSANDO] {result['url']}")
            await page.goto(result["url"], wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)
            
            # Scroll até o final
            print("[SCROLL] Fazendo scroll ate o final da pagina...")
            for i in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Procurar paginação numérica (1, 2, 3...)
            pagination_numeric = soup.select('.pagination, [class*="pagination"], [class*="pager"], nav[aria-label*="pagination"]')
            
            if pagination_numeric:
                pag = pagination_numeric[0]
                result["pagination"]["found"] = True
                result["pagination"]["type"] = "numeric"
                result["pagination"]["selector"] = f".{pag.get('class', ['pagination'])[0]}" if pag.get('class') else "nav[aria-label*='pagination']"
                
                # Procurar números de página
                page_links = pag.select('a, button, [data-page]')
                for link in page_links[:10]:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    if text.isdigit() or 'próxima' in text.lower() or 'next' in text.lower():
                        result["pagination"]["elements"].append({
                            "text": text,
                            "href": href,
                            "classes": ' '.join(link.get('class', []))
                        })
                
                # Tentar encontrar total de páginas
                pag_text = pag.get_text()
                total_match = re.search(r'(\d+)\s*(?:de|of|total|páginas?)', pag_text, re.I)
                if total_match:
                    result["pagination"]["total_pages"] = int(total_match.group(1))
                
                print(f"\n[ENCONTRADO] Paginacao numerica")
                print(f"  Seletor: {result['pagination']['selector']}")
                print(f"  Elementos: {len(result['pagination']['elements'])}")
            
            # Procurar botão "Próxima" ou "Next"
            if not result["pagination"]["found"]:
                next_btn = soup.select_one('a[rel="next"], .next, [aria-label*="next"], button:contains("Próxima")')
                if next_btn:
                    result["pagination"]["found"] = True
                    result["pagination"]["type"] = "next_button"
                    result["pagination"]["selector"] = 'a[rel="next"]'
                    href = next_btn.get('href', '')
                    result["pagination"]["elements"].append({
                        "text": next_btn.get_text(strip=True),
                        "href": href
                    })
                    print(f"\n[ENCONTRADO] Botao 'Proxima'")
                    print(f"  Seletor: {result['pagination']['selector']}")
            
            # Procurar botão "Carregar mais"
            if not result["pagination"]["found"]:
                load_more = soup.select_one('button:contains("Carregar mais"), [class*="load-more"], [class*="carregar"]')
                if load_more:
                    result["pagination"]["found"] = True
                    result["pagination"]["type"] = "load_more"
                    result["pagination"]["selector"] = 'button[class*="load-more"]'
                    print(f"\n[ENCONTRADO] Botao 'Carregar mais'")
            
            # Verificar URL atual
            result["pagination"]["current_url"] = page.url
            
            # Tentar clicar na página 2 se existir
            if result["pagination"]["found"] and result["pagination"]["type"] == "numeric":
                page_2_link = soup.select_one('a:contains("2"), [data-page="2"]')
                if page_2_link:
                    href = page_2_link.get('href', '')
                    if href:
                        full_url = href if href.startswith('http') else f"https://www.portalzuk.com.br{href}"
                        print(f"\n[TESTANDO] Clicando na pagina 2...")
                        print(f"  URL: {full_url}")
                        
                        try:
                            await page.goto(full_url, wait_until='domcontentloaded', timeout=30000)
                            await asyncio.sleep(3)
                            result["pagination"]["page_2_url"] = page.url
                            print(f"  Nova URL: {page.url}")
                            
                            # Extrair padrão
                            if '?' in page.url:
                                result["pagination"]["url_pattern"] = "query_param"
                                match = re.search(r'[?&]page=(\d+)', page.url)
                                if match:
                                    result["pagination"]["url_param"] = "page"
                            elif '/page/' in page.url or '/p/' in page.url:
                                result["pagination"]["url_pattern"] = "path"
                                match = re.search(r'/(?:page|p)/(\d+)', page.url)
                                if match:
                                    result["pagination"]["url_path"] = "/page/{num}"
                        except Exception as e:
                            print(f"  [ERRO] {e}")
            
            await browser.close()
            
    except Exception as e:
        result["error"] = str(e)
        print(f"\n[ERRO] {e}")
    
    return result


async def analisar_mega_leiloes():
    """Analisa paginação do Mega Leilões."""
    
    print("\n" + "="*70)
    print("2. MEGA LEILOES - Analisando Paginacao")
    print("="*70)
    
    result = {
        "site": "Mega Leilões",
        "url": "https://www.megaleiloes.com.br/imoveis",
        "pagination": {
            "found": False,
            "type": None,
            "selector": None,
            "url_pattern": None,
            "total_pages": None,
            "elements": []
        }
    }
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='pt-BR',
            )
            await context.add_init_script(STEALTH_SCRIPT)
            
            page = await context.new_page()
            
            print(f"\n[ACESSANDO] {result['url']}")
            await page.goto(result["url"], wait_until='domcontentloaded', timeout=60000)
            
            # Aguardar SPA carregar
            print("[AGUARDANDO] SPA carregar (15s)...")
            await asyncio.sleep(15)
            
            # Scroll até o final
            print("[SCROLL] Fazendo scroll ate o final...")
            for i in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Procurar paginação numérica
            pagination_numeric = soup.select('.pagination, [class*="pagination"], [class*="pager"], nav[aria-label*="pagination"]')
            
            if pagination_numeric:
                pag = pagination_numeric[0]
                result["pagination"]["found"] = True
                result["pagination"]["type"] = "numeric"
                result["pagination"]["selector"] = f".{pag.get('class', ['pagination'])[0]}" if pag.get('class') else "nav[aria-label*='pagination']"
                
                page_links = pag.select('a, button, [data-page]')
                for link in page_links[:10]:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    if text.isdigit() or 'próxima' in text.lower() or 'next' in text.lower() or '>' in text:
                        result["pagination"]["elements"].append({
                            "text": text,
                            "href": href,
                            "classes": ' '.join(link.get('class', []))
                        })
                
                pag_text = pag.get_text()
                total_match = re.search(r'(\d+)\s*(?:de|of|total|páginas?)', pag_text, re.I)
                if total_match:
                    result["pagination"]["total_pages"] = int(total_match.group(1))
                
                print(f"\n[ENCONTRADO] Paginacao numerica")
                print(f"  Seletor: {result['pagination']['selector']}")
            
            # Procurar botão "Próxima" ou setas
            if not result["pagination"]["found"]:
                next_btn = soup.select_one('a[rel="next"], .next, [aria-label*="next"], button:contains(">")')
                if next_btn:
                    result["pagination"]["found"] = True
                    result["pagination"]["type"] = "next_button"
                    result["pagination"]["selector"] = 'a[rel="next"]'
                    print(f"\n[ENCONTRADO] Botao 'Proxima'")
            
            result["pagination"]["current_url"] = page.url
            
            # Tentar clicar na página 2
            if result["pagination"]["found"]:
                page_2_link = soup.select_one('a:contains("2"), [data-page="2"]')
                if page_2_link:
                    href = page_2_link.get('href', '')
                    if href:
                        full_url = href if href.startswith('http') else f"https://www.megaleiloes.com.br{href}"
                        print(f"\n[TESTANDO] Clicando na pagina 2...")
                        print(f"  URL: {full_url}")
                        
                        try:
                            await page.goto(full_url, wait_until='domcontentloaded', timeout=30000)
                            await asyncio.sleep(5)
                            result["pagination"]["page_2_url"] = page.url
                            print(f"  Nova URL: {page.url}")
                            
                            if '?' in page.url:
                                result["pagination"]["url_pattern"] = "query_param"
                                match = re.search(r'[?&]page=(\d+)', page.url)
                                if match:
                                    result["pagination"]["url_param"] = "page"
                            elif '/page/' in page.url:
                                result["pagination"]["url_pattern"] = "path"
                        except Exception as e:
                            print(f"  [ERRO] {e}")
            
            await browser.close()
            
    except Exception as e:
        result["error"] = str(e)
        print(f"\n[ERRO] {e}")
    
    return result


async def main():
    """Função principal."""
    
    print("="*70)
    print("ANALISE DE PAGINACAO - PORTAL ZUKERMAN E MEGA LEILOES")
    print("="*70)
    
    results = {}
    
    # 1. Portal Zukerman
    results["portalzuk"] = await analisar_portal_zuk()
    await asyncio.sleep(2)
    
    # 2. Mega Leilões
    results["megaleiloes"] = await analisar_mega_leiloes()
    
    # Salvar resultados
    with open("analise_paginacao.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Relatório
    print("\n" + "="*70)
    print("RELATORIO FINAL")
    print("="*70)
    
    for site_id, result in results.items():
        print(f"\n{result['site']}:")
        pag = result.get("pagination", {})
        
        if pag.get("found"):
            print(f"  Tipo: {pag.get('type')}")
            print(f"  Seletor: {pag.get('selector')}")
            print(f"  Padrao URL: {pag.get('url_pattern', 'N/A')}")
            if pag.get("total_pages"):
                print(f"  Total de paginas: {pag.get('total_pages')}")
            if pag.get("page_2_url"):
                print(f"  URL pagina 2: {pag.get('page_2_url')}")
        else:
            print(f"  [NAO ENCONTRADO] Paginacao nao encontrada")
            print(f"  Possivelmente: scroll infinito")
    
    print(f"\n[ARQUIVO] Resultados salvos em: analise_paginacao.json")


if __name__ == "__main__":
    asyncio.run(main())

