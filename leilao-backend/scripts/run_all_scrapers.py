#!/usr/bin/env python3
"""
Script Principal: Execução Completa de Todos os Scrapers
========================================================

Executa todos os scrapers configurados e consolida os resultados.

Sites:
1. Superbid Agregado - API (~11.475 imóveis)
2. Portal Zukerman - Playwright (~949 imóveis)
3. Mega Leilões - Playwright (~650 imóveis)
4. Lance Judicial - Playwright (~308 imóveis)
5. Sold Leilões - API (~143 imóveis)
6. Sodré Santoro - Playwright (~28 imóveis)
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from playwright.async_api import async_playwright

# Diretórios
RESULTS_DIR = Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

CONFIGS_DIR = Path(__file__).parent.parent / "app" / "configs" / "sites"

# Headers para APIs
API_HEADERS = {
    'Accept': 'application/json',
    'Origin': 'https://www.superbid.net',
    'Referer': 'https://www.superbid.net/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Stealth script para Playwright
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
"""


# ============================================================
# SCRAPER 1: SUPERBID AGREGADO (API)
# ============================================================

async def scrape_superbid_agregado(max_items: int = 12000) -> Dict:
    """Scraper para Superbid Agregado via API."""
    
    print("\n" + "="*70)
    print("[1/6] SUPERBID AGREGADO")
    print("="*70)
    
    result = {
        "id": "superbid_agregado",
        "name": "Superbid Agregado",
        "method": "api",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "success": False,
        "total_properties": 0,
        "properties": [],
        "errors": []
    }
    
    try:
        api_url = "https://offer-query.superbid.net/offers/"
        params = {
            "portalId": "2",
            "filter": "product.productType.description:imoveis;stores.id:[1161]",
            "requestOrigin": "store",
            "pageSize": "50",
            "pageNumber": "1"
        }
        
        page = 1
        property_ids = set()
        
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            while len(result["properties"]) < max_items:
                params["pageNumber"] = str(page)
                
                print(f"   Página {page}...", end=" ")
                
                try:
                    response = await client.get(api_url, params=params, headers=API_HEADERS)
                    response.raise_for_status()
                    data = response.json()
                    
                    offers = data.get("offers", [])
                    total = data.get("total", 0)
                    
                    if page == 1:
                        print(f"Total disponível: {total:,}")
                    else:
                        print(f"{len(offers)} itens")
                    
                    if not offers:
                        break
                    
                    for offer in offers:
                        if len(result["properties"]) >= max_items:
                            break
                        
                        offer_id = offer.get("id")
                        if not offer_id or offer_id in property_ids:
                            continue
                        
                        property_ids.add(offer_id)
                        
                        # Extrair dados
                        product = offer.get("product", {})
                        prop = {
                            "id": offer_id,
                            "url": f"https://www.superbid.net/produto/{offer_id}",
                            "title": product.get("shortDesc", "")[:200],
                            "price": offer.get("priceFormatted", ""),
                            "location": "",
                            "image_url": product.get("thumbnailUrl", ""),
                            "extracted_at": datetime.now().isoformat()
                        }
                        
                        # Localização
                        location = product.get("location", {})
                        if location:
                            city = location.get("city", "")
                            state = location.get("state", "")
                            if city or state:
                                prop["location"] = f"{city}, {state}".strip(", ")
                        
                        result["properties"].append(prop)
                    
                    if len(offers) < 50:
                        break
                    
                    page += 1
                    await asyncio.sleep(1.5)  # AUMENTADO: de 0.5s para 1.5s para evitar rate limiting
                    
                except Exception as e:
                    result["errors"].append(f"Página {page}: {str(e)}")
                    print(f"ERRO: {str(e)[:50]}")
                    break
        
        result["success"] = len(result["properties"]) > 0
        result["total_properties"] = len(result["properties"])
        result["finished_at"] = datetime.now().isoformat()
        
        print(f"   [OK] {result['total_properties']} imóveis extraídos")
        
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   [ERRO] {e}")
    
    return result


