# ============================================================
# TAREFA FINAL: Scraping com Seletores Corretos (MCP Discovery)
# ============================================================
# Para: Cursor Agent
# Modo: AUTÔNOMO COMPLETO
# Baseado em: Análise do MCP Web Browser
# ============================================================

"""
╔══════════════════════════════════════════════════════════════╗
║  SELETORES DESCOBERTOS PELO MCP WEB BROWSER                  ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. SOLD LEILÕES - API REST                                  ║
║     • Total: 46.885 imóveis                                  ║
║     • Filtro: product.productType.description:imoveis        ║
║     • URL: offer-query.superbid.net/offers/                  ║
║                                                              ║
║  2. PORTAL ZUKERMAN - Playwright                             ║
║     • Cards: .card-property                                  ║
║     • Links: a[href*="/imovel/"] (30 encontrados)            ║
║     • Padrão: /imovel/{estado}/{cidade}/{bairro}/{id}        ║
║                                                              ║
║  3. LANCE JUDICIAL - Playwright + Scroll                     ║
║     • Cards: .card-item                                      ║
║     • Paginação: .pagination, .next                          ║
║     • Precisa: scroll para carregar AJAX                     ║
║                                                              ║
║  4. MEGA LEILÕES - Playwright + Espera Longa                 ║
║     • SPA React - precisa 15+ segundos                       ║
║     • Scroll extensivo necessário                            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin
import httpx


# ============================================================
# CONFIGURAÇÕES COM SELETORES DO MCP
# ============================================================

CONFIGS = {
    "sold": {
        "id": "sold",
        "name": "Sold Leilões",
        "website": "https://www.sold.com.br",
        "method": "api_rest",
        "api": {
            "base_url": "https://offer-query.superbid.net/offers/",
            "params": {
                "portalId": "2",
                "filter": "product.productType.description:imoveis",
                "pageSize": "50",
            },
            "pagination_param": "pageNumber",
            "total_field": "total",
            "items_field": "offers",
        },
        "priority": 1,
    },
    "portalzuk": {
        "id": "portalzuk",
        "name": "Portal Zukerman",
        "website": "https://www.portalzuk.com.br",
        "listing_url": "/leilao-de-imoveis",
        "method": "playwright",
        "selectors": {
            "card": ".card-property",
            "link": "a[href*='/imovel/']",
            "load_more": "#btn_carregarMais, button.btn.btn-outline.btn-xl, button:has-text('Carregar mais')",
        },
        "link_pattern": r"/imovel/[^/]+/[^/]+/[^/]+/.+?/(\d+-\d+)",
        "pagination": {
            "type": "load_more_button",
            "selector": "#btn_carregarMais",
            "max_clicks": 100,
            "imoveis_por_clique": 30,
        },
        "priority": 2,
    },
    "lancejudicial": {
        "id": "lancejudicial",
        "name": "Lance Judicial",
        "website": "https://www.lancejudicial.com.br",
        "listing_url": "/imoveis",
        "method": "playwright",
        "selectors": {
            "card": ".card-item",
            "link": "a[href*='/leilao/'], a[href*='/imovel/'], a[href*='/lote/']",
            "pagination": ".pagination",
            "next_page": ".next, [rel='next']",
        },
        "link_pattern": r"/(leilao|imovel|lote)/\d+",
        "pagination": "scroll_then_click",  # scroll + botão next
        "priority": 3,
    },
    "megaleiloes": {
        "id": "megaleiloes",
        "name": "Mega Leilões",
        "website": "https://www.megaleiloes.com.br",
        "listing_url": "/imoveis",
        "method": "playwright",
        "selectors": {
            "card": "[class*='card'], [class*='item'], article",
            "link": "a[href*='/leilao/'], a[href*='/imovel/']",
            "pagination": ".text-center",
        },
        "link_pattern": r"/(leilao|imovel)/\d+",
        "wait_time": 15,  # SPA precisa 15+ segundos
        "pagination": {
            "type": "query_param",
            "param": "pagina",
            "url_pattern": "?pagina={page}",
            "max_pages": 50,
        },
        "priority": 4,
    },
}

# Stealth script
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
"""


