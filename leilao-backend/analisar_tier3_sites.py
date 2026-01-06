"""
Análise rápida de sites Tier 3 para configurar leiloeiros adicionais.
Executa análise autônoma de 30 sites e cria configs JSON.
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

# Lista de sites para analisar
LOTE_A = [
    {"url": "https://www.leiloesdodf.com.br", "name": "Leilões do DF"},
    {"url": "https://www.leiloesdors.com.br", "name": "Leilões do RS"},
    {"url": "https://www.leiloessc.com.br", "name": "Leilões SC"},
    {"url": "https://www.leiloespr.com.br", "name": "Leilões PR"},
    {"url": "https://www.leiloesbahia.com.br", "name": "Leilões Bahia"},
    {"url": "https://www.leiloesmg.com.br", "name": "Leilões MG"},
    {"url": "https://www.leiloesrj.com.br", "name": "Leilões RJ"},
    {"url": "https://www.leiloessp.com.br", "name": "Leilões SP"},
    {"url": "https://www.leiloesgo.com.br", "name": "Leilões GO"},
    {"url": "https://www.leiloespe.com.br", "name": "Leilões PE"},
]

LOTE_B = [
    {"url": "https://www.zukerman.com.br", "name": "Zukerman"},
    {"url": "https://www.pestanaleiloes.com.br", "name": "Pestana Leilões"},
    {"url": "https://www.canalleiloes.com.br", "name": "Canal Leilões"},
    {"url": "https://www.leilomaster.com.br", "name": "Leilo Master"},
    {"url": "https://www.leilaoimovel.com.br", "name": "Leilão Imóvel"},
    {"url": "https://www.superleiloes.com.br", "name": "Super Leilões"},
    {"url": "https://www.propleiloes.com.br", "name": "Prop Leilões"},
    {"url": "https://www.alfredimoveis.com.br", "name": "Alfred Imóveis"},
    {"url": "https://www.norteleiloes.com.br", "name": "Norte Leilões"},
]

LOTE_C = [
    # Sites adicionais conhecidos
    {"url": "https://www.leiloesonline.com.br", "name": "Leilões Online"},
    {"url": "https://www.leiloesbrasil.com.br", "name": "Leilões Brasil"},
    {"url": "https://www.leiloeiro.com.br", "name": "Leiloeiro"},
    {"url": "https://www.leiloesjudiciais.com.br", "name": "Leilões Judiciais"},
    {"url": "https://www.leiloesnacionais.com.br", "name": "Leilões Nacionais"},
    {"url": "https://www.leiloesexpress.com.br", "name": "Leilões Express"},
    {"url": "https://www.leiloesrapidos.com.br", "name": "Leilões Rápidos"},
    {"url": "https://www.leiloesfacil.com.br", "name": "Leilões Fácil"},
    {"url": "https://www.leiloesdigital.com.br", "name": "Leilões Digital"},
    {"url": "https://www.leiloesvirtual.com.br", "name": "Leilões Virtual"},
]

CONFIG_DIR = Path("app/configs/sites")
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

results = []

def generate_id(name: str) -> str:
    """Gera ID a partir do nome."""
    return re.sub(r'[^a-z0-9]', '', name.lower().replace(' ', ''))

def create_config(site: Dict, has_properties: bool, count: int = 0, 
                  listing_url: str = "", selectors: Dict = None,
                  pagination: Dict = None, method: str = "playwright",
                  reason: str = "") -> Dict:
    """Cria estrutura de config."""
    site_id = generate_id(site["name"])
    
    if not has_properties:
        return {
            "id": site_id,
            "name": site["name"],
            "website": site["url"],
            "enabled": False,
            "reason": reason or "Sem imóveis encontrados"
        }
    
    config = {
        "id": site_id,
        "name": site["name"],
        "website": site["url"],
        "enabled": True,
        "method": method,
        "listing_url": listing_url,
        "selectors": selectors or {
            "card": "[class*='card'], [class*='item'], article, .property",
            "link": "a[href*='/leilao/'], a[href*='/imovel/'], a[href*='/imoveis/']"
        },
        "pagination": pagination or {
            "type": "query_param",
            "param": "page"
        },
        "estimated_count": count,
        "last_checked": datetime.now().strftime("%Y-%m-%d"),
        "notes": f"Config criado automaticamente em {datetime.now().strftime('%Y-%m-%d')}"
    }
    
    return config

async def analyze_site_browser(site: Dict) -> Dict:
    """Analisa site usando navegador MCP."""
    print(f"\n{'='*60}")
    print(f"Analisando: {site['name']} - {site['url']}")
    print(f"{'='*60}")
    
    result = {
        "site": site,
        "has_properties": False,
        "count": 0,
        "listing_url": "",
        "selectors": {},
        "pagination": {},
        "method": "playwright",
        "reason": "",
        "status": "error"
    }
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(site["url"])
            
            if response.status_code != 200:
                result["reason"] = f"HTTP {response.status_code}"
                result["status"] = "failed"
                return result
            
            html = response.text.lower()
            
            # Procurar por palavras-chave relacionadas a imóveis
            imovel_keywords = [
                "imóvel", "imovel", "casa", "apartamento", "terreno",
                "leilão", "leilao", "lote", "propriedade"
            ]
            
            has_imovel_content = any(keyword in html for keyword in imovel_keywords)
            
            # Procurar por links de imóveis
            imovel_urls = [
                "/imoveis", "/imovel", "/leiloes/imoveis", "/leilao/imoveis",
                "/imoveis/", "/casas", "/apartamentos"
            ]
            
            found_urls = [url for url in imovel_urls if url in html]
            
            if not has_imovel_content and not found_urls:
                result["reason"] = "Sem conteúdo de imóveis detectado"
                result["status"] = "no_properties"
                return result
            
            # Tentar encontrar URL de listagem
            listing_url = found_urls[0] if found_urls else "/imoveis"
            
            # Tentar acessar URL de listagem
            listing_full_url = urljoin(site["url"], listing_url)
            try:
                listing_response = await client.get(listing_full_url, timeout=10.0)
                if listing_response.status_code == 200:
                    listing_html = listing_response.text.lower()
                    
                    # Contar cards/itens (estimativa)
                    card_patterns = [
                        r'class="[^"]*card[^"]*"',
                        r'class="[^"]*item[^"]*"',
                        r'<article',
                        r'class="[^"]*property[^"]*"'
                    ]
                    
                    count = 0
                    for pattern in card_patterns:
                        matches = len(re.findall(pattern, listing_html, re.IGNORECASE))
                        if matches > count:
                            count = matches
                    
                    # Procurar paginação
                    pagination_type = "none"
                    pagination_param = "page"
                    
                    if "page=" in listing_html or "pagina=" in listing_html or "p=" in listing_html:
                        pagination_type = "query_param"
                        if "pagina=" in listing_html:
                            pagination_param = "pagina"
                        elif "p=" in listing_html:
                            pagination_param = "p"
                    
                    if count > 0:
                        result["has_properties"] = True
                        result["count"] = count
                        result["listing_url"] = listing_url
                        result["selectors"] = {
                            "card": "[class*='card'], [class*='item'], article",
                            "link": "a[href*='/leilao/'], a[href*='/imovel/']"
                        }
                        result["pagination"] = {
                            "type": pagination_type,
                            "param": pagination_param
                        }
                        result["status"] = "success"
                    else:
                        result["reason"] = "URL de listagem encontrada mas sem cards detectados"
                        result["status"] = "no_properties"
                else:
                    result["reason"] = f"URL de listagem retornou {listing_response.status_code}"
                    result["status"] = "failed"
            except Exception as e:
                result["reason"] = f"Erro ao acessar listagem: {str(e)[:50]}"
                result["status"] = "error"
                
    except Exception as e:
        result["reason"] = f"Erro: {str(e)[:100]}"
        result["status"] = "error"
    
    return result

async def main():
    """Função principal."""
    print("="*60)
    print("ANÁLISE AUTÔNOMA DE SITES TIER 3")
    print("="*60)
    
    all_sites = LOTE_A + LOTE_B + LOTE_C
    
    print(f"\nTotal de sites: {len(all_sites)}")
    print(f"Lote A: {len(LOTE_A)} sites")
    print(f"Lote B: {len(LOTE_B)} sites")
    print(f"Lote C: {len(LOTE_C)} sites")
    
    # Analisar cada site
    for i, site in enumerate(all_sites, 1):
        print(f"\n[{i}/{len(all_sites)}] Processando: {site['name']}")
        
        result = await analyze_site_browser(site)
        results.append(result)
        
        # Criar config
        config = create_config(
            site=result["site"],
            has_properties=result["has_properties"],
            count=result["count"],
            listing_url=result["listing_url"],
            selectors=result["selectors"],
            pagination=result["pagination"],
            method=result["method"],
            reason=result["reason"]
        )
        
        # Salvar config
        site_id = config["id"]
        config_file = CONFIG_DIR / f"{site_id}.json"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"  [OK] Config salvo: {config_file}")
        print(f"  Status: {result['status']}")
        if result["has_properties"]:
            print(f"  Imoveis estimados: {result['count']}")
        else:
            print(f"  Motivo: {result['reason']}")
        
        # Pequeno delay para não sobrecarregar
        await asyncio.sleep(1)
    
    # Gerar relatório
    print("\n" + "="*60)
    print("RELATÓRIO FINAL")
    print("="*60)
    
    sites_with_properties = [r for r in results if r["has_properties"]]
    sites_without_properties = [r for r in results if not r["has_properties"]]
    
    print(f"\nSites analisados: {len(results)}")
    print(f"Sites com imóveis: {len(sites_with_properties)}")
    print(f"Sites sem imóveis: {len(sites_without_properties)}")
    print(f"Configs criados: {len(results)}")
    
    total_properties = sum(r["count"] for r in sites_with_properties)
    print(f"Imóveis potenciais adicionais: ~{total_properties}")
    
    print("\n" + "="*60)
    print("TABELA DE RESULTADOS")
    print("="*60)
    print(f"{'Site':<30} {'Tem Imóveis?':<15} {'Quantidade':<12} {'Método':<12} {'Status':<10}")
    print("-"*80)
    
    for result in results:
        site_name = result["site"]["name"][:28]
        has_props = "Sim" if result["has_properties"] else "Não"
        count = str(result["count"]) if result["has_properties"] else "-"
        method = result["method"][:10]
        status = "[OK]" if result["status"] == "success" else "[X]"
        
        print(f"{site_name:<30} {has_props:<15} {count:<12} {method:<12} {status:<10}")
    
    # Salvar relatório JSON
    report_file = Path("tier3_analysis_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_sites": len(results),
            "sites_with_properties": len(sites_with_properties),
            "sites_without_properties": len(sites_without_properties),
            "total_properties_estimated": total_properties,
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Relatorio salvo em: {report_file}")

if __name__ == "__main__":
    asyncio.run(main())