# ============================================================
# SCRAPER 2: PORTAL ZUKERMAN (PLAYWRIGHT)
# ============================================================

async def scrape_portal_zuk(max_items: int = 1000) -> Dict:
    """Scraper para Portal Zukerman usando botão 'Carregar mais'."""
    
    print("\n" + "="*70)
    print("[2/6] PORTAL ZUKERMAN")
    print("="*70)
    
    result = {
        "id": "portal_zuk",
        "name": "Portal Zukerman",
        "method": "playwright",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "success": False,
        "total_properties": 0,
        "properties": [],
        "errors": []
    }
    
    try:
        url = "https://www.portalzuk.com.br/leilao-de-imoveis"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            await context.add_init_script(STEALTH_SCRIPT)
            page = await context.new_page()
            
            print(f"   Acessando: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            all_links = set()
            
            # Extrair links iniciais
            initial_links = await page.query_selector_all('a[href*="/imovel/"]')
            for link in initial_links:
                href = await link.get_attribute("href")
                if href:
                    full_url = urljoin("https://www.portalzuk.com.br", href)
                    all_links.add(full_url)
            
            print(f"   Links iniciais: {len(all_links)}")
            
            # Clicar no botão "Carregar mais" até 35 vezes
            max_cliques = 35
            cliques_realizados = 0
            
            for click_num in range(max_cliques):
                if len(all_links) >= max_items:
                    break
                
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
                
                load_more_btn = await page.query_selector("#btn_carregarMais")
                
                if not load_more_btn:
                    print(f"   Botão não encontrado após {cliques_realizados} cliques")
                    break
                
                if not await load_more_btn.is_visible():
                    print(f"   Botão não visível após {cliques_realizados} cliques")
                    break
                
                links_before = len(all_links)
                
                try:
                    await page.evaluate("document.getElementById('btn_carregarMais').click()")
                    cliques_realizados += 1
                    await asyncio.sleep(4)
                except Exception as e:
                    result["errors"].append(f"Erro ao clicar: {str(e)}")
                    break
                
                new_links = await page.query_selector_all('a[href*="/imovel/"]')
                for link in new_links:
                    href = await link.get_attribute("href")
                    if href:
                        full_url = urljoin("https://www.portalzuk.com.br", href)
                        all_links.add(full_url)
                
                novos = len(all_links) - links_before
                print(f"   Clique {cliques_realizados}: {len(all_links)} links (+{novos} novos)")
                
                if novos == 0:
                    break
            
            # Criar propriedades
            for link in list(all_links)[:max_items]:
                result["properties"].append({
                    "url": link,
                    "title": "",
                    "price": "",
                    "location": "",
                    "extracted_at": datetime.now().isoformat()
                })
            
            await browser.close()
        
        result["success"] = len(result["properties"]) > 0
        result["total_properties"] = len(result["properties"])
        result["finished_at"] = datetime.now().isoformat()
        
        print(f"   [OK] {result['total_properties']} imóveis extraídos")
        
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   [ERRO] {e}")
    
    return result


# ============================================================
# SCRAPER 3: MEGA LEILÕES (PLAYWRIGHT)
# ============================================================

async def scrape_mega_leiloes(max_items: int = 700) -> Dict:
    """Scraper para Mega Leilões com paginação - RESTAURADO método que funcionou."""
    
    print("\n" + "="*70)
    print("[3/6] MEGA LEILÕES")
    print("="*70)
    
    result = {
        "id": "mega_leiloes",
        "name": "Mega Leilões",
        "method": "playwright",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "success": False,
        "total_properties": 0,
        "properties": [],
        "errors": []
    }
    
    try:
        base_url = "https://www.megaleiloes.com.br/imoveis"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='pt-BR'
            )
            await context.add_init_script(STEALTH_SCRIPT)
            page = await context.new_page()
            
            all_links = set()
            max_pages = 15
            
            for page_num in range(1, max_pages + 1):
                if page_num == 1:
                    page_url = base_url
                else:
                    page_url = f"{base_url}?pagina={page_num}"
                
                print(f"   Página {page_num}...", end=" ")
                
                try:
                    await page.goto(page_url, wait_until='domcontentloaded', timeout=60000)
                    
                    # Espera longa para SPA React (15s primeira página, 5s demais)
                    wait_time = 15 if page_num == 1 else 5
                    if page_num == 1:
                        print(f"Aguardando SPA ({wait_time}s)...", end=" ")
                    await asyncio.sleep(wait_time)
                    
                    # Scroll para carregar conteúdo lazy
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                    
                    # Extrair HTML e buscar padrões (CORRIGIDO: usar /auditorio/)
                    html = await page.content()
                    import re
                    patterns = [
                        r'href=["\']([^"\']*?/auditorio/\d+/\d+[^"\']*)["\']',  # Padrão correto: /auditorio/{id}/{id}
                        r'href=["\']([^"\']*?/leilao/\d+[^"\']*)["\']',
                        r'href=["\']([^"\']*?megaleiloes\.com\.br/[^"\']*?/\d+[^"\']*)["\']',
                    ]
                    
                    page_links = set()
                    for pattern in patterns:
                        matches = re.findall(pattern, html, re.I)
                        for match in matches:
                            full_url = urljoin("https://www.megaleiloes.com.br", match)
                            # Filtrar apenas URLs de imóveis (não /imoveis)
                            if "megaleiloes" in full_url and "/imoveis" not in full_url:
                                page_links.add(full_url)
                    
                    links_before = len(all_links)
                    all_links.update(page_links)
                    links_added = len(all_links) - links_before
                    
                    print(f"{links_added} novos links (total: {len(all_links)})")
                    
                    # Se não encontrou novos links, provavelmente chegou ao fim
                    if links_added == 0 and page_num > 1:
                        print("   Sem novos links, parando...")
                        break
                    
                    if len(all_links) >= max_items:
                        break
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    result["errors"].append(f"Página {page_num}: {str(e)}")
                    print(f"ERRO: {str(e)[:50]}")
                    break
            
            # Criar propriedades
            for link in list(all_links)[:max_items]:
                result["properties"].append({
                    "url": link,
                    "title": "",
                    "price": "",
                    "location": "",
                    "extracted_at": datetime.now().isoformat()
                })
            
            await browser.close()
        
        result["success"] = len(result["properties"]) > 0
        result["total_properties"] = len(result["properties"])
        result["finished_at"] = datetime.now().isoformat()
        
        print(f"   [OK] {result['total_properties']} imóveis extraídos")
        
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   [ERRO] {e}")
    
    return result


