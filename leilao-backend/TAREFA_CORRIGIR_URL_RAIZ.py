# ============================================================
# TAREFA: Corrigir URLs - Buscar categoria RAIZ de imóveis
# ============================================================

"""
╔══════════════════════════════════════════════════════════════╗
║  PROBLEMA IDENTIFICADO                                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  A tarefa anterior encontrou SUBCATEGORIAS:                  ║
║  - /imoveis/casas (só casas)                                 ║
║  - /imoveis/apartamentos (só apartamentos)                   ║
║  - /todos-imoveis/terrenos (só terrenos)                     ║
║                                                              ║
║  Precisamos da CATEGORIA RAIZ:                               ║
║  - /imoveis (TODOS os imóveis)                               ║
║  - /leilao-de-imoveis (TODOS os imóveis)                     ║
║                                                              ║
║  SOLUÇÃO: Subir na hierarquia da URL até encontrar a raiz    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import re
from datetime import datetime
from urllib.parse import urlparse, urljoin

# URLs encontradas anteriormente (subcategorias)
URLS_ENCONTRADAS = {
    "megaleiloes": {
        "name": "Mega Leilões",
        "website": "https://www.megaleiloes.com.br",
        "url_subcategoria": "/imoveis/casas",
        "urls_testar": [
            "/imoveis",  # Raiz provável
            "/leiloes/imoveis",
            "/buscar?categoria=imoveis",
        ]
    },
    "sold": {
        "name": "Sold Leilões", 
        "website": "https://www.sold.com.br",
        "url_subcategoria": "/h/imoveis?searchType=opened&pageNumber=1&pageSize=15&orderBy=price:desc",
        "urls_testar": [
            "/h/imoveis",  # Já parece ser a raiz
            "/imoveis",
            "/leiloes/imoveis",
        ]
    },
    "lancejudicial": {
        "name": "Lance Judicial",
        "website": "https://www.lancejudicial.com.br",
        "url_subcategoria": "/imoveis/apartamentos",
        "urls_testar": [
            "/imoveis",  # Raiz provável
            "/leiloes/imoveis",
        ]
    },
    "portalzuk": {
        "name": "Portal Zukerman",
        "website": "https://www.portalzuk.com.br",
        "url_subcategoria": "/leilao-de-imoveis/t/todos-imoveis/terrenos",
        "urls_testar": [
            "/leilao-de-imoveis",  # Raiz provável
            "/leilao-de-imoveis/t/todos-imoveis",  # Pode ser "todos"
            "/imoveis",
        ]
    },
    "sodresantoro": {
        "name": "Sodré Santoro",
        "website": "https://www.sodresantoro.com.br",
        "url_subcategoria": "/imoveis",  # Já parece ser a raiz
        "urls_testar": [
            "/imoveis",  # Confirmar
            "/leiloes/imoveis",
        ]
    },
}


async def testar_url_raiz(site_id: str, config: dict) -> dict:
    """Testa URLs candidatas e encontra a raiz de imóveis."""
    
    result = {
        "id": site_id,
        "name": config["name"],
        "website": config["website"],
        "url_subcategoria": config["url_subcategoria"],
        "url_raiz": None,
        "total_imoveis_estimado": 0,
        "subcategorias_encontradas": [],
        "success": False,
    }
    
    print(f"\n{'='*60}")
    print(f"[SITE] {config['name']}")
    print(f"   Subcategoria atual: {config['url_subcategoria']}")
    print(f"{'='*60}")
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("   [ERRO] Playwright nao instalado")
        return result
    
    try:
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
            
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            
            page = await context.new_page()
            
            best_url = None
            best_count = 0
            subcategorias = []
            
            for url_path in config["urls_testar"]:
                full_url = config["website"].rstrip('/') + url_path
                
                print(f"\n   [TESTANDO] {url_path}")
                
                try:
                    await page.goto(full_url, wait_until='domcontentloaded', timeout=25000)
                    await asyncio.sleep(4)
                    
                    # Scroll
                    await page.evaluate("window.scrollBy(0, 800)")
                    await asyncio.sleep(1)
                    
                    html = await page.content()
                    page_text = await page.evaluate("() => document.body.innerText")
                    
                    # Contar itens/imóveis na página
                    # Procurar por contadores comuns
                    count_patterns = [
                        r'(\d+)\s*(?:imóveis|imoveis|resultados|itens|lotes)',
                        r'(?:encontrados?|exibindo)\s*(\d+)',
                        r'total[:\s]*(\d+)',
                        r'(\d+)\s*(?:de\s*\d+)',
                    ]
                    
                    item_count = 0
                    for pattern in count_patterns:
                        matches = re.findall(pattern, page_text, re.I)
                        for match in matches:
                            num = int(match) if isinstance(match, str) else int(match[0])
                            if num > item_count and num < 50000:  # Sanity check
                                item_count = num
                    
                    # Contar cards/links de imóveis
                    card_count = len(re.findall(r'/imovel/\d+|/lote/\d+|/leilao/\d+', html, re.I))
                    
                    # Procurar subcategorias (links para casas, apartamentos, etc.)
                    subcat_links = re.findall(
                        r'href=["\']([^"\']*(?:/imoveis/|/leilao-de-imoveis/)[^"\']*(?:casa|apartamento|terreno|comercial|rural)[^"\']*)["\']',
                        html, re.I
                    )
                    
                    print(f"      Contador encontrado: {item_count}")
                    print(f"      Cards na página: {card_count}")
                    print(f"      Subcategorias: {len(set(subcat_links))}")
                    
                    # Se tem subcategorias, provavelmente é a raiz
                    if len(set(subcat_links)) >= 2:
                        subcategorias = list(set(subcat_links))[:5]
                        print(f"      [OK] Parece ser a RAIZ (tem subcategorias)")
                        
                        if item_count > best_count or (item_count == 0 and card_count > best_count):
                            best_count = item_count if item_count > 0 else card_count
                            best_url = url_path
                    
                    # Se não tem subcategorias mas tem muitos itens
                    elif item_count > best_count or card_count > best_count:
                        best_count = item_count if item_count > 0 else card_count
                        best_url = url_path
                
                except Exception as e:
                    print(f"      [ERRO] {str(e)[:40]}")
                
                await asyncio.sleep(1)
            
            # Resultado
            if best_url:
                result["success"] = True
                result["url_raiz"] = best_url
                result["total_imoveis_estimado"] = best_count
                result["subcategorias_encontradas"] = subcategorias
                
                print(f"\n   [OK] URL RAIZ: {best_url}")
                print(f"   [TOTAL] Estimado: {best_count} imoveis")
            else:
                # Usar a primeira URL testada como fallback
                result["url_raiz"] = config["urls_testar"][0]
                result["success"] = True
                print(f"\n   [WARN] Usando fallback: {result['url_raiz']}")
            
            await browser.close()
    
    except Exception as e:
        print(f"   [ERRO] {e}")
        result["url_raiz"] = config["urls_testar"][0]  # Fallback
    
    return result


def atualizar_config(site_id: str, url_raiz: str, total_estimado: int):
    """Atualiza config com URL raiz correta."""
    
    config_path = f"app/configs/sites/{site_id}.json"
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {"id": site_id}
        
        # Atualizar
        config["scraping"] = config.get("scraping", {})
        config["scraping"]["listing_url"] = url_raiz
        config["scraping"]["is_root_category"] = True
        
        config["metadata"] = config.get("metadata", {})
        config["metadata"]["imoveis_total_estimado"] = total_estimado
        config["metadata"]["url_corrigida_at"] = datetime.now().isoformat()
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"   [CONFIG] Atualizada: {config_path}")
        
    except Exception as e:
        print(f"   [ERRO] {e}")


async def main():
    """Função principal."""
    
    print("="*70)
    print("CORRECAO: Encontrar URL RAIZ de Imoveis")
    print("="*70)
    print("\nProblema: Tarefa anterior encontrou subcategorias")
    print("Solução: Testar URLs mais genéricas (raiz da categoria)")
    
    results = []
    
    for site_id, config in URLS_ENCONTRADAS.items():
        result = await testar_url_raiz(site_id, config)
        results.append(result)
        
        if result["success"]:
            import os
            atualizar_config(site_id, result["url_raiz"], result["total_imoveis_estimado"])
        
        await asyncio.sleep(2)
    
    # Relatório
    print("\n" + "="*70)
    print("RESULTADO FINAL - URLs RAIZ")
    print("="*70)
    
    print(f"\n{'Site':<20} {'URL Anterior':<30} {'URL Corrigida':<25} {'Imóveis Est.'}")
    print("-"*90)
    
    for r in results:
        anterior = r["url_subcategoria"][:28] + ".." if len(r["url_subcategoria"]) > 30 else r["url_subcategoria"]
        print(f"{r['name']:<20} {anterior:<30} {r['url_raiz']:<25} {r['total_imoveis_estimado']}")
    
    # Salvar
    report = {
        "generated_at": datetime.now().isoformat(),
        "objetivo": "Corrigir URLs para categoria RAIZ de imóveis",
        "results": results
    }
    
    with open("urls_raiz_corrigidas.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n[REPORT] Relatorio: urls_raiz_corrigidas.json")


if __name__ == "__main__":
    import os
    asyncio.run(main())
