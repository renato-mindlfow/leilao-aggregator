# ============================================================
# TAREFA AUTÔNOMA: Explorar Descobertas da Investigação
# ============================================================
# Para: Cursor Agent
# Modo: AUTÔNOMO
# Tempo estimado: 20-30 minutos
# ============================================================

"""
╔══════════════════════════════════════════════════════════════╗
║  DESCOBERTAS DA INVESTIGAÇÃO                                 ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. SOLD LEILÕES - API REST descoberta! 🎉                   ║
║     URL: offer-query.superbid.net/offers/                    ║
║     Parâmetros identificados para filtrar imóveis            ║
║                                                              ║
║  2. MEGA LEILÕES - Seletores identificados                   ║
║     Cards: .cards-container, .card-bank                      ║
║     Preço: .card-price                                       ║
║     Requer mais tempo de espera (SPA React)                  ║
║                                                              ║
║  3. LANCE JUDICIAL - Seletores Bootstrap                     ║
║     Cards: .card, .card-gavel-card                           ║
║     Preço: .card-price                                       ║
║     Cloudflare ativo - precisa stealth robusto               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import asyncio
import httpx
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

# ============================================================
# PARTE 1: EXPLORAR API DO SOLD (SUPERBID)
# ============================================================

async def explorar_api_sold() -> Dict:
    """
    Tenta acessar a API REST do Sold/Superbid diretamente.
    """
    
    print("="*70)
    print("EXPLORANDO API DO SOLD (SUPERBID)")
    print("="*70)
    
    result = {
        "site": "Sold Leilões",
        "method": "api_rest",
        "success": False,
        "properties": [],
        "total_found": 0,
        "api_url": None,
        "errors": [],
    }
    
    # URLs de API para testar
    api_urls = [
        # API principal descoberta
        "https://offer-query.superbid.net/offers/?portalId=2&filter=product.productType.description:imoveis&pageNumber=1&pageSize=50",
        "https://offer-query.superbid.net/offers/?portalId=15&filter=product.productType.description:imoveis&pageNumber=1&pageSize=50",
        "https://offer-query.superbid.net/offers/?portalId=2&pageNumber=1&pageSize=50",
        # Sold específico
        "https://offer-query.superbid.net/offers/?filter=stores.id:1161&pageNumber=1&pageSize=50",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'pt-BR,pt;q=0.9',
        'Origin': 'https://www.sold.com.br',
        'Referer': 'https://www.sold.com.br/',
    }
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        for api_url in api_urls:
            try:
                print(f"\n[TESTANDO] {api_url[:70]}...")
                
                response = await client.get(api_url, headers=headers)
                
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # Analisar estrutura
                        if isinstance(data, dict):
                            print(f"   Tipo: Objeto JSON")
                            print(f"   Chaves: {list(data.keys())[:5]}")
                            
                            # Procurar array de ofertas
                            offers = None
                            if 'offers' in data:
                                offers = data['offers']
                            elif 'data' in data:
                                offers = data['data']
                            elif 'items' in data:
                                offers = data['items']
                            elif 'results' in data:
                                offers = data['results']
                            
                            if offers and isinstance(offers, list):
                                print(f"   [OK] {len(offers)} ofertas encontradas!")
                                
                                result["success"] = True
                                result["api_url"] = api_url
                                result["total_found"] = len(offers)
                                
                                # Extrair dados das primeiras ofertas
                                for offer in offers[:10]:
                                    prop = extract_property_from_api(offer)
                                    if prop:
                                        result["properties"].append(prop)
                                
                                # Mostrar exemplo
                                if result["properties"]:
                                    print(f"\n   Exemplo de imóvel:")
                                    sample = result["properties"][0]
                                    print(f"      Título: {sample.get('title', 'N/A')[:50]}...")
                                    print(f"      Preço: {sample.get('price', 'N/A')}")
                                    print(f"      Local: {sample.get('city', 'N/A')}/{sample.get('state', 'N/A')}")
                                
                                return result
                        
                        elif isinstance(data, list):
                            print(f"   Tipo: Array JSON com {len(data)} itens")
                            if len(data) > 0:
                                result["success"] = True
                                result["api_url"] = api_url
                                result["total_found"] = len(data)
                                
                                for item in data[:10]:
                                    prop = extract_property_from_api(item)
                                    if prop:
                                        result["properties"].append(prop)
                                
                                return result
                    
                    except json.JSONDecodeError:
                        print(f"   [WARN] Resposta nao e JSON valido")
                
                elif response.status_code == 403:
                    print(f"   [WARN] Acesso negado (pode precisar de autenticacao)")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"   [ERRO] {e}")
                result["errors"].append(str(e))
    
    return result


def extract_property_from_api(data: Dict) -> Optional[Dict]:
    """Extrai dados de propriedade de resposta da API."""
    
    if not isinstance(data, dict):
        return None
    
    prop = {
        "source": "api",
        "auctioneer_id": "sold",
        "auctioneer_name": "Sold Leilões",
    }
    
    # Campos comuns em APIs de leilão
    field_mappings = {
        "title": ["title", "name", "description", "productName", "titulo", "nome"],
        "price": ["price", "currentPrice", "minimumBid", "valor", "preco", "startingPrice"],
        "city": ["city", "cidade", "location.city", "address.city"],
        "state": ["state", "estado", "uf", "location.state", "address.state"],
        "url": ["url", "link", "detailUrl", "href"],
        "image_url": ["image", "imageUrl", "photo", "thumbnail", "imagem"],
        "category": ["category", "type", "productType", "categoria", "tipo"],
        "area": ["area", "size", "metragem", "m2"],
    }
    
    for field, candidates in field_mappings.items():
        for candidate in candidates:
            # Suporta campos aninhados como "location.city"
            value = get_nested_value(data, candidate)
            if value:
                prop[field] = value
                break
    
    # Construir URL se não existir
    if not prop.get("url") and data.get("id"):
        prop["url"] = f"https://www.sold.com.br/leilao/{data['id']}"
    
    return prop if prop.get("title") or prop.get("price") else None


def get_nested_value(data: Dict, key: str):
    """Obtém valor de chave aninhada (ex: 'location.city')."""
    keys = key.split('.')
    value = data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return None
    return value


# ============================================================
# PARTE 2: MEGA LEILÕES COM SELETORES DESCOBERTOS
# ============================================================

async def testar_mega_leiloes_melhorado() -> Dict:
    """
    Testa Mega Leilões com os seletores descobertos e mais tempo de espera.
    """
    
    print("\n" + "="*70)
    print("TESTANDO MEGA LEILOES (SELETORES MELHORADOS)")
    print("="*70)
    
    result = {
        "site": "Mega Leilões",
        "method": "playwright_stealth_improved",
        "success": False,
        "properties": [],
        "total_found": 0,
        "errors": [],
    }
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        result["errors"].append("Playwright não instalado")
        return result
    
    # Seletores descobertos na investigação
    selectors = {
        "card": ".card-bank, .cards-container, [class*='card-auction']",
        "link": "a[href*='/leilao/'], a[href*='/imovel/']",
        "price": ".card-price, [class*='price']",
        "location": ".card-locality, [class*='locality']",
        "title": ".card-title, h3, h4",
    }
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-BR',
            )
            
            # Stealth scripts
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            """)
            
            page = await context.new_page()
            
            # URLs para testar
            urls = [
                "https://www.megaleiloes.com.br/",
                "https://www.megaleiloes.com.br/buscar",
            ]
            
            for url in urls:
                print(f"\n[TESTANDO] {url}")
                
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    
                    # IMPORTANTE: Esperar mais tempo para SPA carregar
                    print("   [AGUARDANDO] 15 segundos para SPA renderizar...")
                    await asyncio.sleep(15)
                    
                    # Scroll extensivo
                    print("   [SCROLL] Fazendo scroll...")
                    for i in range(10):
                        await page.evaluate(f"window.scrollBy(0, {i * 300})")
                        await asyncio.sleep(0.5)
                    
                    await asyncio.sleep(3)
                    
                    # Tentar encontrar cards com seletores descobertos
                    html = await page.content()
                    
                    # Procurar por links de leilão/imóvel
                    links = set()
                    patterns = [r'/leilao/\d+', r'/imovel/\d+', r'/lote/\d+']
                    
                    for pattern in patterns:
                        matches = re.findall(f'href=["\']([^"\']*{pattern}[^"\']*)["\']', html, re.I)
                        for match in matches:
                            full_url = urljoin("https://www.megaleiloes.com.br", match)
                            links.add(full_url)
                    
                    if links:
                        print(f"   [OK] {len(links)} links encontrados!")
                        result["success"] = True
                        result["total_found"] = len(links)
                        
                        # Extrair alguns dados
                        for link in list(links)[:5]:
                            result["properties"].append({
                                "url": link,
                                "source": "megaleiloes",
                            })
                        
                        break
                    else:
                        print(f"   [WARN] Nenhum link encontrado")
                        
                        # Salvar HTML para debug
                        debug_file = f"mega_debug_{datetime.now().strftime('%H%M%S')}.html"
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(html)
                        print(f"   [DEBUG] HTML salvo em: {debug_file}")
                
                except Exception as e:
                    print(f"   [ERRO] {e}")
                    result["errors"].append(str(e))
            
            await browser.close()
    
    except Exception as e:
        result["errors"].append(str(e))
        print(f"❌ Erro fatal: {e}")
    
    return result


