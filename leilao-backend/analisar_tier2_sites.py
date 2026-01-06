"""
Script para analisar rapidamente os 30 sites do Tier 2.
Testa APIs Superbid primeiro, depois usa browser para outros.
"""
import asyncio
import httpx
import json
import re
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

# Lista de sites Tier 2
SITES = [
    # LOTE 1 - Superbid/White-label
    {"id": "superbid", "name": "Superbid", "url": "https://www.superbid.net"},
    {"id": "lancenoleilao", "name": "Lance no Leilão", "url": "https://www.lancenoleilao.com.br"},
    {"id": "lut", "name": "LUT", "url": "https://www.lut.com.br"},
    {"id": "bigleilao", "name": "Big Leilão", "url": "https://www.bigleilao.com.br"},
    {"id": "vialeiloes", "name": "Via Leilões", "url": "https://www.vialeiloes.com.br"},
    
    # LOTE 2 - Sites grandes
    {"id": "freitasleiloeiro", "name": "Freitas Leiloeiro", "url": "https://www.freitasleiloeiro.com.br"},
    {"id": "frazaoleiloes", "name": "Frazão Leilões", "url": "https://www.frazaoleiloes.com.br"},
    {"id": "francoleiloes", "name": "Franco Leilões", "url": "https://www.francoleiloes.com.br"},
    {"id": "lancejudicial", "name": "Lance Judicial", "url": "https://www.lancejudicial.com.br"},
    {"id": "leiloesfreire", "name": "Leilões Freire", "url": "https://www.leiloesfreire.com.br"},
    
    # LOTE 3 - Sites médios
    {"id": "bfrcontabil", "name": "BFR Contábil", "url": "https://www.bfrcontabil.com.br"},
    {"id": "kronbergleiloes", "name": "Kronberg Leilões", "url": "https://www.kronbergleiloes.com.br"},
    {"id": "leilomaster", "name": "LeiloMaster", "url": "https://www.leilomaster.com.br"},
    {"id": "nossoleilao", "name": "Nossos Leilão", "url": "https://www.nossoleilao.com.br"},
    {"id": "liderleiloes", "name": "Líder Leilões", "url": "https://www.liderleiloes.com.br"},
    
    # LOTE 4 - Regionais
    {"id": "leiloesjudiciaisrs", "name": "Leilões Judiciais RS", "url": "https://www.leiloesjudiciaisrs.com.br"},
    {"id": "santamarialeiloes", "name": "Santa Maria Leilões", "url": "https://www.santamarialeiloes.com.br"},
    {"id": "mgleiloes-rs", "name": "MG Leilões RS", "url": "https://www.mgleiloes-rs.com.br"},
    {"id": "rochaleiloes", "name": "Rocha Leilões", "url": "https://www.rochaleiloes.com.br"},
    {"id": "rigolonleiloes", "name": "Rigolon Leilões", "url": "https://www.rigolonleiloes.com.br"},
    
    # LOTE 5 - Mais sites
    {"id": "hastalegal", "name": "Hasta Legal", "url": "https://www.hastalegal.com.br"},
    {"id": "hastapublica", "name": "Hasta Pública", "url": "https://www.hastapublica.com.br"},
    {"id": "escritoriodeleiloes", "name": "Escritório de Leilões", "url": "https://www.escritoriodeleiloes.com.br"},
    {"id": "grandesleiloes", "name": "Grandes Leilões", "url": "https://www.grandesleiloes.com.br"},
    {"id": "tonialleiloes", "name": "Tonial Leilões", "url": "https://www.tonialleiloes.com.br"},
    
    # LOTE 6 - Finais
    {"id": "trevisanleiloes", "name": "Trevisan Leilões", "url": "https://www.trevisanleiloes.com.br"},
    {"id": "vidalleiloes", "name": "Vidal Leilões", "url": "https://www.vidalleiloes.com.br"},
    {"id": "webleiloes", "name": "Web Leilões", "url": "https://www.webleiloes.com.br"},
    {"id": "zuccalmaglioleiloes", "name": "Zuccalmaglio Leilões", "url": "https://www.zuccalmaglioleiloes.com.br"},
    {"id": "zagoleiloes", "name": "Zago Leilões", "url": "https://www.zagoleiloes.com.br"},
]

API_BASE = "https://offer-query.superbid.net/offers/"
CONFIG_DIR = Path("app/configs/sites")

async def test_superbid_api(site: Dict, portal_ids: list = None) -> Optional[Dict]:
    """Testa se o site usa API Superbid."""
    if portal_ids is None:
        portal_ids = list(range(1, 20))  # Testa IDs 1-19
    
    headers = {
        'Accept': 'application/json',
        'Origin': site['url'],
        'Referer': site['url'] + '/',
    }
    
    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
        for portal_id in portal_ids:
            try:
                url = f"{API_BASE}?portalId={portal_id}&filter=product.productType.description:imoveis&pageNumber=1&pageSize=10"
                r = await client.get(url, headers=headers)
                if r.status_code == 200:
                    data = r.json()
                    total = data.get('total', 0)
                    if total > 0:
                        return {
                            "method": "api_rest",
                            "portal_id": str(portal_id),
                            "total": total,
                            "api_url": API_BASE,
                        }
            except:
                continue
    return None

