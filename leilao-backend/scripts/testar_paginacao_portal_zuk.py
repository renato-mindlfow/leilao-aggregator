"""
Testa a paginação do Portal Zuk para verificar quantos imóveis estão disponíveis
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scrapers.portalzuk_scraper_v2 import PortalZukScraperV2

async def test_pagination():
    print("=" * 60)
    print("TESTE DE PAGINACAO - PORTAL ZUK")
    print("=" * 60)
    
    scraper = PortalZukScraperV2(headless=True)
    
    try:
        await scraper._setup_browser()
        print("\n[1] Navegando para página de listagem...")
        await scraper.page.goto(scraper.LISTING_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        
        print("\n[2] Coletando links sem limite...")
        links = await scraper._collect_property_links(max_properties=None)
        print(f"  Total de links encontrados: {len(links)}")
        
        print("\n[3] Amostra de links (primeiros 10):")
        for i, link in enumerate(links[:10], 1):
            print(f"  {i}. {link[:80]}")
        
        print("\n[4] Testando paginação página por página:")
        page_num = 1
        max_pages = 10
        all_links = set()
        
        while page_num <= max_pages:
            url = scraper.LISTING_URL if page_num == 1 else f"{scraper.LISTING_URL}?page={page_num}"
            
            print(f"\n  Página {page_num}: {url}")
            await scraper.page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)
            
            await scraper._scroll_page()
            
            links_on_page = await scraper.page.query_selector_all(
                'a[href*="/imovel/"], a[href*="/lote/"], a[href*="imoveis/"]'
            )
            
            page_links = set()
            for link in links_on_page:
                href = await link.get_attribute("href")
                if not href:
                    continue
                full_url = href if href.startswith("http") else f"{scraper.BASE_URL}{href}"
                if "/imovel/" in full_url or "/lote/" in full_url:
                    page_links.add(full_url)
            
            new_links = page_links - all_links
            all_links.update(new_links)
            
            print(f"    Links nesta página: {len(page_links)}")
            print(f"    Novos links: {len(new_links)}")
            print(f"    Total acumulado: {len(all_links)}")
            
            if not new_links:
                print(f"    Sem novos links, parando na página {page_num}")
                break
            
            page_num += 1
        
        print(f"\n[5] Resumo:")
        print(f"  Total de links únicos: {len(all_links)}")
        print(f"  Páginas navegadas: {page_num}")
        
    finally:
        await scraper._close_browser()
    
    print("\n" + "=" * 60)
    print("FIM DO TESTE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_pagination())
