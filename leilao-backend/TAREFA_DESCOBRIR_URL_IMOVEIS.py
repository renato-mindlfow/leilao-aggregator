# ============================================================
# TAREFA: Descobrir URL de IMÓVEIS em cada site
# ============================================================
# Para: Cursor Agent
# Modo: AUTÔNOMO
# ============================================================

"""
╔══════════════════════════════════════════════════════════════╗
║  PROBLEMA IDENTIFICADO                                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  As tarefas anteriores estavam usando a página PRINCIPAL     ║
║  dos sites, que contém TODOS os tipos de bens:               ║
║  - Imóveis                                                   ║
║  - Veículos                                                  ║
║  - Máquinas                                                  ║
║  - Equipamentos                                              ║
║  - etc.                                                      ║
║                                                              ║
║  SOLUÇÃO: Descobrir a URL específica de IMÓVEIS              ║
║                                                              ║
║  Padrões comuns:                                             ║
║  - /imoveis                                                  ║
║  - /leilao-de-imoveis                                        ║
║  - /buscar?categoria=imoveis                                 ║
║  - /buscar?tipo=imovel                                       ║
║  - Menu "Imóveis" na página principal                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse, parse_qs

# ============================================================
# SITES PARA DESCOBRIR URL DE IMÓVEIS
# ============================================================

SITES = [
    {
        "id": "megaleiloes",
        "name": "Mega Leilões", 
        "website": "https://www.megaleiloes.com.br",
    },
    {
        "id": "sold",
        "name": "Sold Leilões",
        "website": "https://www.sold.com.br",
    },
    {
        "id": "lancejudicial",
        "name": "Lance Judicial",
        "website": "https://www.lancejudicial.com.br",
    },
    {
        "id": "portalzuk",
        "name": "Portal Zukerman",
        "website": "https://www.portalzuk.com.br",
    },
    {
        "id": "sodresantoro",
        "name": "Sodré Santoro",
        "website": "https://www.sodresantoro.com.br",
    },
]

# Padrões de URL que indicam página de imóveis
IMOVEIS_URL_PATTERNS = [
    r'/imoveis',
    r'/imovel',
    r'/leilao-de-imoveis',
    r'/leiloes-de-imoveis', 
    r'/leiloes/imoveis',
    r'/categoria/imoveis',
    r'/categorias/imoveis',
    r'/buscar\?.*(?:categoria|tipo|filter).*imov',
    r'/busca\?.*(?:categoria|tipo|filter).*imov',
    r'/search\?.*(?:category|type).*(?:property|imovel|real.?estate)',
]

# Palavras-chave que indicam link para imóveis
IMOVEIS_KEYWORDS = [
    'imóveis', 'imoveis', 'imóvel', 'imovel',
    'apartamento', 'casa', 'terreno', 'fazenda',
    'comercial', 'galpão', 'galpao',
    'real estate', 'property', 'properties',
]

# Palavras que indicam NÃO ser imóvel (para filtrar)
NON_IMOVEIS_KEYWORDS = [
    'veículo', 'veiculo', 'carro', 'moto', 'caminhão',
    'máquina', 'maquina', 'equipamento', 'eletrônico',
    'arte', 'joia', 'móvel', 'movel',  # móvel = furniture, não imóvel
]


async def descobrir_url_imoveis(site: Dict) -> Dict:
    """
    Descobre a URL específica de imóveis em um site.
    
    Estratégia:
    1. Acessar página principal
    2. Procurar links/menus que levem a imóveis
    3. Identificar padrão de URL para imóveis
    4. Validar que a URL encontrada tem imóveis
    """
    
    result = {
        "id": site["id"],
        "name": site["name"],
        "website": site["website"],
        "success": False,
        "imoveis_url": None,
        "imoveis_count": 0,
        "url_type": None,  # 'direct_path', 'query_param', 'api', 'menu_link'
        "all_category_links": [],
        "analysis": {},
        "errors": [],
    }
    
    print(f"\n{'='*60}")
    print(f"[DESCOBRINDO] URL de IMOVEIS: {site['name']}")
    print(f"{'='*60}")
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        result["errors"].append("Playwright não instalado")
        return result
    
    try:
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
            
            # Stealth básico
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            
            page = await context.new_page()
            
            # ========================================
            # FASE 1: Acessar página principal
            # ========================================
            print(f"\n[ACESSANDO] {site['website']}")
            
            try:
                await page.goto(site["website"], wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(5)
            except Exception as e:
                print(f"   [WARN] Timeout, continuando...")
            
            # ========================================
            # FASE 2: Procurar links para imóveis
            # ========================================
            print(f"\n[PROCURANDO] Links para imoveis...")
            
            html = await page.content()
            
            # Encontrar todos os links
            all_links = await page.query_selector_all('a[href]')
            
            imoveis_links = []
            category_links = []
            
            for link in all_links:
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    
                    if not href:
                        continue
                    
                    href_lower = href.lower()
                    text_lower = text.lower().strip()
                    
                    # Verificar se é link de categoria
                    is_category = any(kw in href_lower or kw in text_lower 
                                     for kw in ['categoria', 'category', 'tipo', 'type', 'filtro', 'filter'])
                    
                    # Verificar se é link de imóveis
                    is_imoveis = any(kw in href_lower or kw in text_lower 
                                    for kw in IMOVEIS_KEYWORDS)
                    
                    # Verificar se NÃO é imóvel
                    is_not_imoveis = any(kw in href_lower or kw in text_lower 
                                        for kw in NON_IMOVEIS_KEYWORDS)
                    
                    if is_imoveis and not is_not_imoveis:
                        full_url = urljoin(site["website"], href)
                        imoveis_links.append({
                            "url": full_url,
                            "text": text_lower[:50],
                            "href": href,
                        })
                    
                    if is_category:
                        full_url = urljoin(site["website"], href)
                        category_links.append({
                            "url": full_url,
                            "text": text_lower[:50],
                        })
                
                except:
                    continue
            
            # Remover duplicatas
            seen_urls = set()
            unique_imoveis = []
            for link in imoveis_links:
                if link["url"] not in seen_urls:
                    seen_urls.add(link["url"])
                    unique_imoveis.append(link)
            
            result["all_category_links"] = category_links[:10]
            
            print(f"   Links de imóveis encontrados: {len(unique_imoveis)}")
            
            for link in unique_imoveis[:5]:
                print(f"      • {link['text'][:30]} -> {link['url'][:50]}...")
            
            # ========================================
            # FASE 3: Testar URLs candidatas
            # ========================================
            print(f"\n[TESTANDO] URLs candidatas...")
            
            # URLs para testar (encontradas + padrões comuns)
            urls_to_test = []
            
            # Adicionar links encontrados
            for link in unique_imoveis[:5]:
                urls_to_test.append(link["url"])
            
            # Adicionar padrões comuns
            common_paths = [
                '/imoveis',
                '/leilao-de-imoveis',
                '/leiloes/imoveis',
                '/buscar?categoria=imoveis',
                '/buscar?tipo=imovel',
                '/busca?categoria=imoveis',
                '/catalogo/imoveis',
            ]
            
            for path in common_paths:
                urls_to_test.append(site["website"].rstrip('/') + path)
            
            # Remover duplicatas
            urls_to_test = list(dict.fromkeys(urls_to_test))
            
            best_url = None
            best_count = 0
            
            for test_url in urls_to_test[:10]:
                try:
                    print(f"\n   [TESTANDO] {test_url[:60]}...")
                    
                    response = await page.goto(test_url, wait_until='domcontentloaded', timeout=20000)
                    
                    if not response or response.status != 200:
                        print(f"      [ERRO] HTTP {response.status if response else 'N/A'}")
                        continue
                    
                    await asyncio.sleep(3)
                    
                    # Scroll para carregar conteúdo
                    await page.evaluate("window.scrollBy(0, 1000)")
                    await asyncio.sleep(1)
                    
                    test_html = await page.content()
                    
                    # Contar indicadores de imóveis
                    imovel_indicators = 0
                    
                    # Palavras-chave de imóveis
                    for kw in ['apartamento', 'casa', 'terreno', 'imóvel', 'imovel', 'm²', 'quartos', 'dormitórios']:
                        imovel_indicators += len(re.findall(kw, test_html, re.I))
                    
                    # Links de detalhes de imóveis
                    detail_links = len(re.findall(r'/imovel/\d+|/lote/\d+|/item/\d+', test_html, re.I))
                    imovel_indicators += detail_links * 10  # Peso maior
                    
                    # Verificar se NÃO tem muitos veículos
                    veiculo_count = len(re.findall(r'veículo|carro|moto|caminhão', test_html, re.I))
                    
                    # Score final
                    score = imovel_indicators - (veiculo_count * 5)
                    
                    print(f"      Indicadores imóveis: {imovel_indicators}, Veículos: {veiculo_count}, Score: {score}")
                    
                    if score > best_count:
                        best_count = score
                        best_url = test_url
                        print(f"      [OK] Melhor ate agora!")
                    
                except Exception as e:
                    print(f"      [ERRO] {str(e)[:50]}")
                
                await asyncio.sleep(1)
            
            # ========================================
            # FASE 4: Validar melhor URL
            # ========================================
            if best_url and best_count > 50:
                result["success"] = True
                result["imoveis_url"] = best_url
                result["imoveis_count"] = best_count
                
                # Determinar tipo de URL
                if '?' in best_url:
                    result["url_type"] = "query_param"
                elif '/imovel' in best_url.lower() or '/imoveis' in best_url.lower():
                    result["url_type"] = "direct_path"
                else:
                    result["url_type"] = "menu_link"
                
                print(f"\n[OK] URL de IMOVEIS encontrada!")
                print(f"   URL: {best_url}")
                print(f"   Tipo: {result['url_type']}")
                print(f"   Score: {best_count}")
            else:
                print(f"\n[WARN] Nenhuma URL especifica de imoveis encontrada")
                print(f"   Melhor candidata: {best_url} (score: {best_count})")
                result["analysis"]["best_candidate"] = best_url
                result["analysis"]["best_score"] = best_count
            
            await browser.close()
    
    except Exception as e:
        result["errors"].append(str(e))
        print(f"[ERRO] {e}")
    
    return result


def update_config_with_imoveis_url(site_id: str, imoveis_url: str, url_type: str):
    """Atualiza config do site com URL de imóveis."""
    
    import os
    
    config_path = f"app/configs/sites/{site_id}.json"
    
    try:
        # Carregar config existente ou criar nova
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {
                "id": site_id,
                "enabled": False,
            }
        
        # Extrair path relativo
        from urllib.parse import urlparse
        parsed = urlparse(imoveis_url)
        listing_path = parsed.path
        if parsed.query:
            listing_path += '?' + parsed.query
        
        # Atualizar
        config["scraping"] = config.get("scraping", {})
        config["scraping"]["listing_url"] = listing_path
        config["scraping"]["imoveis_url_full"] = imoveis_url
        config["scraping"]["url_type"] = url_type
        
        config["metadata"] = config.get("metadata", {})
        config["metadata"]["imoveis_url_discovered_at"] = datetime.now().isoformat()
        
        # Salvar
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"   [CONFIG] Atualizada: {config_path}")
        
    except Exception as e:
        print(f"   [ERRO] Erro ao salvar config: {e}")


async def main():
    """Função principal."""
    
    print("="*70)
    print("DESCOBERTA DE URLs DE IMOVEIS")
    print("="*70)
    print("\nObjetivo: Encontrar a URL especifica de IMOVEIS em cada site")
    print("          (nao a pagina principal com todos os tipos de bens)")
    
    results = []
    
    for site in SITES:
        result = await descobrir_url_imoveis(site)
        results.append(result)
        
        # Atualizar config se encontrou URL
        if result["success"] and result["imoveis_url"]:
            update_config_with_imoveis_url(
                result["id"],
                result["imoveis_url"],
                result["url_type"]
            )
        
        await asyncio.sleep(3)
    
    # Relatório final
    print("\n" + "="*70)
    print("RELATORIO FINAL")
    print("="*70)
    
    success_count = sum(1 for r in results if r["success"])
    
    print(f"\nSites analisados: {len(results)}")
    print(f"URLs de imóveis encontradas: {success_count}")
    
    print("\n" + "-"*70)
    
    for r in results:
        status = "[OK]" if r["success"] else "[FALHA]"
        print(f"\n{status} {r['name']}")
        
        if r["success"]:
            print(f"   URL: {r['imoveis_url']}")
            print(f"   Tipo: {r['url_type']}")
        else:
            print(f"   Melhor candidata: {r['analysis'].get('best_candidate', 'N/A')}")
            print(f"   Score: {r['analysis'].get('best_score', 0)}")
        
        if r["all_category_links"]:
            print(f"   Links de categoria encontrados: {len(r['all_category_links'])}")
    
    # Salvar relatório
    report = {
        "generated_at": datetime.now().isoformat(),
        "objective": "Descobrir URL específica de IMÓVEIS em cada site",
        "total_sites": len(results),
        "successful": success_count,
        "results": results
    }
    
    with open("descoberta_urls_imoveis.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n[REPORT] Relatorio salvo: descoberta_urls_imoveis.json")
    
    print("\n" + "="*70)
    print("[OK] DESCOBERTA CONCLUIDA")
    print("="*70)


if __name__ == "__main__":
    import os
    asyncio.run(main())
