# ============================================================
# TAREFA AUTÔNOMA: Investigação Profunda dos 3 Gigantes
# ============================================================
# Para: Cursor Agent
# Modo: AUTÔNOMO
# Tempo estimado: 25-35 minutos
# ============================================================

"""
╔══════════════════════════════════════════════════════════════╗
║  CONTEXTO                                                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  3 gigantes falharam no teste com Playwright:                ║
║                                                              ║
║  1. Mega Leilões    - megaleiloes.com.br                     ║
║  2. Sold Leilões    - sold.com.br                            ║
║  3. Lance Judicial  - lancejudicial.com.br                   ║
║                                                              ║
║  Esta tarefa vai investigar PROFUNDAMENTE cada site:         ║
║                                                              ║
║  • Interceptar requisições de rede (APIs internas)           ║
║  • Testar múltiplos padrões de URL                           ║
║  • Analisar estrutura HTML detalhadamente                    ║
║  • Identificar proteções e como contorná-las                 ║
║  • Buscar endpoints JSON/GraphQL                             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse, parse_qs
import traceback

# ============================================================
# CONFIGURAÇÃO DOS 3 GIGANTES PARA INVESTIGAÇÃO
# ============================================================

SITES_INVESTIGAR = [
    {
        "id": "megaleiloes",
        "name": "Mega Leilões",
        "website": "https://www.megaleiloes.com.br",
        "urls_testar": [
            "/",
            "/buscar",
            "/buscar?tipo=imovel",
            "/buscar?categoria=imovel",
            "/leiloes",
            "/leiloes/imoveis",
            "/imoveis",
            "/catalogo",
            "/leilao",
            "/proximos-leiloes",
            "/api/leiloes",
            "/api/imoveis",
            "/api/buscar",
        ],
        "api_patterns": [
            r"/api/",
            r"/v1/",
            r"/graphql",
            r"\.json",
        ],
        "link_patterns": [
            r"/leilao/\d+",
            r"/imovel/\d+",
            r"/lote/\d+",
            r"/item/\d+",
            r"/detalhe/\d+",
        ],
    },
    {
        "id": "sold",
        "name": "Sold Leilões",
        "website": "https://www.sold.com.br",
        "urls_testar": [
            "/",
            "/leiloes",
            "/leiloes/imoveis",
            "/imoveis",
            "/buscar",
            "/buscar?tipo=imovel",
            "/catalogo",
            "/proximos",
            "/api/leiloes",
            "/api/v1/leiloes",
        ],
        "api_patterns": [
            r"/api/",
            r"/v1/",
            r"\.json",
        ],
        "link_patterns": [
            r"/leilao/",
            r"/imovel/",
            r"/lote/",
            r"/item/",
        ],
    },
    {
        "id": "lancejudicial",
        "name": "Lance Judicial",
        "website": "https://www.lancejudicial.com.br",
        "urls_testar": [
            "/",
            "/leiloes",
            "/leiloes/imoveis",
            "/imoveis",
            "/buscar",
            "/buscar?categoria=imoveis",
            "/catalogo",
            "/bens",
            "/bens/imoveis",
            "/api/leiloes",
        ],
        "api_patterns": [
            r"/api/",
            r"\.json",
        ],
        "link_patterns": [
            r"/leilao/",
            r"/imovel/",
            r"/lote/",
            r"/bem/",
            r"/item/",
        ],
    },
]

# Scripts de stealth avançado
STEALTH_SCRIPTS = """
// Ocultar webdriver
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;

// Plugins falsos
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {name: 'Native Client', filename: 'internal-nacl-plugin'},
        ];
        plugins.item = (i) => plugins[i];
        plugins.namedItem = (n) => plugins.find(p => p.name === n);
        plugins.refresh = () => {};
        return plugins;
    }
});

// Languages
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});

// Chrome object
window.chrome = {
    runtime: {id: undefined},
    loadTimes: function() { return {}; },
    csi: function() { return {}; },
    app: {isInstalled: false}
};

// Platform
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});

// Permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// WebGL
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.apply(this, arguments);
};
"""


async def investigar_site(site: Dict) -> Dict:
    """
    Investigação profunda de um site.
    
    Técnicas usadas:
    1. Interceptação de requisições de rede
    2. Análise de múltiplas URLs
    3. Busca por APIs internas
    4. Análise detalhada do HTML
    """
    
    result = {
        "id": site["id"],
        "name": site["name"],
        "website": site["website"],
        "investigation_time": datetime.now().isoformat(),
        "success": False,
        "working_url": None,
        "properties_found": 0,
        "property_links": [],
        "apis_discovered": [],
        "network_requests": [],
        "html_analysis": {},
        "recommendations": [],
        "errors": [],
    }
    
    print(f"\n{'='*70}")
    print(f"[INVESTIGACAO] {site['name']}")
    print(f"{'='*70}")
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        result["errors"].append("Playwright não instalado")
        return result
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--window-size=1920,1080',
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
                extra_http_headers={
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                }
            )
            
            await context.add_init_script(STEALTH_SCRIPTS)
            
            page = await context.new_page()
            
            # ========================================
            # FASE 1: Interceptar requisições de rede
            # ========================================
            print(f"\n[FASE 1] Interceptando requisicoes de rede...")
            
            captured_requests: List[Dict] = []
            captured_apis: Set[str] = set()
            
            async def handle_request(request):
                url = request.url
                # Capturar requisições interessantes
                if any(p in url for p in ['/api/', '.json', '/v1/', '/graphql', 'leilao', 'imovel', 'lote']):
                    captured_requests.append({
                        "url": url,
                        "method": request.method,
                        "resource_type": request.resource_type,
                    })
                    
                    # Identificar APIs
                    for pattern in site["api_patterns"]:
                        if re.search(pattern, url):
                            captured_apis.add(url)
            
            async def handle_response(response):
                url = response.url
                content_type = response.headers.get('content-type', '')
                
                # Capturar respostas JSON
                if 'application/json' in content_type:
                    try:
                        body = await response.text()
                        if len(body) > 100:  # Ignorar respostas pequenas
                            captured_apis.add(url)
                            print(f"      [API] JSON: {url[:70]}...")
                    except:
                        pass
            
            page.on("request", handle_request)
            page.on("response", handle_response)
            
            # Acessar página principal
            print(f"   Acessando: {site['website']}")
            try:
                await page.goto(site["website"], wait_until='networkidle', timeout=45000)
                await asyncio.sleep(3)
            except Exception as e:
                print(f"   [WARN] Timeout na pagina principal: {e}")
            
            # Fazer scroll para disparar lazy loading
            await page.evaluate("""
                async () => {
                    for (let i = 0; i < 10; i++) {
                        window.scrollBy(0, 300);
                        await new Promise(r => setTimeout(r, 200));
                    }
                    window.scrollTo(0, 0);
                }
            """)
            await asyncio.sleep(2)
            
            result["network_requests"] = captured_requests[:20]
            result["apis_discovered"] = list(captured_apis)[:10]
            
            print(f"   [REQUISICOES] Capturadas: {len(captured_requests)}")
            print(f"   [APIS] Descobertas: {len(captured_apis)}")
            
            for api in list(captured_apis)[:5]:
                print(f"      • {api[:70]}...")
            
            # ========================================
            # FASE 2: Testar múltiplas URLs
            # ========================================
            print(f"\n[FASE 2] Testando URLs de listagem...")
            
            best_url = None
            best_count = 0
            best_links = []
            
            for url_path in site["urls_testar"]:
                try:
                    test_url = site["website"].rstrip('/') + url_path
                    print(f"   [TESTANDO] {test_url}")
                    
                    response = await page.goto(test_url, wait_until='domcontentloaded', timeout=20000)
                    
                    if response and response.status == 200:
                        await asyncio.sleep(2)
                        
                        # Scroll
                        await page.evaluate("window.scrollBy(0, 1000)")
                        await asyncio.sleep(1)
                        
                        html = await page.content()
                        
                        # Procurar links de imóveis
                        links = set()
                        for pattern in site["link_patterns"]:
                            matches = re.findall(f'href=["\']([^"\']*{pattern}[^"\']*)["\']', html, re.I)
                            for match in matches:
                                full_url = urljoin(site["website"], match)
                                links.add(full_url)
                        
                        if len(links) > best_count:
                            best_count = len(links)
                            best_url = test_url
                            best_links = list(links)
                            print(f"      [OK] {len(links)} links encontrados!")
                        elif len(links) == 0:
                            print(f"      [WARN] 0 links")
                    else:
                        status = response.status if response else "N/A"
                        print(f"      [ERRO] HTTP {status}")
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"      [ERRO] {str(e)[:50]}")
            
            if best_url:
                result["working_url"] = best_url
                result["properties_found"] = best_count
                result["property_links"] = best_links[:30]
                print(f"\n   [MELHOR URL] {best_url} ({best_count} links)")
            
            # ========================================
            # FASE 3: Análise detalhada do HTML
            # ========================================
            print(f"\n[FASE 3] Analise do HTML...")
            
            # Voltar para melhor URL ou página principal
            target_url = best_url or site["website"]
            await page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
            
            html = await page.content()
            
            # Análise de estrutura
            html_analysis = {
                "total_links": len(re.findall(r'<a\s', html, re.I)),
                "total_divs": len(re.findall(r'<div\s', html, re.I)),
                "has_react": '__NEXT_DATA__' in html or 'react' in html.lower(),
                "has_vue": 'vue' in html.lower() or '__VUE__' in html,
                "has_angular": 'ng-app' in html or 'angular' in html.lower(),
                "has_jquery": 'jquery' in html.lower(),
                "has_cloudflare": 'cf-ray' in html.lower() or 'cloudflare' in html.lower(),
                "frameworks_detected": [],
                "potential_selectors": [],
            }
            
            # Detectar frameworks
            if html_analysis["has_react"]:
                html_analysis["frameworks_detected"].append("React/Next.js")
            if html_analysis["has_vue"]:
                html_analysis["frameworks_detected"].append("Vue.js")
            if html_analysis["has_angular"]:
                html_analysis["frameworks_detected"].append("Angular")
            
            # Procurar seletores potenciais
            potential_classes = re.findall(r'class=["\']([^"\']*(?:card|item|lote|leilao|imovel|property|listing)[^"\']*)["\']', html, re.I)
            html_analysis["potential_selectors"] = list(set(potential_classes))[:10]
            
            result["html_analysis"] = html_analysis
            
            print(f"   Links totais: {html_analysis['total_links']}")
            print(f"   Frameworks: {html_analysis['frameworks_detected'] or 'Nenhum detectado'}")
            print(f"   Seletores potenciais: {len(html_analysis['potential_selectors'])}")
            
            for sel in html_analysis["potential_selectors"][:5]:
                print(f"      • .{sel}")
            
            # ========================================
            # FASE 4: Testar APIs descobertas
            # ========================================
            if captured_apis:
                print(f"\n[FASE 4] Testando APIs descobertas...")
                
                for api_url in list(captured_apis)[:5]:
                    try:
                        print(f"   [TESTANDO API] {api_url[:60]}...")
                        response = await page.goto(api_url, wait_until='domcontentloaded', timeout=10000)
                        
                        if response and response.status == 200:
                            content = await page.content()
                            
                            # Verificar se é JSON
                            if content.strip().startswith('{') or content.strip().startswith('['):
                                # Tentar parsear
                                try:
                                    # Extrair JSON do HTML (pode estar dentro de <pre>)
                                    json_match = re.search(r'[\[\{].*[\]\}]', content, re.S)
                                    if json_match:
                                        data = json.loads(json_match.group())
                                        if isinstance(data, list):
                                            print(f"      [OK] Array JSON com {len(data)} itens!")
                                            result["recommendations"].append(f"API JSON encontrada: {api_url}")
                                        elif isinstance(data, dict):
                                            keys = list(data.keys())[:5]
                                            print(f"      [OK] Objeto JSON: {keys}")
                                except:
                                    pass
                    except:
                        pass
            
            # ========================================
            # FASE 5: Gerar recomendações
            # ========================================
            print(f"\n[FASE 5] Gerando recomendacoes...")
            
            if result["properties_found"] > 0:
                result["success"] = True
                result["recommendations"].append(f"URL funcional encontrada: {result['working_url']}")
                result["recommendations"].append(f"Usar playwright_stealth com esta URL")
            else:
                # Analisar por que falhou
                if html_analysis["has_react"] or html_analysis["has_vue"]:
                    result["recommendations"].append("Site usa SPA (React/Vue) - aguardar mais tempo para renderização")
                    result["recommendations"].append("Tentar esperar por seletores específicos antes de extrair")
                
                if captured_apis:
                    result["recommendations"].append("APIs internas descobertas - tentar acessar diretamente")
                    result["recommendations"].append(f"APIs: {list(captured_apis)[:3]}")
                
                if html_analysis["potential_selectors"]:
                    result["recommendations"].append(f"Seletores potenciais: {html_analysis['potential_selectors'][:3]}")
                
                if not result["recommendations"]:
                    result["recommendations"].append("Site pode requerer autenticação ou ter proteções mais complexas")
                    result["recommendations"].append("Considerar análise manual no navegador")
            
            await browser.close()
            
    except Exception as e:
        result["errors"].append(str(e))
        result["errors"].append(traceback.format_exc())
        print(f"   [ERRO] {e}")
    
    # Resumo
    print(f"\n   {'='*50}")
    status = "[SUCESSO]" if result["success"] else "[PRECISA INVESTIGACAO]"
    print(f"   {status}")
    print(f"   Imóveis encontrados: {result['properties_found']}")
    print(f"   APIs descobertas: {len(result['apis_discovered'])}")
    print(f"   Recomendações: {len(result['recommendations'])}")
    
    return result


def generate_improved_config(investigation: Dict) -> Optional[Dict]:
    """Gera config melhorada baseada na investigação."""
    
    if not investigation["success"]:
        return None
    
    config = {
        "id": investigation["id"],
        "name": investigation["name"],
        "website": investigation["website"],
        "enabled": True,
        
        "scraping": {
            "method": "playwright_stealth",
            "listing_url": investigation["working_url"].replace(investigation["website"], "") or "/",
            "rate_limit_seconds": 3.0,
            "max_pages": 50,
            "timeout_seconds": 45,
            "wait_for_selector": None,  # Preencher se encontrado
        },
        
        "selectors": {
            "property_card": ", ".join([f".{s}" for s in investigation["html_analysis"].get("potential_selectors", [])[:3]]) or ".card, .item",
            "property_link": "a[href*='/leilao/'], a[href*='/imovel/'], a[href*='/lote/']",
            "title": "h1, h2, .titulo, .title",
            "price": ".valor, .preco, .lance, [class*='price']",
            "location": ".endereco, .local, .cidade",
            "image": "img",
            "pagination": {
                "type": "query",
                "param": "page"
            }
        },
        
        "apis_discovered": investigation["apis_discovered"][:5],
        
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "investigation_date": investigation["investigation_time"],
            "properties_at_discovery": investigation["properties_found"],
            "frameworks": investigation["html_analysis"].get("frameworks_detected", []),
            "recommendations": investigation["recommendations"],
        }
    }
    
    return config


async def main():
    """Função principal."""
    
    print("="*70)
    print("INVESTIGACAO PROFUNDA DOS 3 GIGANTES")
    print("="*70)
    print("\nSites a investigar:")
    for site in SITES_INVESTIGAR:
        print(f"  - {site['name']} ({site['website']})")
    print()
    
    results = []
    
    for site in SITES_INVESTIGAR:
        investigation = await investigar_site(site)
        results.append(investigation)
        
        # Salvar config melhorada se sucesso
        if investigation["success"]:
            config = generate_improved_config(investigation)
            if config:
                config_path = f"app/configs/sites/{investigation['id']}.json"
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                print(f"\n   [CONFIG] Atualizada: {config_path}")
        
        await asyncio.sleep(5)  # Rate limiting entre sites
    
    # Relatório final
    print("\n" + "="*70)
    print("RELATORIO FINAL DA INVESTIGACAO")
    print("="*70)
    
    success_count = sum(1 for r in results if r["success"])
    total_properties = sum(r["properties_found"] for r in results)
    total_apis = sum(len(r["apis_discovered"]) for r in results)
    
    print(f"\nSites investigados: {len(results)}")
    print(f"Sucesso: {success_count}")
    print(f"Precisam mais trabalho: {len(results) - success_count}")
    print(f"Total imóveis encontrados: {total_properties}")
    print(f"Total APIs descobertas: {total_apis}")
    
    print("\n" + "-"*70)
    print("DETALHES POR SITE:")
    print("-"*70)
    
    for r in results:
        status = "[OK]" if r["success"] else "[FALHA]"
        print(f"\n{status} {r['name']}")
        print(f"   URL: {r.get('working_url', 'N/A')}")
        print(f"   Imóveis: {r['properties_found']}")
        print(f"   APIs: {len(r['apis_discovered'])}")
        
        if r["apis_discovered"]:
            print(f"   APIs descobertas:")
            for api in r["apis_discovered"][:3]:
                print(f"      • {api[:60]}...")
        
        print(f"   Frameworks: {r['html_analysis'].get('frameworks_detected', [])}")
        
        if r["recommendations"]:
            print(f"   Recomendações:")
            for rec in r["recommendations"][:3]:
                print(f"      • {rec[:60]}...")
        
        if r["html_analysis"].get("potential_selectors"):
            print(f"   Seletores potenciais:")
            for sel in r["html_analysis"]["potential_selectors"][:3]:
                print(f"      • .{sel}")
    
    # Salvar relatório
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_sites": len(results),
        "successful": success_count,
        "total_properties": total_properties,
        "total_apis_discovered": total_apis,
        "investigations": results
    }
    
    with open("investigacao_profunda_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n[REPORT] Relatorio salvo: investigacao_profunda_report.json")
    
    print("\n" + "="*70)
    print("[OK] INVESTIGACAO CONCLUIDA")
    print("="*70)
    
    # Resumo de próximos passos
    print("\n[PROXIMOS PASSOS] Recomendacoes:")
    
    for r in results:
        print(f"\n{r['name']}:")
        if r["success"]:
            print(f"   [OK] Pronto para uso! Config atualizada.")
        else:
            if r["apis_discovered"]:
                print(f"   • Tentar acessar APIs diretamente: {r['apis_discovered'][0][:50]}...")
            if r["html_analysis"].get("frameworks_detected"):
                print(f"   • Site usa {r['html_analysis']['frameworks_detected']} - aumentar tempo de espera")
            if r["html_analysis"].get("potential_selectors"):
                print(f"   • Tentar seletores: .{r['html_analysis']['potential_selectors'][0]}")
            print(f"   • Considerar análise manual no navegador DevTools")


if __name__ == "__main__":
    asyncio.run(main())
