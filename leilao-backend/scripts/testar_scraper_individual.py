"""
Testa um scraper individual para diagnostico
Uso: python scripts/testar_scraper_individual.py <website_url>
"""
import io
import os
import sys

# Forcar UTF-8 no console do Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


def testar_scraper(url: str) -> None:
    print(f"Testando scraper para: {url}")
    print("-" * 60)

    try:
        # Tentar importar universal scraper
        from app.services.universal_scraper import UniversalScraper

        scraper = UniversalScraper()

        # Rodar scraping async no loop atual
        import asyncio

        result = asyncio.run(scraper.scrape_auctioneer({"website": url, "name": url}))

        print(f"Resultado: {len(result) if result else 0} imoveis")

        if result:
            for i, prop in enumerate(result[:3]):
                print(f"\nImovel {i+1}:")
                print(f"  Titulo: {prop.get('title', 'N/A')[:50]}")
                print(f"  Cidade: {prop.get('city', 'N/A')}")
                print(f"  Estado: {prop.get('state', 'N/A')}")
                print(f"  Preco: {prop.get('price', 'N/A')}")
                print(f"  URL: {prop.get('source_url', 'N/A')[:80]}")
        else:
            print("Nenhum imovel extraido!")

    except ImportError as exc:
        print(f"Erro de import: {exc}")
        print("Tentando scraper generico...")

        try:
            from app.scrapers.generic_scraper import GenericScraper

            scraper = GenericScraper()
            result = scraper.scrape(url, max_properties=3)
            print(f"Resultado (generico): {len(result) if result else 0} imoveis")
        except Exception as exc2:
            print(f"Erro no scraper generico: {exc2}")

    except Exception as exc:
        print(f"Erro durante scraping: {exc}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Testar com URL conhecida
        test_urls = [
            "https://www.megaleiloes.com.br",
            "https://www.sodresantoro.com.br",
            "https://www.lfreiloes.com.br",
        ]
        for url in test_urls:
            testar_scraper(url)
            print("\n" + "=" * 60 + "\n")
    else:
        testar_scraper(sys.argv[1])