# ============================================================
# PARTE 3: LANCE JUDICIAL COM STEALTH ROBUSTO
# ============================================================

async def testar_lance_judicial_melhorado() -> Dict:
    """
    Testa Lance Judicial com stealth mais robusto para contornar Cloudflare.
    """
    
    print("\n" + "="*70)
    print("TESTANDO LANCE JUDICIAL (STEALTH ROBUSTO)")
    print("="*70)
    
    result = {
        "site": "Lance Judicial",
        "method": "playwright_stealth_robust",
        "success": False,
        "properties": [],
        "total_found": 0,
        "errors": [],
    }
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        result["errors"].append("Playwright não instalado")
        return result
    
    # Stealth scripts avançados para Cloudflare
    stealth_script = """
        // Webdriver
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        delete navigator.__proto__.webdriver;
        
        // Plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const arr = [1,2,3,4,5];
                arr.item = i => arr[i];
                arr.namedItem = n => null;
                arr.refresh = () => {};
                return arr;
            }
        });
        
        // Chrome
        window.chrome = {
            runtime: {id: undefined},
            loadTimes: () => ({}),
            csi: () => ({}),
            app: {isInstalled: false}
        };
        
        // Languages
        Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
        Object.defineProperty(navigator, 'language', {get: () => 'pt-BR'});
        
        // Platform
        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});
        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
        Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
        
        // Permissions
        const origQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                origQuery(parameters)
        );
    """
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-web-security',
                    '--window-size=1920,1080',
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                }
            )
            
            await context.add_init_script(stealth_script)
            
            page = await context.new_page()
            
            # URLs para testar
            urls = [
                "https://www.lancejudicial.com.br/",
                "https://www.grupolance.com.br/",
            ]
            
            for url in urls:
                print(f"\n[TESTANDO] {url}")
                
                try:
                    await page.goto(url, wait_until='networkidle', timeout=45000)
                    
                    # Verificar Cloudflare challenge
                    page_text = await page.evaluate("() => document.body.innerText")
                    
                    if 'checking your browser' in page_text.lower() or 'just a moment' in page_text.lower():
                        print("   [AGUARDANDO] Cloudflare challenge detectado, aguardando...")
                        await asyncio.sleep(10)
                        
                        # Verificar novamente
                        page_text = await page.evaluate("() => document.body.innerText")
                    
                    # Aguardar renderização
                    await asyncio.sleep(5)
                    
                    # Scroll
                    for i in range(5):
                        await page.evaluate(f"window.scrollBy(0, {i * 400})")
                        await asyncio.sleep(0.3)
                    
                    await asyncio.sleep(2)
                    
                    html = await page.content()
                    
                    # Seletores Bootstrap descobertos
                    # Procurar cards
                    cards_found = len(re.findall(r'class=["\'][^"\']*card[^"\']*["\']', html, re.I))
                    print(f"   [CARDS] Encontrados: {cards_found}")
                    
                    # Procurar links
                    links = set()
                    patterns = [r'/leilao/', r'/imovel/', r'/lote/', r'/bem/']
                    
                    for pattern in patterns:
                        matches = re.findall(f'href=["\']([^"\']*{pattern}[^"\']*)["\']', html, re.I)
                        for match in matches:
                            full_url = urljoin(url, match)
                            links.add(full_url)
                    
                    if links:
                        print(f"   [OK] {len(links)} links encontrados!")
                        result["success"] = True
                        result["total_found"] = len(links)
                        
                        for link in list(links)[:10]:
                            result["properties"].append({
                                "url": link,
                                "source": "lancejudicial",
                            })
                        
                        break
                    else:
                        print(f"   [WARN] Nenhum link de imovel encontrado")
                        
                        # Verificar se passou pelo Cloudflare
                        if 'cloudflare' in html.lower():
                            print(f"   [CF] Cloudflare ainda ativo no HTML")
                        
                        # Salvar para debug
                        debug_file = f"lance_debug_{datetime.now().strftime('%H%M%S')}.html"
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(html)
                        print(f"   [DEBUG] HTML salvo: {debug_file}")
                
                except Exception as e:
                    print(f"   [ERRO] {e}")
                    result["errors"].append(str(e))
            
            await browser.close()
    
    except Exception as e:
        result["errors"].append(str(e))
        print(f"❌ Erro fatal: {e}")
    
    return result


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