# ============================================================
# SCRAPER 4: LANCE JUDICIAL (PLAYWRIGHT)
# ============================================================

async def scrape_lance_judicial(max_items: int = 350) -> Dict:
    """Scraper para Lance Judicial com paginação PJAX."""
    
    print("\n" + "="*70)
    print("[4/6] LANCE JUDICIAL")
    print("="*70)
    
    result = {
        "id": "lance_judicial",
        "name": "Lance Judicial",
        "method": "playwright",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "success": False,
        "total_properties": 0,
        "properties": [],
        "errors": []
    }
    
    try:
        base_url = "https://www.grupolance.com.br/imoveis"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            await context.add_init_script(STEALTH_SCRIPT)
            page = await context.new_page()
            
            print(f"   Acessando: {base_url}")
            await page.goto(base_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(5)
            
            all_links = set()
            max_pages = 10
            page_num = 1
            
            while len(all_links) < max_items and page_num <= max_pages:
                print(f"   Página {page_num}...", end=" ")
                
                try:
                    await page.wait_for_selector('.card', timeout=10000)
                    await page.wait_for_load_state('networkidle', timeout=15000)
                    await asyncio.sleep(3)
                    
                    links = await page.query_selector_all('.card a, [class*="card"] a')
                    new_count = 0
                    
                    for link in links:
                        href = await link.get_attribute("href")
                        if href and '/imoveis/' in href:
                            full_url = urljoin("https://www.grupolance.com.br", href)
                            if full_url not in all_links:
                                all_links.add(full_url)
                                new_count += 1
                    
                    print(f"{new_count} novos links (total: {len(all_links)})")
                    
                    if new_count == 0:
                        break
                    
                    # Tentar ir para próxima página
                    if page_num < max_pages:
                        next_page_num = page_num + 1
                        next_btn = await page.query_selector(f'a[href*="pagina={next_page_num}"]')
                        
                        if next_btn and await next_btn.is_visible():
                            await next_btn.click()
                            await page.wait_for_load_state('networkidle', timeout=15000)
                            await asyncio.sleep(5)
                            page_num = next_page_num
                        else:
                            break
                    else:
                        break
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    result["errors"].append(f"Página {page_num}: {str(e)}")
                    print(f"ERRO: {str(e)[:50]}")
                    break
            
            # Criar propriedades
            for link in list(all_links)[:max_items]:
                result["properties"].append({
                    "url": link,
                    "title": "",
                    "price": "",
                    "location": "",
                    "extracted_at": datetime.now().isoformat()
                })
            
            await browser.close()
        
        result["success"] = len(result["properties"]) > 0
        result["total_properties"] = len(result["properties"])
        result["finished_at"] = datetime.now().isoformat()
        
        print(f"   [OK] {result['total_properties']} imóveis extraídos")
        
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   [ERRO] {e}")
    
    return result


# ============================================================
# SCRAPER 5: SOLD LEILÕES (API)
# ============================================================

async def scrape_sold(max_items: int = 150) -> Dict:
    """Scraper para Sold Leilões via API."""
    
    print("\n" + "="*70)
    print("[5/6] SOLD LEILÕES")
    print("="*70)
    
    result = {
        "id": "sold",
        "name": "Sold Leilões",
        "method": "api",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "success": False,
        "total_properties": 0,
        "properties": [],
        "errors": []
    }
    
    try:
        api_url = "https://offer-query.superbid.net/offers/"
        params = {
            "portalId": "2",
            "filter": "product.productType.description:imoveis;stores.id:[1161,1741]",
            "requestOrigin": "store",
            "pageSize": "50",
            "pageNumber": "1"
        }
        
        page = 1
        property_ids = set()
        
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            while len(result["properties"]) < max_items:
                params["pageNumber"] = str(page)
                
                print(f"   Página {page}...", end=" ")
                
                try:
                    response = await client.get(api_url, params=params, headers=API_HEADERS)
                    response.raise_for_status()
                    data = response.json()
                    
                    offers = data.get("offers", [])
                    total = data.get("total", 0)
                    
                    if page == 1:
                        print(f"Total disponível: {total:,}")
                    else:
                        print(f"{len(offers)} itens")
                    
                    if not offers:
                        break
                    
                    for offer in offers:
                        if len(result["properties"]) >= max_items:
                            break
                        
                        offer_id = offer.get("id")
                        if not offer_id or offer_id in property_ids:
                            continue
                        
                        property_ids.add(offer_id)
                        
                        # Extrair dados
                        product = offer.get("product", {})
                        prop = {
                            "id": offer_id,
                            "url": f"https://www.sold.com.br/produto/{offer_id}",
                            "title": product.get("shortDesc", "")[:200],
                            "price": offer.get("priceFormatted", ""),
                            "location": "",
                            "image_url": product.get("thumbnailUrl", ""),
                            "extracted_at": datetime.now().isoformat()
                        }
                        
                        # Localização
                        location = product.get("location", {})
                        if location:
                            city = location.get("city", "")
                            state = location.get("state", "")
                            if city or state:
                                prop["location"] = f"{city}, {state}".strip(", ")
                        
                        result["properties"].append(prop)
                    
                    if len(offers) < 50:
                        break
                    
                    page += 1
                    await asyncio.sleep(1.5)  # AUMENTADO: de 0.5s para 1.5s para evitar rate limiting
                    
                except Exception as e:
                    result["errors"].append(f"Página {page}: {str(e)}")
                    print(f"ERRO: {str(e)[:50]}")
                    break
        
        result["success"] = len(result["properties"]) > 0
        result["total_properties"] = len(result["properties"])
        result["finished_at"] = datetime.now().isoformat()
        
        print(f"   [OK] {result['total_properties']} imóveis extraídos")
        
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   [ERRO] {e}")
    
    return result


# ============================================================
# SCRAPER 6: SODRÉ SANTORO (PLAYWRIGHT)
# ============================================================

async def scrape_sodre_santoro(max_items: int = 50) -> Dict:
    """Scraper para Sodré Santoro - RESTAURADO método que funcionou."""
    
    print("\n" + "="*70)
    print("[6/6] SODRÉ SANTORO")
    print("="*70)
    
    result = {
        "id": "sodre_santoro",
        "name": "Sodré Santoro",
        "method": "playwright",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "success": False,
        "total_properties": 0,
        "properties": [],
        "errors": []
    }
    
    try:
        base_url = "https://www.sodresantoro.com.br/imoveis"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            await context.add_init_script(STEALTH_SCRIPT)
            page = await context.new_page()
            
            print(f"   Acessando: {base_url}")
            await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            all_links = set()
            max_pages = 5
            page_num = 1
            
            while len(all_links) < max_items and page_num <= max_pages:
                if page_num > 1:
                    page_url = f"{base_url}?page={page_num}"
                    await page.goto(page_url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(2)
                
                print(f"   Página {page_num}...", end=" ")
                
                try:
                    # Aguardar carregamento
                    await asyncio.sleep(3)
                    
                    # Scroll para carregar conteúdo
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                    
                    # CORRIGIDO: Buscar links com padrões corretos (leilao.sodresantoro.com.br/leilao/{id}/lote/{id}/)
                    # Seletores: .card a ou a[href*='/leilao/']
                    links = await page.query_selector_all('.card a, a[href*="/leilao/"], a[href*="/lote/"]')
                    
                    # Também buscar no HTML com padrões corretos
                    html = await page.content()
                    import re
                    patterns = [
                        r'href=["\']([^"\']*?leilao\.sodresantoro\.com\.br/leilao/\d+/lote/\d+[^"\']*)["\']',  # Padrão correto
                        r'href=["\']([^"\']*?/leilao/\d+[^"\']*)["\']',
                        r'href=["\']([^"\']*?/lote/\d+[^"\']*)["\']',
                        r'href=["\']([^"\']*?sodresantoro\.com\.br/leilao/\d+[^"\']*)["\']'
                    ]
                    
                    new_count = 0
                    
                    # Processar links do seletor
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            # Normalizar URL (pode ser relativa ou absoluta)
                            if href.startswith('http'):
                                full_url = href
                            elif href.startswith('//'):
                                full_url = 'https:' + href
                            elif href.startswith('/'):
                                full_url = urljoin("https://www.sodresantoro.com.br", href)
                            else:
                                full_url = urljoin(base_url, href)
                            
                            # Aceitar URLs de leilão ou lote
                            if ('/leilao/' in full_url or '/lote/' in full_url) and full_url not in all_links:
                                all_links.add(full_url)
                                new_count += 1
                    
                    # Processar links do HTML
                    for pattern in patterns:
                        matches = re.findall(pattern, html, re.I)
                        for match in matches:
                            if match.startswith('http'):
                                full_url = match
                            else:
                                full_url = urljoin("https://www.sodresantoro.com.br", match)
                            
                            if ('/leilao/' in full_url or '/lote/' in full_url) and full_url not in all_links:
                                all_links.add(full_url)
                                new_count += 1
                    
                    print(f"{new_count} novos links (total: {len(all_links)})")
                    
                    if new_count == 0:
                        break
                    
                    page_num += 1
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    result["errors"].append(f"Página {page_num}: {str(e)}")
                    print(f"ERRO: {str(e)[:50]}")
                    break
            
            # Criar propriedades
            for link in list(all_links)[:max_items]:
                result["properties"].append({
                    "url": link,
                    "title": "",
                    "price": "",
                    "location": "",
                    "extracted_at": datetime.now().isoformat()
                })
            
            await browser.close()
        
        result["success"] = len(result["properties"]) > 0
        result["total_properties"] = len(result["properties"])
        result["finished_at"] = datetime.now().isoformat()
        
        print(f"   [OK] {result['total_properties']} imóveis extraídos")
        
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   [ERRO] {e}")
    
    return result


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

async def main():
    """Executa todos os scrapers e consolida resultados."""
    
    print("="*70)
    print("SCRAPING COMPLETO - LEILOHUB")
    print("="*70)
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    all_results = []
    
    # Executar scrapers em sequência
    scrapers = [
        ("superbid_agregado", scrape_superbid_agregado, 12000),
        ("portal_zuk", scrape_portal_zuk, 1000),
        ("mega_leiloes", scrape_mega_leiloes, 700),
        ("lance_judicial", scrape_lance_judicial, 350),
        ("sold", scrape_sold, 150),
        ("sodre_santoro", scrape_sodre_santoro, 50),
    ]
    
    for scraper_id, scraper_func, max_items in scrapers:
        try:
            result = await scraper_func(max_items)
            all_results.append(result)
            
            # Salvar resultado individual
            output_file = RESULTS_DIR / f"resultado_{scraper_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"   [SAVED] {output_file}")
            
            # Pausa entre scrapers
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"   [ERRO FATAL] {scraper_id}: {e}")
            all_results.append({
                "id": scraper_id,
                "success": False,
                "errors": [str(e)],
                "total_properties": 0
            })
    
    # Consolidar resultados
    print("\n" + "="*70)
    print("CONSOLIDANDO RESULTADOS")
    print("="*70)
    
    consolidated = {
        "data_execucao": datetime.now().strftime("%Y-%m-%d"),
        "total_imoveis": sum(r.get("total_properties", 0) for r in all_results),
        "por_fonte": {},
        "resumo": {
            "fontes_ativas": sum(1 for r in all_results if r.get("success")),
            "taxa_sucesso": f"{sum(1 for r in all_results if r.get('success')) * 100 / len(all_results):.1f}%",
            "erros": []
        }
    }
    
    for result in all_results:
        scraper_id = result.get("id", "unknown")
        consolidated["por_fonte"][scraper_id] = {
            "total": result.get("total_properties", 0),
            "arquivo": f"resultado_{scraper_id}.json",
            "success": result.get("success", False),
            "errors": result.get("errors", [])
        }
        
        if result.get("errors"):
            consolidated["resumo"]["erros"].extend([
                f"{scraper_id}: {e}" for e in result.get("errors", [])
            ])
    
    # Salvar consolidado
    consolidated_file = RESULTS_DIR / "scraping_consolidado_final.json"
    with open(consolidated_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] Consolidado salvo: {consolidated_file}")
    
    # Relatório final
    print("\n" + "="*70)
    print("RELATÓRIO FINAL")
    print("="*70)
    print(f"\n{'Fonte':<25} {'Esperado':<12} {'Extraído':<12} {'Status':<10}")
    print("-"*70)
    
    expected = {
        "superbid_agregado": 11475,
        "portal_zuk": 949,
        "mega_leiloes": 650,
        "lance_judicial": 308,
        "sold": 143,
        "sodre_santoro": 28
    }
    
    for result in all_results:
        scraper_id = result.get("id", "unknown")
        name = result.get("name", scraper_id)
        extracted = result.get("total_properties", 0)
        exp = expected.get(scraper_id, 0)
        status = "OK" if result.get("success") else "FALHA"
        
        print(f"{name:<25} ~{exp:<11} {extracted:<12} {status:<10}")
    
    total_expected = sum(expected.values())
    total_extracted = consolidated["total_imoveis"]
    print("-"*70)
    print(f"{'TOTAL':<25} ~{total_expected:<11} {total_extracted:<12}")
    
    print("\n" + "="*70)
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())

