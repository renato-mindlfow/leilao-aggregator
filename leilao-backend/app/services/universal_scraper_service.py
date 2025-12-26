"""
Universal Scraper Service - Scrapes ALL auctioneers from database using generic or specific scrapers.
Handles retries, error logging, status updates, and ensures all pages are scraped.
"""
import logging
import time
import gc
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from urllib.parse import urlparse, urljoin

from app.services import db
from app.services.postgres_database import PostgresDatabase
from app.scrapers.generic_scraper import GenericScraper, ScraperConfig
from app.scrapers.base_scraper import BaseScraper
from app.models.property import Property
from app.models.auctioneer import Auctioneer
from app.services.quality_filter import QualityFilter, QualityFilterResult

logger = logging.getLogger(__name__)


class UniversalScraperService:
    """
    Service that scrapes ALL auctioneers from the database.
    Uses specific scrapers when available, otherwise falls back to generic scraper.
    """
    
    # Map of auctioneer names/IDs to their specific scraper classes
    SPECIFIC_SCRAPERS: Dict[str, Dict[str, Any]] = {
        "portal_zuk": {
            "name": "Portal Zuk",
            "module": "app.scrapers.portalzuk_scraper",
            "class": "PortalZukScraper",
            "method": "scrape_listings"
        },
        "superbid": {
            "name": "Superbid",
            "module": "app.scrapers.superbid_scraper",
            "class": "SuperbidScraper",
            "method": "scrape_properties"
        },
        "megaleiloes": {
            "name": "Mega Leilões",
            "module": "app.scrapers.megaleiloes_scraper",
            "class": "MegaleiloesScraper",
            "method": "scrape_properties"
        },
        "leilaovip": {
            "name": "Leilão VIP",
            "module": "app.scrapers.leilaovip_scraper",
            "class": "LeilaoVipScraper",
            "method": "scrape_properties"
        },
        "inovaleilao": {
            "name": "Inova Leilão",
            "module": "app.scrapers.inovaleilao_scraper",
            "class": "InovaLeilaoScraper",
            "method": "scrape_properties"
        },
        "pestana": {
            "name": "Pestana Leilões",
            "module": "app.scrapers.pestana_scraper",
            "class": "PestanaScraper",
            "method": "scrape_properties"
        },
        "pestana_leiloes": {
            "name": "Pestana Leilões",
            "module": "app.scrapers.pestana_scraper",
            "class": "PestanaScraper",
            "method": "scrape_properties"
        }
    }
    
    def __init__(self, use_quality_filter: bool = True):
        self.db = db
        if not isinstance(self.db, PostgresDatabase):
            logger.warning(f"Database is not PostgreSQL! Type: {type(self.db)}")
        self.quality_filter = QualityFilter(use_ai=True) if use_quality_filter else None
    
    def scrape_all_auctioneers(self, max_retries: int = 3) -> Dict[str, Any]:
        """
        Scrape ALL auctioneers from the database.
        
        Args:
            max_retries: Maximum number of retries per auctioneer on failure
        
        Returns:
            Dictionary with scraping results
        """
        results = {
            "started_at": datetime.now().isoformat(),
            "auctioneers_processed": 0,
            "auctioneers_success": 0,
            "auctioneers_failed": 0,
            "total_properties_scraped": 0,
            "properties_by_auctioneer": {},
            "errors": []
        }
        
        # Get all active auctioneers from database
        auctioneers = self.db.get_auctioneers()
        active_auctioneers = [a for a in auctioneers if a.is_active]
        
        logger.info(f"Starting scrape for {len(active_auctioneers)} active auctioneers")
        
        for auctioneer in active_auctioneers:
            try:
                # Update status to running
                if isinstance(self.db, PostgresDatabase):
                    self.db.update_auctioneer_scrape_status(auctioneer.id, "running")
                
                # Scrape this auctioneer
                scrape_result = self.scrape_auctioneer(auctioneer, max_retries=max_retries)
                
                # Update results
                results["auctioneers_processed"] += 1
                results["properties_by_auctioneer"][auctioneer.name] = scrape_result["properties_scraped"]
                results["total_properties_scraped"] += scrape_result["properties_scraped"]
                
                if scrape_result["success"]:
                    results["auctioneers_success"] += 1
                    # Update status to success and property count
                    if isinstance(self.db, PostgresDatabase):
                        property_count = self.db.get_auctioneer_property_count(auctioneer.id)
                        self.db.update_auctioneer_scrape_status(
                            auctioneer.id,
                            "success",
                            property_count=property_count
                        )
                else:
                    results["auctioneers_failed"] += 1
                    error_msg = f"{auctioneer.name}: {scrape_result.get('error', 'Unknown error')}"
                    results["errors"].append(error_msg)
                    # Update status to error
                    if isinstance(self.db, PostgresDatabase):
                        self.db.update_auctioneer_scrape_status(
                            auctioneer.id,
                            "error",
                            error=scrape_result.get('error', 'Unknown error')
                        )
                
                logger.info(
                    f"Completed {auctioneer.name}: "
                    f"{scrape_result['properties_scraped']} properties, "
                    f"status: {'success' if scrape_result['success'] else 'failed'}"
                )
                
                # Generate quality report for this auctioneer
                if scrape_result["success"] and scrape_result["properties_scraped"] > 0:
                    try:
                        report_service = get_quality_report_service()
                        quality_report = report_service.generate_report(auctioneer_name=auctioneer.name)
                        logger.info(
                            f"Quality report for {auctioneer.name}: "
                            f"{quality_report.get('with_photo_percentage', 0):.1f}% with photo, "
                            f"{quality_report.get('with_price_percentage', 0):.1f}% with price, "
                            f"{quality_report.get('with_description_percentage', 0):.1f}% with description"
                        )
                    except Exception as e:
                        logger.warning(f"Error generating quality report for {auctioneer.name}: {e}")
                
                # Small delay between auctioneers
                time.sleep(2)
                gc.collect()
                
            except Exception as e:
                logger.error(f"Unexpected error processing {auctioneer.name}: {e}")
                results["auctioneers_failed"] += 1
                results["errors"].append(f"{auctioneer.name}: Unexpected error - {str(e)}")
                if isinstance(self.db, PostgresDatabase):
                    self.db.update_auctioneer_scrape_status(auctioneer.id, "error", error=str(e))
        
        results["completed_at"] = datetime.now().isoformat()
        duration = (datetime.fromisoformat(results["completed_at"]) - 
                   datetime.fromisoformat(results["started_at"])).total_seconds()
        results["duration_seconds"] = duration
        
        # Generate overall quality report
        try:
            report_service = get_quality_report_service()
            quality_report = report_service.generate_report()
            results["quality_report"] = quality_report
        except Exception as e:
            logger.warning(f"Error generating overall quality report: {e}")
        
        logger.info(
            f"Scraping completed: {results['auctioneers_success']} success, "
            f"{results['auctioneers_failed']} failed, "
            f"{results['total_properties_scraped']} total properties"
        )
        
        return results
    
    def scrape_auctioneer(self, auctioneer: Auctioneer, max_retries: int = 3) -> Dict[str, Any]:
        """
        Scrape a single auctioneer.
        
        Args:
            auctioneer: Auctioneer to scrape
            max_retries: Maximum retries on failure
        
        Returns:
            Dictionary with scraping result
        """
        result = {
            "success": False,
            "properties_scraped": 0,
            "error": None
        }
        
        scraper = None
        properties = []
        
        for attempt in range(1, max_retries + 1):
            try:
                # Try to get specific scraper first
                scraper = self._get_scraper_for_auctioneer(auctioneer)
                
                if scraper is None:
                    result["error"] = f"No scraper available for {auctioneer.name}"
                    logger.warning(result["error"])
                    break
                
                # Scrape properties (NO LIMIT - scrape ALL pages)
                properties = []
                
                # PortalZuk uses scrape_listings with max_properties=None
                if auctioneer.name == "Portal Zuk" and hasattr(scraper, 'scrape_listings'):
                    scrape_result = scraper.scrape_listings(max_properties=None, state="all")
                    if isinstance(scrape_result, list):
                        properties = scrape_result
                    elif hasattr(scrape_result, 'complete_properties'):
                        properties = scrape_result.complete_properties
                # GenericScraper uses scrape_listings with max_pages - pass large number, it will stop when no more pages
                elif isinstance(scraper, GenericScraper) and hasattr(scraper, 'scrape_listings'):
                    # Pass a very large number - the scraper will stop when no next page is found
                    properties = scraper.scrape_listings(max_pages=1000)
                # Other scrapers use scrape_properties with max_properties
                elif hasattr(scraper, 'scrape_properties'):
                    method = getattr(scraper, 'scrape_properties')
                    # Some scrapers (like MegaLeiloes, Superbid) check "while result.total_complete < max_properties"
                    # which fails if max_properties is None. Pass a very large number instead to scrape all properties.
                    try:
                        # Pass a very large number (effectively unlimited) - scrapers will stop when no more pages found
                        scrape_result = method(max_properties=100000)
                    except TypeError:
                        # If that fails, try without parameters
                        scrape_result = method()
                    
                    # Handle different return types
                    if hasattr(scrape_result, 'complete_properties'):
                        properties = scrape_result.complete_properties
                    elif isinstance(scrape_result, list):
                        properties = scrape_result
                    else:
                        properties = []
                elif hasattr(scraper, 'scrape_listings'):
                    # Try scrape_listings with max_pages=None or large number
                    try:
                        scrape_result = scraper.scrape_listings(max_pages=None)
                    except TypeError:
                        try:
                            scrape_result = scraper.scrape_listings(max_pages=1000)
                        except TypeError:
                            scrape_result = scraper.scrape_listings()
                    
                    if isinstance(scrape_result, list):
                        properties = scrape_result
                    elif hasattr(scrape_result, 'complete_properties'):
                        properties = scrape_result.complete_properties
                else:
                    result["error"] = f"Scraper {type(scraper).__name__} has no recognized scrape method"
                    break
                
                # Ensure auctioneer_name is set on all properties
                for prop in properties:
                    if not prop.auctioneer_name:
                        prop.auctioneer_name = auctioneer.name
                    if not prop.auctioneer_id:
                        prop.auctioneer_id = auctioneer.id
                
                # Validate and save properties to database
                saved_count = 0
                rejected_count = 0
                for prop in properties:
                    try:
                        # Apply quality filter if enabled
                        if self.quality_filter:
                            filter_result = self.quality_filter.validate_and_clean(prop)
                            if not filter_result.is_valid:
                                rejected_count += 1
                                logger.warning(
                                    f"Property rejected: {prop.title[:50] if prop.title else 'unknown'} - "
                                    f"{filter_result.rejection_reason}"
                                )
                                continue
                            
                            # Log warnings and changes
                            if filter_result.warnings:
                                logger.info(f"Property warnings: {', '.join(filter_result.warnings)}")
                            if filter_result.changes_made:
                                logger.debug(f"Property changes: {', '.join(filter_result.changes_made)}")
                        
                        # Save to database
                        self.db.add_property(prop, upsert=True)
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"Error saving property {prop.id if prop.id else 'unknown'}: {e}")
                
                if rejected_count > 0:
                    logger.info(f"Rejected {rejected_count} properties for {auctioneer.name} due to quality filter")
                
                result["success"] = True
                result["properties_scraped"] = saved_count
                break
                
            except Exception as e:
                error_msg = f"Attempt {attempt}/{max_retries} failed: {str(e)}"
                logger.error(f"{auctioneer.name}: {error_msg}")
                result["error"] = error_msg
                
                if attempt < max_retries:
                    wait_time = attempt * 2  # Exponential backoff
                    logger.info(f"Retrying {auctioneer.name} in {wait_time} seconds...")
                    time.sleep(wait_time)
            finally:
                # Clean up scraper resources
                if scraper and hasattr(scraper, 'close_driver'):
                    try:
                        scraper.close_driver()
                    except:
                        pass
                del scraper
                del properties
                gc.collect()
        
        return result
    
    def _get_scraper_for_auctioneer(self, auctioneer: Auctioneer) -> Optional[BaseScraper]:
        """
        Get appropriate scraper for an auctioneer.
        Tries specific scrapers first, then falls back to generic scraper.
        """
        # Try specific scraper by ID or name
        auctioneer_id_lower = auctioneer.id.lower()
        auctioneer_name_lower = auctioneer.name.lower()
        
        # Check if we have a specific scraper
        for key, scraper_config in self.SPECIFIC_SCRAPERS.items():
            if key in auctioneer_id_lower or key in auctioneer_name_lower:
                try:
                    import importlib
                    module = importlib.import_module(scraper_config["module"])
                    scraper_class = getattr(module, scraper_config["class"])
                    return scraper_class()
                except Exception as e:
                    logger.warning(f"Failed to load specific scraper {key} for {auctioneer.name}: {e}")
                    break
        
        # Fall back to generic scraper
        return self._create_generic_scraper(auctioneer)
    
    def _create_generic_scraper(self, auctioneer: Auctioneer) -> Optional[GenericScraper]:
        """Create a generic scraper for an auctioneer."""
        if not auctioneer.website:
            logger.warning(f"No website URL for auctioneer {auctioneer.name}")
            return None
        
        try:
            # Parse the website URL to get base URL
            parsed = urlparse(auctioneer.website)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # Try to detect common listing URL patterns
            # Common patterns: /imoveis, /lotes, /leiloes, /busca, /propriedades
            listing_url_template = None
            common_paths = ["/imoveis", "/lotes", "/leiloes", "/busca", "/propriedades", "/ofertas"]
            
            # Try the base URL first
            if parsed.path in common_paths or not parsed.path or parsed.path == "/":
                for path in common_paths:
                    listing_url_template = f"{base_url}{path}?page={{page}}"
                    break
            
            if not listing_url_template:
                listing_url_template = f"{base_url}/imoveis?page={{page}}"
            
            # Create generic scraper config
            config = ScraperConfig(
                name=auctioneer.name,
                base_url=base_url,
                listings_url_template=listing_url_template
            )
            
            return GenericScraper(config, headless=True)
            
        except Exception as e:
            logger.error(f"Error creating generic scraper for {auctioneer.name}: {e}")
            return None
    


# Singleton instance
_universal_scraper_service: Optional[UniversalScraperService] = None


def get_universal_scraper_service() -> UniversalScraperService:
    """Get the singleton universal scraper service instance."""
    global _universal_scraper_service
    if _universal_scraper_service is None:
        _universal_scraper_service = UniversalScraperService()
    return _universal_scraper_service

