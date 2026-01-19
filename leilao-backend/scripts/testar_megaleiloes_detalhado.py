"""
Teste detalhado do scraper Megaleiloes
"""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

print("=" * 60)
print("TESTE DETALHADO - MEGALEILOES")
print("=" * 60)

# 1. Verificar credenciais
print("\n[1] VERIFICANDO CREDENCIAIS")
openai_key = os.getenv("OPENAI_API_KEY")
scrapingbee_key = os.getenv("SCRAPINGBEE_API_KEY")
print(f"  OPENAI_API_KEY: {'OK' if openai_key else 'FALTANDO'}")
print(f"  SCRAPINGBEE_API_KEY: {'OK' if scrapingbee_key else 'FALTANDO'}")

# 2. Tentar importar scrapers
print("\n[2] IMPORTANDO SCRAPERS")
try:
    from app.scrapers.scraper_manager import ScraperManager

    print("  ScraperManager: OK")
except ImportError as e:
    print(f"  ScraperManager: ERRO - {e}")

try:
    from app.services.universal_scraper_service import UniversalScraperService

    print("  UniversalScraperService: OK")
except ImportError as e:
    print(f"  UniversalScraperService: ERRO - {e}")

# 3. Listar scrapers disponiveis
print("\n[3] SCRAPERS REGISTRADOS")
try:
    manager = ScraperManager()
    if hasattr(manager, "scrapers"):
        print(f"  Total: {len(manager.scrapers)}")
        for name in list(manager.scrapers.keys())[:10]:
            print(f"    - {name}")
    elif hasattr(manager, "get_available_scrapers"):
        scrapers = manager.get_available_scrapers()
        print(f"  Total: {len(scrapers)}")
        for s in scrapers[:10]:
            print(f"    - {s}")
    else:
        print("  Estrutura do manager desconhecida")
        print(f"  Atributos: {dir(manager)}")
except Exception as e:
    print(f"  ERRO: {e}")

# 4. Testar scrape do Megaleiloes
print("\n[4] TESTANDO SCRAPE - MEGALEILOES")
url = "https://www.megaleiloes.com.br/"

try:
    from app.scrapers.megaleiloes_scraper import MegaleiloesScraper

    scraper = MegaleiloesScraper()
    print(f"  URL: {url}")
    print("  Iniciando scrape limitado (max_properties=5)...")

    result = scraper.scrape_properties(max_properties=5, verify_urls=False)

    print(
        f"  Resultado: {result.total_complete} completos, "
        f"{result.total_incomplete} incompletos, "
        f"{result.total_scraped} total"
    )

    if result.errors:
        print(f"  Erros: {len(result.errors)}")
        for err in result.errors[:3]:
            print(f"    - {err}")

    if result.complete_properties:
        for i, prop in enumerate(result.complete_properties[:3]):
            print(f"\n  Imovel {i+1}:")
            print(f"    Titulo: {prop.title[:50]}")
            print(f"    Cidade: {prop.city}")
            print(f"    Estado: {prop.state}")
            print(f"    Preco: {prop.first_auction_value or prop.evaluation_value}")
            print(f"    Source: {prop.source}")
    else:
        print("  NENHUM IMOVEL COMPLETO EXTRAIDO!")

except Exception as e:
    print(f"  ERRO durante scrape: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("FIM DO TESTE")
print("=" * 60)
