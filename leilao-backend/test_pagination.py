"""
Teste de paginação com leiloeiro real.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Adiciona o diretório do backend ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.scrapers.generic_scraper import GenericScraper, ScraperConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pagination():
    print("=" * 60)
    print("TESTE DE PAGINAÇÃO")
    print("=" * 60)
    
    # Configuração para Mega Leilões
    config = ScraperConfig(
        name="Mega Leilões",
        base_url="https://www.megaleiloes.com.br",
        listings_url_template="https://www.megaleiloes.com.br/",
        card_selector='div[class*="card"], div[class*="lote"], article, div[class*="item"]',
    )
    
    scraper = GenericScraper(config=config)
    
    # Testa com Mega Leilões (grande volume)
    url = "https://www.megaleiloes.com.br/"
    
    print(f"\nTestando: {url}")
    print("Limite de páginas: 5 (para teste)")
    print("-" * 40)
    
    # Scrape com paginação limitada
    properties = await scraper.scrape_all_pages(
        base_url=url,
        max_pages=5,  # Limita para teste
        delay=2.0  # Delay de 2 segundos
    )
    
    print(f"\nResultado:")
    print(f"  Total de imóveis: {len(properties)}")
    
    if properties:
        print(f"\nPrimeiros 3 imóveis:")
        for i, prop in enumerate(properties[:3], 1):
            print(f"  {i}. {prop.get('title', 'Sem título')[:50]}...")
            print(f"     Categoria: {prop.get('category')}")
            print(f"     Cidade: {prop.get('city')}")
    
    # Estatísticas esperadas
    print("\n" + "=" * 60)
    if len(properties) >= 20:
        print("✅ PAGINAÇÃO FUNCIONANDO!")
        print(f"   Sem paginação: ~20 imóveis")
        print(f"   Com paginação: {len(properties)} imóveis")
    else:
        print("⚠️ Poucos imóveis encontrados")
        print("   Verifique se a paginação está funcionando")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_pagination())

