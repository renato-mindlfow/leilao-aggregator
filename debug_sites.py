"""
Debug rápido dos sites que não estão encontrando links
"""
import asyncio
from playwright.async_api import async_playwright
import re
from urllib.parse import urljoin

sites_debug = [
    {
        "name": "Mega Leilões",
        "url": "https://www.megaleiloes.com.br/imoveis",
        "patterns": [r"/leilao/\d+", r"/imovel/\d+"],
    },
    {
        "name": "Lance Judicial",
        "url": "https://www.lancejudicial.com.br/imoveis",
        "patterns": [r"/leilao/\d+", r"/imovel/\d+", r"/lote/\d+"],
    },
    {
        "name": "Portal Zukerman",
        "url": "https://www.portalzuk.com.br/leilao-de-imoveis",
        "patterns": [r"/imovel/[^/]+/\d+"],
    },
]

async def debug_site(site_info):
    """Debug de um site específico."""
    print(f"\n{'='*70}")
    print(f"DEBUG: {site_info['name']}")
    print(f"URL: {site_info['url']}")
    print(f"{'='*70}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        )
        page = await context.new_page()
        
        try:
            await page.goto(site_info['url'], wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)  # Aguardar carregamento
            
            html = await page.content()
            
            # Procurar links com os padrões
            links_found = []
            for pattern in site_info['patterns']:
                matches = re.findall(f'href=["\']([^"\']*{pattern}[^"\']*)["\']', html, re.I)
                for match in matches:
                    links_found.append(match)
            
            print(f"\nLinks encontrados: {len(set(links_found))}")
            if links_found:
                print("Primeiros 5 links:")
                for link in list(set(links_found))[:5]:
                    print(f"  - {link}")
            else:
                print("\nNenhum link encontrado com os padrões!")
                print("\nProcurando qualquer link com 'leilao' ou 'imovel':")
                all_links = re.findall(r'href=["\']([^"\']*(?:leilao|imovel|lote)[^"\']*)["\']', html, re.I)
                if all_links:
                    print(f"Encontrados {len(set(all_links))} links:")
                    for link in list(set(all_links))[:10]:
                        print(f"  - {link}")
                else:
                    print("Nenhum link encontrado!")
            
            # Verificar título da página
            title = await page.title()
            print(f"\nTitulo da pagina: {title}")
            
        except Exception as e:
            print(f"ERRO: {e}")
        finally:
            await browser.close()

async def main():
    for site in sites_debug:
        await debug_site(site)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())