async def test_listing_url(site: Dict) -> Dict:
    """Testa URLs comuns de listagem de imóveis."""
    urls_to_test = [
        "/imoveis",
        "/leilao-de-imoveis",
        "/leiloes/imoveis",
        "/categoria/imoveis",
        "/busca?tipo=imoveis",
    ]
    
    results = []
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=False) as client:
        for path in urls_to_test:
            try:
                full_url = site['url'].rstrip('/') + path
                r = await client.get(full_url, headers={'User-Agent': 'Mozilla/5.0'})
                if r.status_code == 200:
                    html = r.text.lower()
                    # Verifica se parece ser página de listagem
                    if any(term in html for term in ['imovel', 'leilao', 'lote', 'lance']):
                        results.append({
                            "url": path,
                            "status": 200,
                            "has_content": True
                        })
            except:
                continue
    
    return results

async def analyze_site(site: Dict) -> Dict:
    """Analisa um site e retorna configuração."""
    print(f"\n{'='*70}")
    print(f"Analisando: {site['name']} ({site['url']})")
    print(f"{'='*70}")
    
    result = {
        "id": site['id'],
        "name": site['name'],
        "website": site['url'],
        "enabled": False,
        "method": None,
        "listing_url": None,
        "selectors": {},
        "pagination": {},
        "notes": []
    }
    
    # 1. Testa API Superbid primeiro
    print("  [1/3] Testando API Superbid...")
    api_result = await test_superbid_api(site)
    if api_result:
        result["enabled"] = True
        result["method"] = "api_rest"
        result["listing_url"] = ""
        result["api"] = {
            "base_url": API_BASE,
            "params": {
                "portalId": api_result["portal_id"],
                "filter": "product.productType.description:imoveis",
                "pageSize": "50"
            },
            "pagination_param": "pageNumber",
            "total_field": "total",
            "items_field": "offers"
        }
        result["notes"].append(f"API Superbid - Portal ID {api_result['portal_id']} - {api_result['total']} imoveis")
        print(f"  [OK] API encontrada! Portal ID: {api_result['portal_id']}, Total: {api_result['total']}")
        return result
    
    # 2. Testa URLs de listagem
    print("  [2/3] Testando URLs de listagem...")
    url_results = await test_listing_url(site)
    if url_results:
        best_url = url_results[0]["url"]
        result["listing_url"] = best_url
        result["method"] = "playwright"  # Default, precisa browser para seletores
        result["notes"].append(f"URL encontrada: {best_url}")
        print(f"  [OK] URL encontrada: {best_url}")
    else:
        result["notes"].append("Nenhuma URL de imoveis encontrada")
        print(f"  [WARN] Nenhuma URL de imoveis encontrada")
    
    # 3. Site precisa análise manual com browser
    result["notes"].append("Requer analise manual com browser para seletores")
    print(f"  [3/3] [WARN] Requer analise manual")
    
    return result

async def main():
    """Função principal."""
    print("="*70)
    print("ANÁLISE RÁPIDA - TIER 2 (30 SITES)")
    print("="*70)
    
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    results = []
    summary = []
    
    for site in SITES:
        try:
            config = await analyze_site(site)
            results.append(config)
            
            # Salva config JSON
            config_file = CONFIG_DIR / f"{site['id']}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Adiciona ao resumo
            status = "OK" if config["enabled"] else "WARN"
            method = config.get("method", "?")
            listing = config.get("listing_url", "?")
            summary.append({
                "site": site['name'],
                "url": listing,
                "method": method,
                "status": status
            })
            
        except Exception as e:
            print(f"  [ERRO] Erro: {e}")
            summary.append({
                "site": site['name'],
                "url": "ERRO",
                "method": "ERRO",
                "status": "ERRO"
            })
    
    # Salva resumo
    summary_file = Path("tier2_analysis_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(SITES),
            "enabled": sum(1 for r in results if r["enabled"]),
            "sites": summary
        }, f, indent=2, ensure_ascii=False)
    
    # Imprime tabela resumo
    print("\n" + "="*70)
    print("RESUMO")
    print("="*70)
    print(f"{'Site':<30} {'URL':<25} {'Metodo':<15} {'Status'}")
    print("-"*70)
    for s in summary:
        print(f"{s['site']:<30} {s['url']:<25} {s['method']:<15} {s['status']}")
    
    print(f"\n[OK] Configs salvos em: {CONFIG_DIR}")
    print(f"[OK] Resumo salvo em: {summary_file}")

if __name__ == "__main__":
    asyncio.run(main())

