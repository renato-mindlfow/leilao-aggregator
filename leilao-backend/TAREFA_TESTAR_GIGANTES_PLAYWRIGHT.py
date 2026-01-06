# ============================================================
# TAREFA AUTÔNOMA: Testar Gigantes com Playwright
# ============================================================
# Para: Cursor Agent
# Modo: AUTÔNOMO
# Tempo estimado: 15-20 minutos
# ============================================================

"""
╔══════════════════════════════════════════════════════════════╗
║  CONTEXTO                                                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  A análise mostrou que os 5 gigantes precisam de Playwright: ║
║                                                              ║
║  - 3 têm Cloudflare (Mega, Zuk, Sold)                        ║
║  - 2 precisam investigação (Sodré, Lance Judicial)           ║
║                                                              ║
║  BOA NOTÍCIA: Já temos scrapers Playwright funcionando!      ║
║                                                              ║
║  Esta tarefa vai:                                            ║
║  1. Testar Portal Zuk com scraper existente                  ║
║  2. Adaptar padrão Playwright para outros gigantes           ║
║  3. Extrair imóveis reais                                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

# Adicionar path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# CONFIGURAÇÃO DOS GIGANTES
# ============================================================

GIGANTES_CONFIG = {
    "megaleiloes": {
        "name": "Mega Leilões",
        "website": "https://www.megaleiloes.com.br",
        "listing_urls": [
            "https://www.megaleiloes.com.br/",
            "https://www.megaleiloes.com.br/buscar",
            "https://www.megaleiloes.com.br/buscar?tipo=imovel",
        ],
        "link_patterns": [r"/leilao/\d+", r"/imovel/", r"/lote/"],
        "selectors": {
            "property_link": "a[href*='/leilao/']",
            "title": "h1, h2, .titulo, .title",
            "price": ".valor, .preco, .lance",
        }
    },
    "portalzuk": {
        "name": "Portal Zukerman",
        "website": "https://www.portalzuk.com.br",
        "listing_urls": [
            "https://www.portalzuk.com.br/",
            "https://www.portalzuk.com.br/leilao-de-imoveis",
            "https://www.portalzuk.com.br/imovel",
        ],
        "link_patterns": [r"/imovel/\d+", r"/lote/"],
        "selectors": {
            "property_link": "a[href*='/imovel/']",
            "title": "h1, h2, .property-title",
            "price": ".price, .valor",
        }
    },
    "sold": {
        "name": "Sold Leilões",
        "website": "https://www.sold.com.br",
        "listing_urls": [
            "https://www.sold.com.br/",
            "https://www.sold.com.br/leiloes",
            "https://www.sold.com.br/imoveis",
        ],
        "link_patterns": [r"/leilao/", r"/imovel/", r"/item/"],
        "selectors": {
            "property_link": "a[href*='/leilao/'], a[href*='/imovel/']",
            "title": "h1, h2, .titulo",
            "price": ".preco, .valor",
        }
    },
    "sodresantoro": {
        "name": "Sodré Santoro",
        "website": "https://www.sodresantoro.com.br",
        "listing_urls": [
            "https://www.sodresantoro.com.br/",
            "https://www.sodresantoro.com.br/leiloes",
            "https://www.sodresantoro.com.br/imoveis",
        ],
        "link_patterns": [r"/lote/", r"/imovel/", r"/detalhe/"],
        "selectors": {
            "property_link": "a[href*='/lote/'], a[href*='/imovel/']",
            "title": "h1, h2, .titulo",
            "price": ".valor, .preco",
        }
    },
    "lancejudicial": {
        "name": "Lance Judicial",
        "website": "https://www.lancejudicial.com.br",
        "listing_urls": [
            "https://www.lancejudicial.com.br/",
            "https://www.lancejudicial.com.br/leiloes",
            "https://www.lancejudicial.com.br/imoveis",
        ],
        "link_patterns": [r"/leilao/", r"/imovel/", r"/lote/"],
        "selectors": {
            "property_link": "a[href*='/leilao/'], a[href*='/imovel/']",
            "title": "h1, h2, .titulo",
            "price": ".valor, .preco, .lance",
        }
    },
}

# ============================================================
# SCRAPER PLAYWRIGHT GENÉRICO
# ============================================================

# Scripts de stealth
STEALTH_SCRIPTS = """
Object.defineProperty(navigator, 'webdriver', {get: () => false});
delete navigator.__proto__.webdriver;
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
"""


async def test_gigante_playwright(site_id: str, config: Dict, max_properties: int = 10) -> Dict:
    """
    Testa um site gigante usando Playwright com stealth.
    """
    
    result = {
        "site_id": site_id,
        "name": config["name"],
        "website": config["website"],
        "success": False,
        "properties_found": 0,
        "property_links": [],
        "sample_data": [],
        "working_url": None,
        "errors": [],
        "method_used": "playwright_stealth",
    }
    
    print(f"\n{'='*60}")
    print(f"[PLAYWRIGHT] Testando: {config['name']}")
    print(f"{'='*60}")
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        result["errors"].append("Playwright nao instalado. Execute: pip install playwright && playwright install chromium")
        print(f"   [ERRO] Playwright nao instalado")
        return result
    
    try:
        async with async_playwright() as p:
            # Lançar navegador com stealth
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--window-size=1920,1080',
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
            )
            
            # Injetar stealth scripts
            await context.add_init_script(STEALTH_SCRIPTS)
            
            page = await context.new_page()
            
            # Tentar cada URL de listagem
            for listing_url in config["listing_urls"]:
                try:
                    print(f"\n   [TESTANDO] {listing_url}")
                    
                    await page.goto(listing_url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(3)  # Aguardar JS
                    
                    # Scroll para carregar conteúdo
                    await page.evaluate("""
                        async () => {
                            for (let i = 0; i < 5; i++) {
                                window.scrollBy(0, 500);
                                await new Promise(r => setTimeout(r, 300));
                            }
                        }
                    """)
                    await asyncio.sleep(2)
                    
                    # Verificar se há bloqueio
                    page_text = await page.evaluate("() => document.body.innerText")
                    if 'navegador incompativel' in page_text.lower() or 'access denied' in page_text.lower():
                        print(f"      [WARN] Bloqueio detectado")
                        continue
                    
                    # Procurar links de imóveis
                    html = await page.content()
                    
                    links = set()
                    for pattern in config["link_patterns"]:
                        matches = re.findall(f'href=["\']([^"\']*{pattern}[^"\']*)["\']', html, re.I)
                        for match in matches:
                            full_url = urljoin(config["website"], match)
                            links.add(full_url)
                    
                    # Também tentar seletor CSS
                    try:
                        elements = await page.query_selector_all(config["selectors"]["property_link"])
                        for elem in elements:
                            href = await elem.get_attribute('href')
                            if href:
                                full_url = urljoin(config["website"], href)
                                links.add(full_url)
                    except:
                        pass
                    
                    if links:
                        result["working_url"] = listing_url
                        result["property_links"] = list(links)[:20]
                        result["properties_found"] = len(links)
                        print(f"      [OK] {len(links)} links encontrados!")
                        break
                    else:
                        print(f"      [WARN] Nenhum link encontrado")
                        
                except Exception as e:
                    print(f"      [ERRO] {e}")
                    result["errors"].append(str(e))
            
            # Se encontrou links, extrair dados de alguns imóveis
            if result["property_links"]:
                print(f"\n   [EXTRAINDO] Dados de {min(5, len(result['property_links']))} imoveis...")
                
                for i, prop_url in enumerate(result["property_links"][:5], 1):
                    try:
                        print(f"      {i}. {prop_url[:50]}...")
                        
                        await page.goto(prop_url, wait_until='domcontentloaded', timeout=20000)
                        await asyncio.sleep(2)
                        
                        prop_data = {"url": prop_url}
                        
                        # Extrair título
                        for sel in config["selectors"]["title"].split(", "):
                            try:
                                elem = await page.query_selector(sel)
                                if elem:
                                    text = await elem.inner_text()
                                    if text and len(text.strip()) > 5:
                                        prop_data["title"] = text.strip()[:150]
                                        break
                            except:
                                pass
                        
                        # Extrair preço do HTML
                        html = await page.content()
                        price_match = re.search(r'R\$\s*([\d.,]+)', html)
                        if price_match:
                            prop_data["price"] = price_match.group(0)
                        
                        # Extrair localização
                        loc_match = re.search(r'([A-Za-zÀ-ÿ\s]{3,25})\s*[-/]\s*([A-Z]{2})\b', html)
                        if loc_match:
                            prop_data["location"] = f"{loc_match.group(1).strip()}/{loc_match.group(2)}"
                        
                        if prop_data.get("title"):
                            result["sample_data"].append(prop_data)
                            print(f"         [OK] {prop_data.get('title', 'N/A')[:40]}...")
                        
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        print(f"         [ERRO] {e}")
            
            await browser.close()
            
            result["success"] = result["properties_found"] > 0
            
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   [ERRO FATAL] {e}")
    
    return result


def update_config_file(site_id: str, analysis: Dict):
    """Atualiza o arquivo de configuração com os resultados."""
    
    config_path = f"app/configs/sites/{site_id}.json"
    
    if not os.path.exists(config_path):
        print(f"   [WARN] Config nao encontrada: {config_path}")
        return
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Atualizar com resultados
        config["enabled"] = analysis["success"]
        config["scraping"]["method"] = analysis["method_used"]
        
        if analysis["working_url"]:
            listing_path = analysis["working_url"].replace(analysis["website"], "")
            config["scraping"]["listing_url"] = listing_path or "/"
        
        config["metadata"]["last_tested_at"] = datetime.now().isoformat()
        config["metadata"]["properties_at_discovery"] = analysis["properties_found"]
        config["metadata"]["playwright_tested"] = True
        
        if analysis["sample_data"]:
            config["metadata"]["sample_data"] = analysis["sample_data"][0]
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        status = "[OK]" if analysis["success"] else "[WARN]"
        print(f"   {status} Config atualizada: {config_path}")
        
    except Exception as e:
        print(f"   [ERRO] Erro ao atualizar config: {e}")


async def main():
    """Função principal."""
    
    print("="*70)
    print("TESTE DOS GIGANTES COM PLAYWRIGHT")
    print("="*70)
    print("\nSites a testar:")
    for site_id, config in GIGANTES_CONFIG.items():
        print(f"  - {config['name']} ({config['website']})")
    
    results = []
    
    for site_id, config in GIGANTES_CONFIG.items():
        result = await test_gigante_playwright(site_id, config)
        results.append(result)
        
        # Atualizar config se existe
        update_config_file(site_id, result)
        
        await asyncio.sleep(3)  # Rate limiting
    
    # Relatório final
    print("\n" + "="*70)
    print("RELATORIO FINAL")
    print("="*70)
    
    success_count = sum(1 for r in results if r["success"])
    total_properties = sum(r["properties_found"] for r in results)
    
    print(f"\nSites testados: {len(results)}")
    print(f"Sucesso: {success_count}")
    print(f"Falha: {len(results) - success_count}")
    print(f"Total imóveis encontrados: {total_properties}")
    
    print("\nDetalhes por site:")
    for r in results:
        status = "[OK]" if r["success"] else "[FALHA]"
        print(f"\n  {status} {r['name']}")
        print(f"     Imóveis: {r['properties_found']}")
        print(f"     URL: {r.get('working_url', 'N/A')}")
        
        if r["sample_data"]:
            sample = r["sample_data"][0]
            print(f"     Exemplo: {sample.get('title', 'N/A')[:40]}...")
            if sample.get("price"):
                print(f"     Preço: {sample['price']}")
        
        if r["errors"]:
            print(f"     Erros: {r['errors'][0][:50]}...")
    
    # Salvar relatório
    report = {
        "generated_at": datetime.now().isoformat(),
        "method": "playwright_stealth",
        "total_sites": len(results),
        "successful": success_count,
        "total_properties": total_properties,
        "results": results
    }
    
    with open("gigantes_playwright_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n[REPORT] Relatorio salvo: gigantes_playwright_report.json")
    
    print("\n" + "="*70)
    print("[OK] TESTE CONCLUIDO")
    print("="*70)
    
    if success_count > 0:
        print(f"\n[SUCESSO] {success_count} gigantes funcionando com Playwright!")
        print("   Configs atualizadas com enabled=true")
    else:
        print("\n[WARN] Nenhum gigante funcionou. Possiveis causas:")
        print("   - Protecoes mais agressivas")
        print("   - Estrutura de URLs diferente")
        print("   - Necessita investigacao manual")


if __name__ == "__main__":
    asyncio.run(main())
