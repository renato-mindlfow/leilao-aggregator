"""
Scraper Manager - Coordinates all auction website scrapers.
"""
import logging
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.models.property import Property
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ScraperManager:
    """Manages and coordinates all auction website scrapers."""
    
    def __init__(self):
        self.scrapers: dict[str, BaseScraper] = {}
        self.last_run: Optional[datetime] = None
        self.properties: list[Property] = []
        
    def register_scraper(self, scraper: BaseScraper) -> None:
        """Register a scraper for an auction website."""
        self.scrapers[scraper.name] = scraper
        logger.info(f"Registered scraper: {scraper.name}")
        
    def get_scraper(self, name: str) -> Optional[BaseScraper]:
        """Get a scraper by name."""
        return self.scrapers.get(name)
        
    def list_scrapers(self) -> list[str]:
        """List all registered scrapers."""
        return list(self.scrapers.keys())
        
    def run_scraper(self, name: str, max_pages: int = 5) -> list[Property]:
        """Run a specific scraper and return the properties found."""
        scraper = self.scrapers.get(name)
        if not scraper:
            logger.error(f"Scraper not found: {name}")
            return []
            
        try:
            logger.info(f"Starting scraper: {name}")
            scraper.setup_driver()
            properties = scraper.scrape_listings(max_pages=max_pages)
            logger.info(f"Scraper {name} found {len(properties)} properties")
            return properties
        except Exception as e:
            logger.error(f"Error running scraper {name}: {e}")
            return []
        finally:
            scraper.close_driver()
            
    def run_all_scrapers(self, max_pages: int = 3, max_workers: int = 3) -> list[Property]:
        """Run all registered scrapers and return all properties found."""
        all_properties: list[Property] = []
        
        def run_single(name: str) -> list[Property]:
            return self.run_scraper(name, max_pages=max_pages)
            
        # Run scrapers in parallel with limited workers
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(run_single, self.scrapers.keys())
            for result in results:
                all_properties.extend(result)
                
        self.properties = all_properties
        self.last_run = datetime.now()
        logger.info(f"All scrapers completed. Total properties: {len(all_properties)}")
        return all_properties
        
    def get_properties(self) -> list[Property]:
        """Get all scraped properties."""
        return self.properties
        
    def get_last_run(self) -> Optional[datetime]:
        """Get the timestamp of the last scraper run."""
        return self.last_run


# Global scraper manager instance
scraper_manager = ScraperManager()


def get_scraper_manager() -> ScraperManager:
    """Get the global scraper manager instance."""
    return scraper_manager
