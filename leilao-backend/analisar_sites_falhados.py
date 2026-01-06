#!/usr/bin/env python3
"""
Script para analisar os 4 sites que falharam no scraping.
Usa Playwright para acessar e analisar cada site.
"""

import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
"""

SITES = [
    {
        "id": "megaleiloes",
        "name": "Mega Leilões",
        "url": "https://www.megaleiloes.com.br/imoveis"
    },
    {
        "id": "lancejudicial",
        "name": "Lance Judicial",
        "url": "https://www.lancejudicial.com.br/imoveis"
    },
    {
        "id": "portalzuk",
        "name": "Portal Zukerman",
        "url": "https://www.portalzuk.com.br/leilao-de-imoveis"
    },
    {
        "id": "sold",
        "name": "Sold Leilões",
        "url": "https://www.sold.com.br/h/imoveis"
    }
]


async def analisar_megaleiloes(page):
    """Analisa Mega Leilões."""
    print("\n" + "="*70)
    print("1. MEGA LEILÕES")
    print("="*70)
    
    try:
        await page.goto("https://www.megaleiloes.com.br/imoveis", wait_until='networkidle', timeout=45000)
        await asyncio.sleep(5)
        
        # Scroll
        await page.evaluate("window.scrollBy(0, 1000)")
        await asyncio.sleep(2)
        
        html = await page.content()
        body_text = await page.evaluate("() => document.body.innerText")
        
        result = {
            "url": page.url,
            "cards": [],
            "links": [],
            "pagination": {},
            "detail_selectors": {}
        }
        
        # Procurar cards
        cards = await page.query_selector_all('[class*="card"], [class*="item"], article, [data-testid*="card"]')
        print(f"\nCards encontrados: {len(cards)}")
        
        if cards:
            for i in range(min(3, len(cards))):
                card_html = await cards[i].inner_html()
                classes = await cards[i].get_attribute('class')
                tag = await cards[i].evaluate('el => el.tagName')
                result["cards"].append({
                    "tag": tag,
                    "classes": classes,
                    "has_link": bool(await cards[i].query_selector('a'))
                })
            print(f"  Exemplo: {result['cards'][0]['tag']} com classes: {result['cards'][0]['classes'][:100]}")
        
        # Procurar links
        links = await page.query_selector_all('a[href*="/leilao/"], a[href*="/imovel/"]')
        print(f"\nLinks encontrados: {len(links)}")
        
        if links:
            for i in range(min(5, len(links))):
                href = await links[i].get_attribute('href')
                text = await links[i].inner_text()
                result["links"].append({
                    "href": href,
                    "text": text[:50]
                })
            print(f"  Primeiro link: {result['links'][0]['href']}")
        
        # Padrão URL
        url_patterns = re.findall(r'href=["\']([^"\']*\/leilao\/\d+[^"\']*)["\']', html)
        if url_patterns:
            result["url_pattern"] = url_patterns[0]
            print(f"\nPadrão URL: {url_patterns[0]}")
        
        # Paginação
        pagination = await page.query_selector('.pagination, [class*="pagination"]')
        if pagination:
            pag_html = await pagination.inner_html()
            result["pagination"]["html"] = pag_html[:300]
            has_next = await pagination.query_selector('a[rel="next"], .next')
            result["pagination"]["has_next"] = bool(has_next)
            print(f"\nPaginação encontrada: {bool(pagination)}")
        
        # Tentar abrir um imóvel
        if links:
            first_link = await links[0].get_attribute('href')
            if first_link:
                full_url = first_link if first_link.startswith('http') else f"https://www.megaleiloes.com.br{first_link}"
                print(f"\nAcessando imóvel: {full_url}")
                
                try:
                    await page.goto(full_url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(3)
                    
                    # Título
                    title_selectors = ['h1', 'h2.title', '.titulo', '[class*="title"]']
                    for sel in title_selectors:
                        title_el = await page.query_selector(sel)
                        if title_el:
                            title = await title_el.inner_text()
                            if title.strip():
                                result["detail_selectors"]["title"] = sel
                                result["detail_selectors"]["title_example"] = title.strip()[:50]
                                print(f"  Título: {sel} -> {title.strip()[:50]}")
                                break
                    
                    # Preço
                    price_selectors = ['.valor', '.preco', '.lance', '[class*="price"]', '[class*="valor"]']
                    for sel in price_selectors:
                        price_el = await page.query_selector(sel)
                        if price_el:
                            price_text = await price_el.inner_text()
                            if re.search(r'R\$\s*[\d.,]+', price_text):
                                result["detail_selectors"]["price"] = sel
                                result["detail_selectors"]["price_example"] = price_text.strip()[:50]
                                print(f"  Preço: {sel} -> {price_text.strip()[:50]}")
                                break
                    
                    # Localização
                    body_text_detail = await page.evaluate("() => document.body.innerText")
                    loc_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[-\/]\s*([A-Z]{2})\b', body_text_detail)
                    if loc_match:
                        location = f"{loc_match.group(1)}/{loc_match.group(2)}"
                        result["detail_selectors"]["location"] = location
                        print(f"  Localização: {location}")
                    
                except Exception as e:
                    print(f"  Erro ao acessar imóvel: {e}")
        
        return result
        
    except Exception as e:
        print(f"\nErro: {e}")
        return {"error": str(e)}


async def analisar_lancejudicial(page):
    """Analisa Lance Judicial."""
    print("\n" + "="*70)
    print("2. LANCE JUDICIAL")
    print("="*70)
    
    try:
        await page.goto("https://www.lancejudicial.com.br/imoveis", wait_until='networkidle', timeout=45000)
        await asyncio.sleep(5)
        
        body_text = await page.evaluate("() => document.body.innerText")
        
        result = {
            "url": page.url,
            "cloudflare": False,
            "cards": [],
            "links": [],
            "pagination": {}
        }
        
        # Verificar Cloudflare
        cloudflare_indicators = ['checking your browser', 'just a moment', 'cloudflare']
        result["cloudflare"] = any(ind in body_text.lower() for ind in cloudflare_indicators)
        print(f"\nCloudflare detectado: {result['cloudflare']}")
        
        if result["cloudflare"]:
            print("  Aguardando bypass...")
            await asyncio.sleep(10)
            body_text = await page.evaluate("() => document.body.innerText")
            result["cloudflare"] = any(ind in body_text.lower() for ind in cloudflare_indicators)
        
        # Procurar cards
        cards = await page.query_selector_all('[class*="card"], [class*="item"], article')
        print(f"\nCards encontrados: {len(cards)}")
        
        if cards:
            for i in range(min(3, len(cards))):
                classes = await cards[i].get_attribute('class')
                tag = await cards[i].evaluate('el => el.tagName')
                result["cards"].append({
                    "tag": tag,
                    "classes": classes
                })
            print(f"  Exemplo: {result['cards'][0]['tag']} com classes: {result['cards'][0]['classes'][:100]}")
        
        # Procurar links
        links = await page.query_selector_all('a[href*="/leilao/"], a[href*="/imovel/"], a[href*="/lote/"]')
        print(f"\nLinks encontrados: {len(links)}")
        
        if links:
            for i in range(min(5, len(links))):
                href = await links[i].get_attribute('href')
                text = await links[i].inner_text()
                result["links"].append({
                    "href": href,
                    "text": text[:50]
                })
            print(f"  Primeiro link: {result['links'][0]['href']}")
        
        # Paginação
        pagination = await page.query_selector('.pagination, [class*="pagination"]')
        if pagination:
            result["pagination"]["found"] = True
            has_next = await pagination.query_selector('.next, a[rel="next"]')
            result["pagination"]["has_next"] = bool(has_next)
            print(f"\nPaginação encontrada: {bool(pagination)}")
        
        return result
        
    except Exception as e:
        print(f"\nErro: {e}")
        return {"error": str(e)}


async def analisar_portalzuk(page):
    """Analisa Portal Zukerman."""
    print("\n" + "="*70)
    print("3. PORTAL ZUKERMAN")
    print("="*70)
    
    try:
        await page.goto("https://www.portalzuk.com.br/leilao-de-imoveis", wait_until='networkidle', timeout=45000)
        await asyncio.sleep(5)
        
        result = {
            "url": page.url,
            "cards": [],
            "links": [],
            "url_patterns": [],
            "pagination": {}
        }
        
        # Procurar cards
        cards = await page.query_selector_all('[class*="card"], [class*="property"], article')
        print(f"\nCards encontrados: {len(cards)}")
        
        if cards:
            for i in range(min(3, len(cards))):
                classes = await cards[i].get_attribute('class')
                tag = await cards[i].evaluate('el => el.tagName')
                result["cards"].append({
                    "tag": tag,
                    "classes": classes
                })
            print(f"  Exemplo: {result['cards'][0]['tag']} com classes: {result['cards'][0]['classes'][:100]}")
        
        # Procurar links - Portal Zuk tem padrão especial /imovel/estado/cidade/bairro/id
        links = await page.query_selector_all('a[href*="/imovel/"]')
        print(f"\nLinks encontrados: {len(links)}")
        
        if links:
            for i in range(min(5, len(links))):
                href = await links[i].get_attribute('href')
                text = await links[i].inner_text()
                result["links"].append({
                    "href": href,
                    "text": text[:50]
                })
                
                # Extrair padrão da URL
                url_match = re.search(r'/imovel/([^/]+)/([^/]+)/([^/]+)/(\d+)', href)
                if url_match:
                    result["url_patterns"].append({
                        "estado": url_match.group(1),
                        "cidade": url_match.group(2),
                        "bairro": url_match.group(3),
                        "id": url_match.group(4),
                        "full_url": href
                    })
            
            if result["url_patterns"]:
                pattern = result["url_patterns"][0]
                print(f"  Padrão URL: /imovel/{pattern['estado']}/{pattern['cidade']}/{pattern['bairro']}/{pattern['id']}")
        
        # Paginação
        pagination = await page.query_selector('.pagination, [class*="pagination"]')
        if pagination:
            result["pagination"]["found"] = True
            has_next = await pagination.query_selector('.next, a[rel="next"]')
            result["pagination"]["has_next"] = bool(has_next)
            print(f"\nPaginação encontrada: {bool(pagination)}")
        
        return result
        
    except Exception as e:
        print(f"\nErro: {e}")
        return {"error": str(e)}


async def analisar_sold(page):
    """Analisa Sold Leilões."""
    print("\n" + "="*70)
    print("4. SOLD LEILÕES")
    print("="*70)
    
    try:
        await page.goto("https://www.sold.com.br/h/imoveis", wait_until='networkidle', timeout=45000)
        await asyncio.sleep(5)
        
        result = {
            "url": page.url,
            "mui_components": False,
            "cards": [],
            "links": [],
            "api": {}
        }
        
        # Verificar Material-UI
        mui_check = await page.evaluate("""() => {
            return !!document.querySelector('[class*="Mui"], [class*="mui"]');
        }""")
        result["mui_components"] = mui_check
        print(f"\nMaterial-UI detectado: {mui_check}")
        
        # Procurar cards (Material-UI)
        cards = await page.query_selector_all('[class*="MuiCard"], [class*="card"], [class*="product"], article')
        print(f"\nCards encontrados: {len(cards)}")
        
        if cards:
            for i in range(min(3, len(cards))):
                classes = await cards[i].get_attribute('class')
                tag = await cards[i].evaluate('el => el.tagName')
                is_mui = 'Mui' in (classes or '')
                result["cards"].append({
                    "tag": tag,
                    "classes": classes,
                    "mui": is_mui
                })
            print(f"  Exemplo: {result['cards'][0]['tag']} com classes: {result['cards'][0]['classes'][:100]}")
        
        # Procurar links
        links = await page.query_selector_all('a[href*="/leilao/"], a[href*="/produto/"], a[href*="/oferta/"]')
        print(f"\nLinks encontrados: {len(links)}")
        
        if links:
            for i in range(min(5, len(links))):
                href = await links[i].get_attribute('href')
                text = await links[i].inner_text()
                result["links"].append({
                    "href": href,
                    "text": text[:50]
                })
            print(f"  Primeiro link: {result['links'][0]['href']}")
        
        # API já testada via httpx
        result["api"] = {
            "status": "tested_via_httpx",
            "note": "API testada separadamente"
        }
        
        return result
        
    except Exception as e:
        print(f"\nErro: {e}")
        return {"error": str(e)}


async def main():
    """Função principal."""
    
    print("="*70)
    print("ANÁLISE DOS 4 SITES QUE FALHARAM NO SCRAPING")
    print("="*70)
    
    results = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
        )
        
        await context.add_init_script(STEALTH_SCRIPT)
        
        page = await context.new_page()
        
        # 1. Mega Leilões
        results["megaleiloes"] = await analisar_megaleiloes(page)
        await asyncio.sleep(3)
        
        # 2. Lance Judicial
        results["lancejudicial"] = await analisar_lancejudicial(page)
        await asyncio.sleep(3)
        
        # 3. Portal Zukerman
        results["portalzuk"] = await analisar_portalzuk(page)
        await asyncio.sleep(3)
        
        # 4. Sold Leilões
        results["sold"] = await analisar_sold(page)
        
        await browser.close()
    
    # Testar API do Sold
    print("\n" + "="*70)
    print("TESTANDO API DO SOLD")
    print("="*70)
    
    try:
        import httpx
        r = httpx.get(
            'https://offer-query.superbid.net/offers/?portalId=2&filter=product.productType.description:imoveis&pageNumber=1&pageSize=10',
            headers={'Accept': 'application/json', 'Origin': 'https://www.sold.com.br'},
            timeout=30.0
        )
        d = r.json()
        results["sold"]["api"] = {
            "status_code": r.status_code,
            "total": d.get("total", 0),
            "items_returned": len(d.get("offers", [])),
            "filter": "product.productType.description:imoveis",
            "working": True
        }
        print(f"\nAPI Status: {r.status_code}")
        print(f"Total de ofertas: {d.get('total', 0)}")
        print(f"Ofertas retornadas: {len(d.get('offers', []))}")
        print(f"Filtro funcionando: product.productType.description:imoveis")
    except Exception as e:
        results["sold"]["api"] = {"error": str(e)}
        print(f"\nErro ao testar API: {e}")
    
    # Salvar resultados
    with open("analise_sites_falhados.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*70)
    print("ANÁLISE CONCLUÍDA")
    print("="*70)
    print("\nResultados salvos em: analise_sites_falhados.json")


if __name__ == "__main__":
    asyncio.run(main())

