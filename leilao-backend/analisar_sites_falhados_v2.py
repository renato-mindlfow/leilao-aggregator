#!/usr/bin/env python3
"""
Análise direta dos 4 sites usando diferentes estratégias.
"""

import asyncio
import json
import re
import httpx
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
"""


async def analisar_megaleiloes():
    """Analisa Mega Leilões."""
    print("\n" + "="*70)
    print("1. MEGA LEILÕES - https://www.megaleiloes.com.br/imoveis")
    print("="*70)
    
    result = {
        "url": "https://www.megaleiloes.com.br/imoveis",
        "method": "playwright_domcontentloaded"
    }
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            )
            await context.add_init_script(STEALTH_SCRIPT)
            page = await context.new_page()
            
            # Acessar com domcontentloaded
            await page.goto("https://www.megaleiloes.com.br/imoveis", wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(10)  # Esperar SPA carregar
            
            # Scroll
            await page.evaluate("window.scrollBy(0, 2000)")
            await asyncio.sleep(3)
            
            html = await page.content()
            
            # Analisar HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Procurar cards
            cards = soup.select('[class*="card"], [class*="item"], article')
            result["cards_found"] = len(cards)
            print(f"\nCards encontrados: {len(cards)}")
            
            if cards:
                card = cards[0]
                classes = ' '.join(card.get('class', []))
                result["card_selector"] = f".{card.get('class', ['card'])[0]}" if card.get('class') else "article"
                print(f"  Seletor CSS sugerido: {result['card_selector']}")
                print(f"  Classes: {classes[:100]}")
            
            # Procurar links
            links = soup.select('a[href*="/leilao/"], a[href*="/imovel/"]')
            result["links_found"] = len(links)
            print(f"\nLinks encontrados: {len(links)}")
            
            if links:
                link = links[0]
                href = link.get('href', '')
                result["link_pattern"] = href
                result["link_selector"] = 'a[href*="/leilao/"], a[href*="/imovel/"]'
                print(f"  Padrão URL: {href}")
                print(f"  Seletor: a[href*=\"/leilao/\"]")
            
            # Paginação
            pagination = soup.select('.pagination, [class*="pagination"]')
            result["pagination_found"] = len(pagination) > 0
            print(f"\nPaginação: {result['pagination_found']}")
            
            # Tentar acessar um imóvel
            if links:
                first_link = links[0].get('href', '')
                if first_link:
                    full_url = first_link if first_link.startswith('http') else f"https://www.megaleiloes.com.br{first_link}"
                    print(f"\nAcessando imóvel: {full_url[:60]}...")
                    
                    try:
                        await page.goto(full_url, wait_until='domcontentloaded', timeout=30000)
                        await asyncio.sleep(5)
                        
                        detail_html = await page.content()
                        detail_soup = BeautifulSoup(detail_html, 'html.parser')
                        
                        # Título
                        title = detail_soup.select_one('h1, h2.title, .titulo, [class*="title"]')
                        if title:
                            result["title_selector"] = "h1" if detail_soup.select_one('h1') else "[class*=\"title\"]"
                            result["title_example"] = title.get_text(strip=True)[:50]
                            print(f"  Título: {result['title_selector']} -> {result['title_example']}")
                        
                        # Preço
                        price = detail_soup.select_one('.valor, .preco, .lance, [class*="price"], [class*="valor"]')
                        if price:
                            result["price_selector"] = ".valor, .preco, [class*=\"price\"]"
                            result["price_example"] = price.get_text(strip=True)[:50]
                            print(f"  Preço: {result['price_selector']} -> {result['price_example']}")
                        
                        # Localização
                        body_text = await page.evaluate("() => document.body.innerText")
                        loc_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[-\/]\s*([A-Z]{2})\b', body_text)
                        if loc_match:
                            result["location_example"] = f"{loc_match.group(1)}/{loc_match.group(2)}"
                            print(f"  Localização: {result['location_example']}")
                        
                    except Exception as e:
                        print(f"  Erro: {e}")
            
            await browser.close()
            
    except Exception as e:
        result["error"] = str(e)
        print(f"\nErro: {e}")
    
    return result


async def analisar_lancejudicial():
    """Analisa Lance Judicial."""
    print("\n" + "="*70)
    print("2. LANCE JUDICIAL - https://www.lancejudicial.com.br/imoveis")
    print("="*70)
    
    result = {
        "url": "https://www.lancejudicial.com.br/imoveis",
        "cloudflare": False
    }
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            )
            await context.add_init_script(STEALTH_SCRIPT)
            page = await context.new_page()
            
            await page.goto("https://www.lancejudicial.com.br/imoveis", wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(10)
            
            body_text = await page.evaluate("() => document.body.innerText")
            result["cloudflare"] = any(ind in body_text.lower() for ind in ['checking your browser', 'just a moment'])
            print(f"\nCloudflare: {result['cloudflare']}")
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Cards
            cards = soup.select('[class*="card"], article')
            result["cards_found"] = len(cards)
            print(f"\nCards encontrados: {len(cards)}")
            
            if cards:
                card = cards[0]
                classes = ' '.join(card.get('class', []))
                result["card_selector"] = f".{card.get('class', ['card'])[0]}" if card.get('class') else "article"
                print(f"  Seletor: {result['card_selector']}")
            
            # Links
            links = soup.select('a[href*="/leilao/"], a[href*="/imovel/"], a[href*="/lote/"]')
            result["links_found"] = len(links)
            print(f"\nLinks encontrados: {len(links)}")
            
            if links:
                link = links[0]
                result["link_selector"] = 'a[href*="/leilao/"], a[href*="/imovel/"]'
                result["link_pattern"] = link.get('href', '')
                print(f"  Padrão: {link.get('href', '')[:60]}")
            
            # Paginação
            pagination = soup.select('.pagination, [class*="pagination"]')
            result["pagination_found"] = len(pagination) > 0
            print(f"\nPaginação: {result['pagination_found']}")
            
            await browser.close()
            
    except Exception as e:
        result["error"] = str(e)
        print(f"\nErro: {e}")
    
    return result


async def analisar_portalzuk():
    """Analisa Portal Zukerman."""
    print("\n" + "="*70)
    print("3. PORTAL ZUKERMAN - https://www.portalzuk.com.br/leilao-de-imoveis")
    print("="*70)
    
    result = {
        "url": "https://www.portalzuk.com.br/leilao-de-imoveis",
        "url_pattern": "/imovel/{estado}/{cidade}/{bairro}/{id}"
    }
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            )
            await context.add_init_script(STEALTH_SCRIPT)
            page = await context.new_page()
            
            await page.goto("https://www.portalzuk.com.br/leilao-de-imoveis", wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(10)
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Cards
            cards = soup.select('[class*="card"], [class*="property"], article')
            result["cards_found"] = len(cards)
            print(f"\nCards encontrados: {len(cards)}")
            
            if cards:
                card = cards[0]
                result["card_selector"] = f".{card.get('class', ['card'])[0]}" if card.get('class') else "article"
                print(f"  Seletor: {result['card_selector']}")
            
            # Links - padrão especial /imovel/estado/cidade/bairro/id
            links = soup.select('a[href*="/imovel/"]')
            result["links_found"] = len(links)
            print(f"\nLinks encontrados: {len(links)}")
            
            if links:
                link = links[0]
                href = link.get('href', '')
                result["link_selector"] = 'a[href*="/imovel/"]'
                result["link_pattern"] = href
                
                # Extrair padrão
                match = re.search(r'/imovel/([^/]+)/([^/]+)/([^/]+)/(\d+)', href)
                if match:
                    result["url_pattern_detail"] = {
                        "estado": match.group(1),
                        "cidade": match.group(2),
                        "bairro": match.group(3),
                        "id": match.group(4)
                    }
                    print(f"  Padrão: /imovel/{match.group(1)}/{match.group(2)}/{match.group(3)}/{match.group(4)}")
            
            # Paginação
            pagination = soup.select('.pagination, [class*="pagination"]')
            result["pagination_found"] = len(pagination) > 0
            print(f"\nPaginação: {result['pagination_found']}")
            
            await browser.close()
            
    except Exception as e:
        result["error"] = str(e)
        print(f"\nErro: {e}")
    
    return result


def testar_api_sold():
    """Testa API do Sold."""
    print("\n" + "="*70)
    print("4. SOLD LEILÕES - API")
    print("="*70)
    
    result = {
        "api_url": "https://offer-query.superbid.net/offers/",
        "tests": []
    }
    
    # Teste 1: Portal ID 2, filtro imóveis
    try:
        r = httpx.get(
            'https://offer-query.superbid.net/offers/?portalId=2&filter=product.productType.description:imoveis&pageNumber=1&pageSize=10',
            headers={'Accept': 'application/json', 'Origin': 'https://www.sold.com.br'},
            timeout=30.0
        )
        d = r.json()
        result["tests"].append({
            "url": "portalId=2&filter=product.productType.description:imoveis",
            "status": r.status_code,
            "total": d.get("total", 0),
            "items_returned": len(d.get("offers", [])),
            "working": True
        })
        print(f"\nTeste 1: portalId=2, filtro imoveis")
        print(f"  Status: {r.status_code}")
        print(f"  Total: {d.get('total', 0)} ofertas")
        print(f"  Retornadas: {len(d.get('offers', []))}")
    except Exception as e:
        result["tests"].append({"error": str(e)})
    
    # Teste 2: Store ID 1161 (Sold)
    try:
        r = httpx.get(
            'https://offer-query.superbid.net/offers/?portalId=2&filter=stores.id:1161&pageNumber=1&pageSize=10',
            headers={'Accept': 'application/json', 'Origin': 'https://www.sold.com.br'},
            timeout=30.0
        )
        d = r.json()
        result["tests"].append({
            "url": "portalId=2&filter=stores.id:1161",
            "status": r.status_code,
            "total": d.get("total", 0),
            "items_returned": len(d.get("offers", [])),
            "working": True
        })
        print(f"\nTeste 2: portalId=2, stores.id:1161")
        print(f"  Status: {r.status_code}")
        print(f"  Total: {d.get('total', 0)} ofertas")
    except Exception as e:
        result["tests"].append({"error": str(e)})
    
    result["recommendation"] = "Usar API REST - filtro: product.productType.description:imoveis"
    
    return result


async def main():
    """Função principal."""
    
    print("="*70)
    print("ANÁLISE DETALHADA DOS 4 SITES QUE FALHARAM")
    print("="*70)
    
    results = {}
    
    # 1. Mega Leilões
    results["megaleiloes"] = await analisar_megaleiloes()
    await asyncio.sleep(2)
    
    # 2. Lance Judicial
    results["lancejudicial"] = await analisar_lancejudicial()
    await asyncio.sleep(2)
    
    # 3. Portal Zukerman
    results["portalzuk"] = await analisar_portalzuk()
    
    # 4. Sold (API)
    results["sold"] = testar_api_sold()
    
    # Salvar
    with open("analise_sites_falhados_detalhada.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*70)
    print("ANÁLISE CONCLUÍDA")
    print("="*70)
    print("\nResultados salvos em: analise_sites_falhados_detalhada.json")


if __name__ == "__main__":
    asyncio.run(main())