async def scrape_sold_api(max_items: int = 500) -> Dict:
    """
    SOLD LEILÕES - API REST
    Descoberto: 46.885 imóveis disponíveis
    """
    
    config = CONFIGS["sold"]
    result = {
        "id": config["id"],
        "name": config["name"],
        "method": "api_rest",
        "success": False,
        "total_available": 0,
        "total_extracted": 0,
        "properties": [],
        "errors": [],
    }
    
    print(f"\n{'='*70}")
    print(f"[PRIORIDADE 1] {config['name']} (API REST)")
    print(f"   Esperado: ~46.885 imoveis")
    print("="*70)
    
    try:
        api_config = config["api"]
        base_url = api_config["base_url"]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Origin": "https://www.sold.com.br",
            "Referer": "https://www.sold.com.br/",
        }
        
        all_properties = []
        page = 1
        max_pages = (max_items // 50) + 1
        
        async with httpx.AsyncClient(timeout=30) as client:
            while page <= max_pages and len(all_properties) < max_items:
                
                params = {
                    **api_config["params"],
                    api_config["pagination_param"]: str(page),
                }
                
                print(f"\n   [PAGINA] {page}...")
                
                try:
                    response = await client.get(base_url, params=params, headers=headers)
                    
                    if response.status_code != 200:
                        print(f"      [ERRO] HTTP {response.status_code}")
                        result["errors"].append(f"HTTP {response.status_code}")
                        break
                    
                    data = response.json()
                    
                    total = data.get(api_config["total_field"], 0)
                    items = data.get(api_config["items_field"], [])
                    
                    if page == 1:
                        result["total_available"] = total
                        print(f"      [TOTAL] Disponivel na API: {total:,} imoveis")
                    
                    print(f"      Extraidos: {len(items)} | Acumulado: {len(all_properties) + len(items)}")
                    
                    if not items:
                        print(f"      [WARN] Sem mais itens")
                        break
                    
                    for item in items:
                        prop = {
                            "id": item.get("id"),
                            "url": f"https://www.sold.com.br/leilao/{item.get('id', '')}",
                            "title": item.get("product", {}).get("shortDesc", ""),
                            "price": item.get("price", 0),
                            "price_formatted": item.get("priceFormatted", ""),
                            "location": "",
                            "state": "",
                            "city": "",
                            "image_url": item.get("product", {}).get("thumbnailUrl", ""),
                            "auctioneer_id": "sold",
                            "auctioneer_name": "Sold Leilões",
                        }
                        
                        # Localização
                        auction = item.get("auction", {})
                        address = auction.get("address", {})
                        if address:
                            city = address.get("city", "")
                            state = address.get("stateCode", "")
                            prop["city"] = city
                            prop["state"] = state
                            prop["location"] = f"{city}/{state}" if city else ""
                        
                        all_properties.append(prop)
                    
                    page += 1
                    await asyncio.sleep(0.3)  # Rate limiting
                    
                except Exception as e:
                    print(f"      [ERRO] {e}")
                    result["errors"].append(str(e))
                    break
        
        result["success"] = len(all_properties) > 0
        result["total_extracted"] = len(all_properties)
        result["properties"] = all_properties
        
        print(f"\n   [OK] Extraidos: {len(all_properties):,} imoveis")
        
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   [ERRO FATAL] {e}")
    
    return result


async def scrape_portal_zuk(max_items: int = 200) -> Dict:
    """
    PORTAL ZUKERMAN - Playwright com seletores corretos
    Descoberto: .card-property, a[href*="/imovel/"]
    """
    
    config = CONFIGS["portalzuk"]
    result = {
        "id": config["id"],
        "name": config["name"],
        "method": "playwright",
        "success": False,
        "total_extracted": 0,
        "properties": [],
        "errors": [],
    }
    
    print(f"\n{'='*70}")
    print(f"[PRIORIDADE 2] {config['name']} (Playwright)")
    print(f"   Seletores: {config['selectors']}")
    print("="*70)
    
    try:
        from playwright.async_api import async_playwright
        
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
            
            url = f"{config['website']}{config['listing_url']}"
            print(f"\n   [ACESSANDO] {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)
            
            # Fechar modal se existir
            modal = await page.query_selector("#modalVirada, .modal.show")
            if modal:
                print("   [FECHANDO] Modal encontrado, fechando...")
                close_btn = await page.query_selector("#modalVirada .close, .modal .close, [data-dismiss='modal']")
                if close_btn:
                    await close_btn.click()
                    await asyncio.sleep(1)
                else:
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(1)
            
            # Ler contador total de imóveis (opcional)
            body_text = await page.evaluate("() => document.body.innerText")
            patterns = [
                r'(\d+)\s*im[oó]veis?\s*(?:encontrados|dispon[íi]veis?|total)',
                r'(?:total|encontrados?)\s*[:\s]*(\d+)\s*im[oó]veis?',
            ]
            total_contador = None
            for pattern in patterns:
                match = re.search(pattern, body_text, re.I)
                if match:
                    total_contador = int(match.group(1))
                    print(f"   [CONTADOR] Total: {total_contador} imoveis")
                    break
            
            # Extrair links iniciais
            print("   [PAGINACAO] Usando botao 'Carregar mais'...")
            all_links = set()
            initial_links = await page.query_selector_all(config["selectors"]["link"])
            for link in initial_links:
                href = await link.get_attribute("href")
                if href:
                    full_url = urljoin(config["website"], href)
                    all_links.add(full_url)
            
            print(f"   Imoveis iniciais: {len(all_links)}")
            
            # Loop de cliques no botão "Carregar mais"
            max_cliques = 100
            cliques_realizados = 0
            
            for click_num in range(max_cliques):
                # Scroll até o final
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
                
                # Procurar botão "Carregar mais"
                load_more_btn = await page.query_selector("#btn_carregarMais")
                
                if not load_more_btn:
                    print(f"      [INFO] Botao nao encontrado apos {cliques_realizados} cliques, parando...")
                    break
                
                is_visible = await load_more_btn.is_visible()
                if not is_visible:
                    print(f"      [INFO] Botao nao visivel apos {cliques_realizados} cliques, parando...")
                    break
                
                # Contar links antes do clique
                links_before = len(all_links)
                
                # Clicar usando JavaScript para evitar interceptação
                try:
                    await page.evaluate("document.getElementById('btn_carregarMais').click()")
                    cliques_realizados += 1
                    await asyncio.sleep(3)  # Aguardar carregar novos itens
                except Exception as e:
                    print(f"      [ERRO] Erro ao clicar: {e}")
                    break
                
                # Extrair novos links
                new_links = await page.query_selector_all(config["selectors"]["link"])
                for link in new_links:
                    href = await link.get_attribute("href")
                    if href:
                        full_url = urljoin(config["website"], href)
                        all_links.add(full_url)
                
                links_after = len(all_links)
                novos = links_after - links_before
                
                print(f"      Clique {cliques_realizados}: {links_after} links totais (+{novos} novos)")
                
                # Se não adicionou novos links, parar
                if novos == 0:
                    print(f"      [INFO] Sem novos links, parando...")
                    break
                
                # Se atingiu o limite desejado
                if len(all_links) >= max_items:
                    print(f"      [INFO] Limite atingido ({max_items}), parando...")
                    break
                
                # Se já tem todos os imóveis do contador
                if total_contador and len(all_links) >= total_contador:
                    print(f"      [INFO] Todos os imoveis do contador extraidos, parando...")
                    break
            
            print(f"\n    Total de links: {len(all_links)}")
            
            # Converter para propriedades
            for url in list(all_links)[:max_items]:
                # Extrair info da URL
                # Padrão: /imovel/{estado}/{cidade}/{bairro}/{rua}/{id}
                parts = url.split('/')
                state = parts[4] if len(parts) > 4 else ""
                city = parts[5] if len(parts) > 5 else ""
                
                result["properties"].append({
                    "url": url,
                    "title": "",
                    "price": "",
                    "state": state.upper() if state else "",
                    "city": city.replace("-", " ").title() if city else "",
                    "location": f"{city.replace('-', ' ').title()}/{state.upper()}" if city and state else "",
                    "auctioneer_id": "portalzuk",
                    "auctioneer_name": "Portal Zukerman",
                })
            
            result["success"] = len(all_links) > 0
            result["total_extracted"] = len(result["properties"])
            
            await browser.close()
            
            print(f"\n   [OK] Extraidos: {result['total_extracted']} imoveis")
            
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   [ERRO] {e}")
    
    return result


async def scrape_lance_judicial(max_items: int = 200) -> Dict:
    """
    LANCE JUDICIAL - Playwright com scroll + seletores corretos
    Descoberto: .card-item, precisa scroll para AJAX
    """
    
    config = CONFIGS["lancejudicial"]
    result = {
        "id": config["id"],
        "name": config["name"],
        "method": "playwright",
        "success": False,
        "total_extracted": 0,
        "properties": [],
        "errors": [],
    }
    
    print(f"\n{'='*70}")
    print(f"[PRIORIDADE 3] {config['name']} (Playwright + Scroll)")
    print(f"   Seletores: {config['selectors']}")
    print("="*70)
    
    try:
        from playwright.async_api import async_playwright
        
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
            
            url = f"{config['website']}{config['listing_url']}"
            print(f"\n   [ACESSANDO] {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)
            
            # Scroll extensivo para carregar AJAX
            print("   [SCROLL] Fazendo scroll para carregar AJAX...")
            all_links = set()
            
            for scroll_num in range(15):
                # Extrair links
                html = await page.content()
                
                # Múltiplos padrões de link
                patterns = [
                    r'href=["\']([^"\']*?/leilao/\d+[^"\']*)["\']',
                    r'href=["\']([^"\']*?/imovel/\d+[^"\']*)["\']',
                    r'href=["\']([^"\']*?/lote/\d+[^"\']*)["\']',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, html, re.I)
                    for match in matches:
                        full_url = urljoin(config["website"], match)
                        if config["website"].replace("www.", "") in full_url.replace("www.", ""):
                            all_links.add(full_url)
                
                print(f"      Scroll {scroll_num + 1}: {len(all_links)} links únicos")
                
                if len(all_links) >= max_items:
                    break
                
                # Scroll
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(1.5)
                
                # Tentar clicar em "próxima página" se existir
                try:
                    next_btn = await page.query_selector(".next, [rel='next'], .pagination a:last-child")
                    if next_btn:
                        await next_btn.click()
                        await asyncio.sleep(3)
                except:
                    pass
            
            print(f"\n   [TOTAL] Links: {len(all_links)}")
            
            # Converter para propriedades
            for url in list(all_links)[:max_items]:
                result["properties"].append({
                    "url": url,
                    "title": "",
                    "price": "",
                    "location": "",
                    "auctioneer_id": "lancejudicial",
                    "auctioneer_name": "Lance Judicial",
                })
            
            result["success"] = len(all_links) > 0
            result["total_extracted"] = len(result["properties"])
            
            await browser.close()
            
            print(f"\n   [OK] Extraidos: {result['total_extracted']} imoveis")
            
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   [ERRO] {e}")
    
    return result


async def scrape_mega_leiloes(max_items: int = 200) -> Dict:
    """
    MEGA LEILÕES - Playwright com espera longa para SPA
    Descoberto: SPA React precisa 15+ segundos
    """
    
    config = CONFIGS["megaleiloes"]
    result = {
        "id": config["id"],
        "name": config["name"],
        "method": "playwright",
        "success": False,
        "total_extracted": 0,
        "properties": [],
        "errors": [],
    }
    
    print(f"\n{'='*70}")
    print(f"[PRIORIDADE 4] {config['name']} (SPA - Espera Longa)")
    print(f"   Tempo de espera: {config.get('wait_time', 15)}s")
    print("="*70)
    
    try:
        from playwright.async_api import async_playwright
        
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
            
            url = f"{config['website']}{config['listing_url']}"
            print(f"\n   [ACESSANDO] {url}")
            
            # Usar paginação numérica com query param
            print("   [PAGINACAO] Usando paginacao numerica (?pagina=2)...")
            all_links = set()
            pagination_config = config.get("pagination", {})
            max_pages = pagination_config.get("max_pages", 50)
            
            for page_num in range(1, max_pages + 1):
                # Construir URL da página
                if page_num == 1:
                    page_url = url
                else:
                    param = pagination_config.get("param", "pagina")
                    page_url = f"{url}?{param}={page_num}"
                
                print(f"   [PAGINA] {page_num}: {page_url}")
                
                await page.goto(page_url, wait_until='domcontentloaded', timeout=60000)
                
                # Espera longa para SPA
                wait_time = config.get("wait_time", 15)
                if page_num == 1:
                    print(f"   [AGUARDANDO] SPA carregar ({wait_time}s)...")
                await asyncio.sleep(wait_time if page_num == 1 else 5)
                
                # Scroll para carregar conteúdo lazy
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                html = await page.content()
                
                # Múltiplos padrões
                patterns = [
                    r'href=["\']([^"\']*?/leilao/\d+[^"\']*)["\']',
                    r'href=["\']([^"\']*?/imovel/\d+[^"\']*)["\']',
                    r'href=["\']([^"\']*?megaleiloes\.com\.br/[^"\']*?/\d+[^"\']*)["\']',
                ]
                
                page_links = set()
                for pattern in patterns:
                    matches = re.findall(pattern, html, re.I)
                    for match in matches:
                        full_url = urljoin(config["website"], match)
                        # Filtrar apenas URLs de imóveis (não /imoveis)
                        if "megaleiloes" in full_url and "/imoveis" not in full_url:
                            page_links.add(full_url)
                
                links_before = len(all_links)
                all_links.update(page_links)
                links_added = len(all_links) - links_before
                
                print(f"      Links encontrados: {len(page_links)} | Novos: {links_added} | Total: {len(all_links)}")
                
                # Se não encontrou novos links, provavelmente chegou ao fim
                if links_added == 0 and page_num > 1:
                    print(f"      [INFO] Sem novos links, parando paginacao...")
                    break
                
                if len(all_links) >= max_items:
                    break
            
            print(f"\n   [TOTAL] Links: {len(all_links)}")
            
            # Converter para propriedades
            for url in list(all_links)[:max_items]:
                result["properties"].append({
                    "url": url,
                    "title": "",
                    "price": "",
                    "location": "",
                    "auctioneer_id": "megaleiloes",
                    "auctioneer_name": "Mega Leilões",
                })
            
            result["success"] = len(all_links) > 0
            result["total_extracted"] = len(result["properties"])
            
            await browser.close()
            
            print(f"\n   [OK] Extraidos: {result['total_extracted']} imoveis")
            
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   [ERRO] {e}")
    
    return result


def save_config(site_id: str, result: Dict):
    """Salva/atualiza config do site."""
    
    config_path = f"app/configs/sites/{site_id}.json"
    
    try:
        base_config = CONFIGS.get(site_id, {})
        
        config = {
            "id": site_id,
            "name": base_config.get("name", site_id),
            "website": base_config.get("website", ""),
            "enabled": result["success"] and result["total_extracted"] > 0,
            "method": result["method"],
            "listing_url": base_config.get("listing_url", ""),
            "selectors": base_config.get("selectors", {}),
            "api": base_config.get("api", {}),
            "last_scrape": {
                "date": datetime.now().isoformat(),
                "success": result["success"],
                "total_extracted": result["total_extracted"],
                "errors": result.get("errors", []),
            },
        }
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        status = "[OK]" if config["enabled"] else "[WARN]"
        print(f"   {status} Config salva: {config_path}")
        
    except Exception as e:
        print(f"   [ERRO] Erro ao salvar config: {e}")


async def main():
    """Executa scraping de todos os sites com seletores do MCP."""
    
    print("="*70)
    print("SCRAPING COM SELETORES DESCOBERTOS PELO MCP")
    print("="*70)
    print(f"\nInício: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 1. SOLD - API REST (Prioridade 1)
    sold_result = await scrape_sold_api(max_items=500)
    results.append(sold_result)
    save_config("sold", sold_result)
    
    with open("resultado_sold_final.json", "w", encoding="utf-8") as f:
        json.dump(sold_result, f, ensure_ascii=False, indent=2)
    
    await asyncio.sleep(2)
    
    # 2. PORTAL ZUK - Playwright (Prioridade 2)
    zuk_result = await scrape_portal_zuk(max_items=500)
    results.append(zuk_result)
    save_config("portalzuk", zuk_result)
    
    with open("resultado_zuk_final.json", "w", encoding="utf-8") as f:
        json.dump(zuk_result, f, ensure_ascii=False, indent=2)
    
    await asyncio.sleep(2)
    
    # 3. LANCE JUDICIAL - Playwright + Scroll (Prioridade 3)
    lance_result = await scrape_lance_judicial(max_items=200)
    results.append(lance_result)
    save_config("lancejudicial", lance_result)
    
    with open("resultado_lance_final.json", "w", encoding="utf-8") as f:
        json.dump(lance_result, f, ensure_ascii=False, indent=2)
    
    await asyncio.sleep(2)
    
    # 4. MEGA LEILÕES - SPA (Prioridade 4)
    mega_result = await scrape_mega_leiloes(max_items=600)
    results.append(mega_result)
    save_config("megaleiloes", mega_result)
    
    with open("resultado_mega_final.json", "w", encoding="utf-8") as f:
        json.dump(mega_result, f, ensure_ascii=False, indent=2)
    
    # Relatório final
    print("\n" + "="*70)
    print("RELATORIO FINAL - SELETORES MCP")
    print("="*70)
    
    total = 0
    print(f"\n{'Site':<25} {'Metodo':<15} {'Extraidos':<12} {'Status'}")
    print("-"*70)
    
    for r in results:
        status = "[OK]" if r["success"] else "[FALHA]"
        print(f"{r['name']:<25} {r['method']:<15} {r['total_extracted']:<12} {status}")
        total += r["total_extracted"]
    
    # Adicionar Sodré (anterior)
    print(f"{'Sodre Santoro':<25} {'playwright':<15} {'28':<12} [OK] (anterior)")
    total += 28
    
    print("-"*70)
    print(f"{'TOTAL':<40} {total:,}")
    
    # Exemplos
    print("\n" + "-"*70)
    print("EXEMPLOS DE IMOVEIS:")
    print("-"*70)
    
    for r in results:
        if r["properties"]:
            print(f"\n{r['name']} ({r['total_extracted']} imoveis):")
            for prop in r["properties"][:3]:
                title = prop.get("title") or "N/A"
                price = prop.get("price_formatted") or prop.get("price") or "N/A"
                location = prop.get("location") or "N/A"
                print(f"   - {title[:40]}...")
                print(f"     Preco: {price} | Local: {location}")
                print(f"     URL: {prop['url'][:60]}...")
    
    # Consolidado
    consolidated = {
        "generated_at": datetime.now().isoformat(),
        "mcp_discovery": True,
        "total_sites": len(results) + 1,  # +1 para Sodré
        "successful": sum(1 for r in results if r["success"]) + 1,
        "total_properties": total,
        "results": results,
    }
    
    with open("scraping_mcp_final.json", "w", encoding="utf-8") as f:
        json.dump(consolidated, f, ensure_ascii=False, indent=2)
    
    print(f"\n[REPORT] Relatorio: scraping_mcp_final.json")
    
    print("\n" + "="*70)
    print("[OK] SCRAPING FINALIZADO")
    print("="*70)
    print(f"\nFim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n[RESULTADO] {total:,} imoveis extraidos dos 5 gigantes!")


if __name__ == "__main__":
    asyncio.run(main())
