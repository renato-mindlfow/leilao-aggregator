# Scrapers module for auction data collection
# Lazy imports para evitar dependências desnecessárias

def __getattr__(name: str):
    """Lazy import de módulos para evitar importar Selenium quando não necessário."""
    if name == 'BaseScraper':
        from .base_scraper import BaseScraper
        return BaseScraper
    elif name == 'ScraperManager':
        from .scraper_manager import ScraperManager
        return ScraperManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Para type checking e imports diretos ainda funcionarem
try:
    from .scraper_manager import ScraperManager
    __all__ = ['ScraperManager']  # BaseScraper só quando necessário
except ImportError:
    __all__ = []