async def main():
    """Função principal."""
    
    print("="*70)
    print("EXPLORANDO DESCOBERTAS DA INVESTIGACAO")
    print("="*70)
    
    results = []
    
    # 1. API do Sold (maior potencial)
    sold_result = await explorar_api_sold()
    results.append(sold_result)
    
    # 2. Mega Leilões com seletores
    mega_result = await testar_mega_leiloes_melhorado()
    results.append(mega_result)
    
    # 3. Lance Judicial com stealth robusto
    lance_result = await testar_lance_judicial_melhorado()
    results.append(lance_result)
    
    # Relatório final
    print("\n" + "="*70)
    print("RELATORIO FINAL")
    print("="*70)
    
    success_count = sum(1 for r in results if r["success"])
    total_properties = sum(r["total_found"] for r in results)
    
    print(f"\nSites testados: {len(results)}")
    print(f"Sucesso: {success_count}")
    print(f"Total imóveis: {total_properties}")
    
    for r in results:
        status = "[OK]" if r["success"] else "[FALHA]"
        print(f"\n{status} {r['site']}")
        print(f"   Método: {r['method']}")
        print(f"   Imóveis: {r['total_found']}")
        
        if r.get("api_url"):
            print(f"   API: {r['api_url'][:60]}...")
        
        if r["properties"]:
            sample = r["properties"][0]
            if sample.get("title"):
                print(f"   Exemplo: {sample.get('title', 'N/A')[:40]}...")
            if sample.get("price"):
                print(f"   Preço: {sample.get('price')}")
    
    # Salvar relatório
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_sites": len(results),
        "successful": success_count,
        "total_properties": total_properties,
        "results": results
    }
    
    with open("exploracao_final_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n[REPORT] Relatorio salvo: exploracao_final_report.json")
    
    # Atualizar configs para sites que funcionaram
    if sold_result["success"]:
        save_sold_api_config(sold_result)
    
    print("\n" + "="*70)
    print("[OK] EXPLORACAO CONCLUIDA")
    print("="*70)


def save_sold_api_config(result: Dict):
    """Salva config específica para API do Sold."""
    
    config = {
        "id": "sold",
        "name": "Sold Leilões",
        "website": "https://www.sold.com.br",
        "enabled": True,
        
        "scraping": {
            "method": "api_rest",  # Método especial para API
            "api_url": result["api_url"],
            "rate_limit_seconds": 2.0,
            "max_pages": 50,
            "page_size": 50,
        },
        
        "api_config": {
            "base_url": "https://offer-query.superbid.net/offers/",
            "headers": {
                "Origin": "https://www.sold.com.br",
                "Referer": "https://www.sold.com.br/",
            },
            "params": {
                "filter": "product.productType.description:imoveis",
                "pageSize": 50,
            }
        },
        
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "method_discovered": "api_rest",
            "properties_at_discovery": result["total_found"],
        }
    }
    
    config_path = "app/configs/sites/sold.json"
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"\n[CONFIG] API salva: {config_path}")


if __name__ == "__main__":
    asyncio.run(main())
