"""
Testa a paginação do Mega Leilões para verificar duplicatas
"""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scrapers.megaleiloes_scraper import MegaleiloesScraper
from collections import Counter

def test_pagination():
    print("=" * 60)
    print("TESTE DE PAGINACAO - MEGA LEILOES")
    print("=" * 60)
    
    scraper = MegaleiloesScraper()
    
    print("\n[1] Coletando links de múltiplas páginas...")
    all_links = []
    for page in range(1, 11):  # Testar primeiras 10 páginas
        print(f"  Página {page}...")
        links = scraper.get_property_links_from_listing(page=page)
        if not links:
            print(f"    Página {page} não retornou links, parando.")
            break
        print(f"    Encontrados: {len(links)} links")
        all_links.extend(links)
    
    print(f"\n[2] Total de links coletados: {len(all_links)}")
    print(f"  Links únicos: {len(set(all_links))}")
    
    # Verificar duplicatas
    link_counter = Counter(all_links)
    duplicates = {link: count for link, count in link_counter.items() if count > 1}
    
    if duplicates:
        print(f"\n[3] ⚠️  {len(duplicates)} URLs duplicadas encontradas:")
        for link, count in list(duplicates.items())[:5]:
            print(f"    {link[:70]}: {count} vezes")
        if len(duplicates) > 5:
            print(f"    ... e mais {len(duplicates) - 5} URLs duplicadas")
    else:
        print("\n[3] ✓ Nenhuma URL duplicada encontrada")
    
    # Amostra de URLs
    print("\n[4] Amostra de links (primeiros 10):")
    for i, link in enumerate(list(set(all_links))[:10], 1):
        print(f"  {i}. {link[:80]}")
    
    print("\n" + "=" * 60)
    print("FIM DO TESTE")
    print("=" * 60)

if __name__ == "__main__":
    test_pagination()
