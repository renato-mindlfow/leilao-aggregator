"""
Verifica qual arquitetura de scraping está implementada.
Resultado: Confirma se estamos usando Crawl4AI + LLM (95% sucesso)
"""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 70)
print("VERIFICAÇÃO DE ARQUITETURA DE SCRAPING")
print("=" * 70)

# 1. Verificar se Crawl4AI está instalado
print("\n[1] DEPENDÊNCIAS")
try:
    import crawl4ai
    print(f"  crawl4ai: INSTALADO (versão {crawl4ai.__version__ if hasattr(crawl4ai, '__version__') else 'desconhecida'})")
    CRAWL4AI_DISPONIVEL = True
except ImportError:
    print("  crawl4ai: NÃO INSTALADO")
    CRAWL4AI_DISPONIVEL = False

try:
    import openai
    print(f"  openai: INSTALADO")
    OPENAI_DISPONIVEL = True
except ImportError:
    print("  openai: NÃO INSTALADO")
    OPENAI_DISPONIVEL = False

try:
    from playwright.sync_api import sync_playwright
    print("  playwright: INSTALADO")
    PLAYWRIGHT_DISPONIVEL = True
except ImportError:
    print("  playwright: NÃO INSTALADO")
    PLAYWRIGHT_DISPONIVEL = False

# 2. Verificar UniversalScraper
print("\n[2] UNIVERSAL SCRAPER (Crawl4AI + LLM)")
try:
    from app.services.universal_scraper import UniversalScraper
    print("  UniversalScraper: DISPONÍVEL")
    
    # Verificar se usa Crawl4AI
    import inspect
    source = inspect.getsourcefile(UniversalScraper)
    with open(source, 'r', encoding='utf-8') as f:
        content = f.read()
    
    usa_crawl4ai = 'crawl4ai' in content.lower()
    usa_llm = any(x in content.lower() for x in ['llm', 'openai', 'gpt'])
    
    print(f"  Usa Crawl4AI: {'SIM' if usa_crawl4ai else 'NÃO'}")
    print(f"  Usa LLM/OpenAI: {'SIM' if usa_llm else 'NÃO'}")
        
except ImportError as e:
    print(f"  UniversalScraper: NÃO DISPONÍVEL ({e})")
    usa_crawl4ai = False
    usa_llm = False

# 3. Verificar scrapers específicos
print("\n[3] SCRAPERS ESPECÍFICOS")
scrapers_dir = os.path.join(os.path.dirname(__file__), "..", "app", "scrapers")
if os.path.exists(scrapers_dir):
    scrapers = [f for f in os.listdir(scrapers_dir) if f.endswith('_scraper.py')]
    print(f"  Total de scrapers: {len(scrapers)}")
    
    scraper_methods = {}
    for scraper_file in scrapers:
        filepath = os.path.join(scrapers_dir, scraper_file)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
        except:
            continue
        
        methods = []
        if 'crawl4ai' in content:
            methods.append('Crawl4AI')
        if 'playwright' in content:
            methods.append('Playwright')
        if 'selenium' in content:
            methods.append('Selenium')
        if 'requests' in content or 'httpx' in content:
            methods.append('HTTP')
        if 'beautifulsoup' in content:
            methods.append('BeautifulSoup')
        if 'scrapingbee' in content:
            methods.append('ScrapingBee')
        
        scraper_methods[scraper_file] = methods
        
    # Mostrar apenas primeiros 10
    for scraper_file in list(scraper_methods.keys())[:10]:
        methods = scraper_methods[scraper_file]
        print(f"  {scraper_file}: {', '.join(methods) if methods else 'Desconhecido'}")
    
    if len(scraper_methods) > 10:
        print(f"  ... e mais {len(scraper_methods) - 10} scrapers")

# 4. Verificar ScraperManager
print("\n[4] SCRAPER MANAGER")
try:
    from app.scrapers.scraper_manager import ScraperManager
    manager = ScraperManager()
    
    if hasattr(manager, 'scrapers'):
        print(f"  Scrapers registrados: {len(manager.scrapers)}")
        for name in list(manager.scrapers.keys())[:10]:
            print(f"    - {name}")
    else:
        print("  Estrutura do manager desconhecida")
except Exception as e:
    print(f"  ERRO: {e}")

# 5. Resumo
print("\n" + "=" * 70)
print("RESUMO")
print("=" * 70)

if CRAWL4AI_DISPONIVEL and OPENAI_DISPONIVEL:
    print("\n✅ Crawl4AI + OpenAI estão instalados")
    print("   Arquitetura recomendada (95% sucesso) está DISPONÍVEL")
else:
    print("\n⚠️ ATENÇÃO: Dependências faltando")
    if not CRAWL4AI_DISPONIVEL:
        print("   - Instalar: pip install crawl4ai")
    if not OPENAI_DISPONIVEL:
        print("   - Instalar: pip install openai")

if usa_crawl4ai and usa_llm:
    print("\n✅ UniversalScraper usa Crawl4AI + LLM")
    print("   Arquitetura correta (95% sucesso) está IMPLEMENTADA")
elif usa_crawl4ai:
    print("\n⚠️ UniversalScraper usa Crawl4AI mas não LLM")
elif usa_llm:
    print("\n⚠️ UniversalScraper usa LLM mas não Crawl4AI")
else:
    print("\n❌ UniversalScraper NÃO usa Crawl4AI + LLM")
    print("   Arquitetura atual é diferente da recomendada")

print("\n" + "=" * 70)
