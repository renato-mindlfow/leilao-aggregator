# ============================================================
# TAREFA AUTÔNOMA: Análise dos 5 GIGANTES
# ============================================================
# Para: Cursor Agent
# Modo: AUTÔNOMO
# Tempo estimado: 20-30 minutos
# ============================================================

"""
╔══════════════════════════════════════════════════════════════╗
║  CONTEXTO                                                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  A tarefa anterior configurou 4 sites MÉDIOS que já          ║
║  tinham seletores identificados.                             ║
║                                                              ║
║  Agora precisamos analisar os 5 GIGANTES do mercado:         ║
║                                                              ║
║  1. Mega Leilões    - megaleiloes.com.br    (~1500 imóveis)  ║
║  2. Sodré Santoro   - sodresantoro.com.br   (~1200 imóveis)  ║
║  3. Portal Zuk      - portalzuk.com.br      (~2000 imóveis)  ║
║  4. Sold            - sold.com.br           (~800 imóveis)   ║
║  5. Lance Judicial  - lancejudicial.com.br  (~500 imóveis)   ║
║                                                              ║
║  Estes sites representam ~70% do mercado de leilões.         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re
from urllib.parse import urljoin, urlparse

# ============================================================
# SITES GIGANTES PARA ANÁLISE
# ============================================================

GIGANTES = [
    {
        "id": "megaleiloes",
        "name": "Mega Leilões",
        "website": "https://www.megaleiloes.com.br",
        "listing_urls": [
            "/",
            "/leilao",
            "/leiloes",
            "/imoveis",
            "/busca",
        ],
        "link_patterns": ["/imovel/", "/lote/", "/item/", "/leilao/"],
        "expected_properties": 1500,
    },
    {
        "id": "sodresantoro",
        "name": "Sodré Santoro",
        "website": "https://www.sodresantoro.com.br",
        "listing_urls": [
            "/",
            "/imoveis",
            "/leiloes",
            "/busca",
            "/catalogo",
        ],
        "link_patterns": ["/imovel/", "/lote/", "/detalhe/", "/bem/"],
        "expected_properties": 1200,
    },
    {
        "id": "portalzuk",
        "name": "Portal Zukerman",
        "website": "https://www.portalzuk.com.br",
        "listing_urls": [
            "/",
            "/imovel",
            "/imoveis",
            "/leilao",
            "/busca",
        ],
        "link_patterns": ["/imovel/"],
        "expected_properties": 2000,
    },
    {
        "id": "sold",
        "name": "Sold Leilões",
        "website": "https://www.sold.com.br",
        "listing_urls": [
            "/",
            "/imoveis",
            "/leiloes",
            "/busca",
        ],
        "link_patterns": ["/imovel/", "/lote/", "/item/"],
        "expected_properties": 800,
    },
    {
        "id": "lancejudicial",
        "name": "Lance Judicial",
        "website": "https://www.lancejudicial.com.br",
        "listing_urls": [
            "/",
            "/imoveis",
            "/leiloes",
            "/busca",
        ],
        "link_patterns": ["/imovel/", "/lote/", "/leilao/"],
        "expected_properties": 500,
    },
]

# Headers para simular navegador real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


async def analyze_gigante(client: httpx.AsyncClient, site: Dict) -> Dict:
    """
    Analisa profundamente um site gigante.
    
    Tenta múltiplas URLs e identifica a melhor estrutura.
    """
    
    result = {
        "id": site["id"],
        "name": site["name"],
        "website": site["website"],
        "status": "unknown",
        "working_url": None,
        "requires_js": False,
        "has_cloudflare": False,
        "properties_found": 0,
        "property_links": [],
        "selectors": {},
        "sample_data": {},
        "errors": [],
        "analysis_notes": [],
    }
    
    print(f"\n{'='*60}")
    print(f"[ANALISANDO] {site['name']}")
    print(f"   URL: {site['website']}")
    print(f"{'='*60}")
    
    # 1. Testar conectividade e detectar proteções
    try:
        response = await client.get(site["website"], follow_redirects=True)
        
        # Detectar Cloudflare
        if any(h in response.headers for h in ['cf-ray', 'cf-cache-status']):
            result["has_cloudflare"] = True
            result["analysis_notes"].append("[WARN] Cloudflare detectado")
            print(f"   [WARN] Cloudflare detectado")
        
        # Verificar se precisa JS
        html = response.text
        if any(x in html for x in ['__NEXT_DATA__', 'React', 'Vue', 'Angular', 'window.__INITIAL_STATE__']):
            result["requires_js"] = True
            result["analysis_notes"].append("[WARN] Site usa JavaScript framework")
            print(f"   [WARN] Requer JavaScript")
        
        if response.status_code != 200:
            result["errors"].append(f"HTTP {response.status_code}")
            print(f"   [ERRO] HTTP {response.status_code}")
            
    except Exception as e:
        result["errors"].append(f"Erro de conexão: {str(e)}")
        print(f"   [ERRO] Erro: {e}")
        return result
    
    # 2. Tentar encontrar página de listagem com imóveis
    best_url = None
    best_count = 0
    best_links = []
    
    for listing_path in site["listing_urls"]:
        try:
            url = site["website"].rstrip('/') + listing_path
            print(f"   [TESTANDO] {url}")
            
            response = await client.get(url, follow_redirects=True)
            
            if response.status_code != 200:
                continue
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Procurar links de imóveis
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                for pattern in site["link_patterns"]:
                    if pattern in href.lower():
                        full_url = urljoin(site["website"], href)
                        links.add(full_url)
                        break
            
            if len(links) > best_count:
                best_count = len(links)
                best_url = url
                best_links = list(links)
                print(f"      [OK] {len(links)} links encontrados!")
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"      [ERRO] {e}")
    
    if best_url:
        result["working_url"] = best_url
        result["properties_found"] = best_count
        result["property_links"] = best_links[:20]  # Guardar até 20 para teste
        result["status"] = "active"
        print(f"\n   [OK] Melhor URL: {best_url} ({best_count} imoveis)")
    else:
        result["status"] = "needs_investigation"
        result["analysis_notes"].append("Nenhuma página de listagem encontrada")
        print(f"\n   [WARN] Nenhum imovel encontrado - pode precisar de Playwright")
        return result
    
    # 3. Analisar página de listagem para identificar seletores
    try:
        response = await client.get(best_url, follow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tentar identificar seletores de cards
        card_candidates = [
            '.card', '.item', '.property', '.imovel', '.lote', '.leilao',
            'article', '.listing-item', '[class*="card"]', '[class*="item"]',
            '.resultado', '.box', '.produto'
        ]
        
        for selector in card_candidates:
            cards = soup.select(selector)
            if cards and len(cards) >= 3:  # Pelo menos 3 cards
                result["selectors"]["card"] = selector
                print(f"   [CARD] Selector: {selector} ({len(cards)} encontrados)")
                break
        
        # Identificar seletor de link
        result["selectors"]["link"] = f"a[href*='{site['link_patterns'][0]}']"
        
    except Exception as e:
        result["errors"].append(f"Erro ao analisar listagem: {str(e)}")
    
    # 4. Analisar uma página de imóvel para identificar mais seletores
    if best_links:
        try:
            sample_url = best_links[0]
            print(f"\n   [IMOVEL] Analisando pagina: {sample_url[:60]}...")
            
            await asyncio.sleep(1)
            response = await client.get(sample_url, follow_redirects=True)
            
            if response.status_code == 200:
                prop_soup = BeautifulSoup(response.text, 'html.parser')
                prop_html = response.text
                
                # Título
                for sel in ['h1', 'h2.title', '.titulo', '.nome', '[class*="title"]']:
                    elem = prop_soup.select_one(sel)
                    if elem and elem.get_text().strip():
                        text = elem.get_text().strip()
                        if len(text) > 10 and len(text) < 300:
                            result["selectors"]["title"] = sel
                            result["sample_data"]["title"] = text[:100]
                            print(f"   [TITULO] {text[:50]}...")
                            break
                
                # Preço
                price_match = re.search(r'R\$\s*([\d.,]+)', prop_html)
                if price_match:
                    result["sample_data"]["price"] = price_match.group(0)
                    result["selectors"]["price"] = "regex:R$"
                    print(f"   [PRECO] {price_match.group(0)}")
                
                # Localização
                loc_match = re.search(r'([A-Za-zÀ-ÿ\s]{3,30})\s*[-/]\s*([A-Z]{2})\b', prop_html)
                if loc_match:
                    result["sample_data"]["location"] = f"{loc_match.group(1).strip()}/{loc_match.group(2)}"
                    print(f"   [LOCAL] {result['sample_data']['location']}")
                
                # Imagem
                for img in prop_soup.select('img')[:20]:
                    src = img.get('src') or img.get('data-src', '')
                    if src and not any(x in src.lower() for x in ['logo', 'icon', 'avatar', 'placeholder']):
                        result["sample_data"]["image"] = urljoin(sample_url, src)
                        result["selectors"]["image"] = "img"
                        break
                
                result["sample_data"]["url"] = sample_url
                
        except Exception as e:
            result["errors"].append(f"Erro ao analisar imóvel: {str(e)}")
    
    # 5. Determinar método recomendado
    if result["requires_js"] or result["has_cloudflare"]:
        if result["has_cloudflare"] and result["requires_js"]:
            result["recommended_method"] = "playwright_stealth"
        elif result["requires_js"]:
            result["recommended_method"] = "playwright_simple"
        else:
            result["recommended_method"] = "httpx_stealth"
    else:
        result["recommended_method"] = "httpx_simple" if result["properties_found"] > 0 else "playwright_stealth"
    
    print(f"\n   [METODO] Recomendado: {result['recommended_method']}")
    
    return result


def generate_config(analysis: Dict) -> Dict:
    """Gera configuração JSON baseada na análise."""
    
    config = {
        "id": analysis["id"],
        "name": analysis["name"],
        "website": analysis["website"],
        "enabled": analysis["status"] == "active",
        
        "scraping": {
            "method": analysis.get("recommended_method", "httpx_stealth"),
            "listing_url": (analysis.get("working_url") or "").replace(analysis["website"], "") or "/",
            "rate_limit_seconds": 2.5 if analysis.get("has_cloudflare") else 2.0,
            "max_pages": 100,
            "timeout_seconds": 45 if analysis.get("requires_js") else 30
        },
        
        "selectors": {
            "property_card": analysis.get("selectors", {}).get("card", ".card, .item, article"),
            "property_link": analysis.get("selectors", {}).get("link", "a[href*='/imovel/']"),
            "title": analysis.get("selectors", {}).get("title", "h1, h2"),
            "price": ".valor, .preco, .lance, [class*='price'], [class*='valor']",
            "location": ".endereco, .local, .cidade, [class*='location']",
            "area": ".area, [class*='m2'], [class*='area']",
            "image": analysis.get("selectors", {}).get("image", "img"),
            "pagination": {
                "type": "query",
                "param": "page",
                "next_selector": ".pagination .next, a[rel='next'], .next"
            }
        },
        
        "schedule": {
            "frequency": "daily",
            "preferred_time": "03:00",
            "timezone": "America/Sao_Paulo"
        },
        
        "health": {
            "min_properties_expected": max(50, analysis.get("properties_found", 0) // 2),
            "max_consecutive_failures": 3,
            "alert_on_decrease_percent": 30
        },
        
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "tier": 1,
            "has_cloudflare": analysis.get("has_cloudflare", False),
            "requires_js": analysis.get("requires_js", False),
            "properties_at_discovery": analysis.get("properties_found", 0),
            "sample_data": analysis.get("sample_data", {}),
            "analysis_notes": analysis.get("analysis_notes", [])
        }
    }
    
    return config


async def main():
    """Função principal."""
    
    print("="*70)
    print("ANALISE DOS 5 GIGANTES DO MERCADO DE LEILOES")
    print("="*70)
    print("\nSites a analisar:")
    for i, site in enumerate(GIGANTES, 1):
        print(f"  {i}. {site['name']} - {site['website']}")
    print()
    
    results = []
    configs = []
    
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        verify=False,
        headers=HEADERS
    ) as client:
        
        for site in GIGANTES:
            analysis = await analyze_gigante(client, site)
            results.append(analysis)
            
            # Gerar config
            config = generate_config(analysis)
            configs.append(config)
            
            await asyncio.sleep(2)  # Rate limiting entre sites
    
    # Salvar configs
    print("\n" + "="*70)
    print("SALVANDO CONFIGURACOES")
    print("="*70)
    
    config_dir = "app/configs/sites"
    os.makedirs(config_dir, exist_ok=True)
    
    for config in configs:
        filepath = os.path.join(config_dir, f"{config['id']}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        status = "[OK]" if config["enabled"] else "[WARN]"
        print(f"  {status} {filepath}")
    
    # Salvar relatório de análise
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_sites": len(results),
        "active": sum(1 for r in results if r["status"] == "active"),
        "needs_investigation": sum(1 for r in results if r["status"] == "needs_investigation"),
        "total_properties_found": sum(r["properties_found"] for r in results),
        "results": results
    }
    
    with open("gigantes_analysis_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n  [REPORT] gigantes_analysis_report.json")
    
    # Relatório final
    print("\n" + "="*70)
    print("RELATORIO FINAL")
    print("="*70)
    
    print(f"\nSites analisados: {len(results)}")
    print(f"Ativos (httpx): {sum(1 for r in results if r['status'] == 'active' and 'httpx' in r.get('recommended_method', ''))}")
    print(f"Requerem Playwright: {sum(1 for r in results if 'playwright' in r.get('recommended_method', ''))}")
    print(f"Precisam investigação: {sum(1 for r in results if r['status'] == 'needs_investigation')}")
    print(f"Total imóveis encontrados: {sum(r['properties_found'] for r in results)}")
    
    print("\nDetalhes por site:")
    for r in results:
        status_icon = "[OK]" if r["status"] == "active" else "[WARN]"
        cf_icon = "[CF]" if r.get("has_cloudflare") else ""
        js_icon = "[JS]" if r.get("requires_js") else ""
        
        print(f"\n  {status_icon} {r['name']} {cf_icon}{js_icon}")
        print(f"     URL: {r.get('working_url', 'N/A')}")
        print(f"     Imóveis: {r['properties_found']}")
        print(f"     Método: {r.get('recommended_method', 'N/A')}")
        
        if r.get("sample_data"):
            if r["sample_data"].get("title"):
                print(f"     Título: {r['sample_data']['title'][:40]}...")
            if r["sample_data"].get("price"):
                print(f"     Preço: {r['sample_data']['price']}")
    
    print("\n" + "="*70)
    print("[OK] ANALISE CONCLUIDA")
    print("="*70)
    print("\nPróximos passos:")
    print("  1. Revisar configs em app/configs/sites/")
    print("  2. Sites com Cloudflare/JS precisam de Playwright")
    print("  3. Testar scrapers: python -m app.services.scraper_orchestrator --sites megaleiloes,sold")
    print("  4. Ajustar seletores conforme necessário")


if __name__ == "__main__":
    asyncio.run(main())
