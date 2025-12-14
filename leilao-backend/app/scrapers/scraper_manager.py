"""
Scraper Manager - Coordinates all auction website scrapers.
"""
import logging
import gc
import hashlib
import uuid
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.models.property import Property, PropertyCategory, AuctionType
from app.scrapers.base_scraper import BaseScraper
from app.services import db
from app.services.postgres_database import PostgresDatabase, normalize_url

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


def run_all_scrapers() -> Dict[str, Any]:
    """
    Executa todos os scrapers automaticamente sem limitadores.
    
    Importa todos os scrapers (portalzuk, superbid, megaleiloes, leilaovip, inovaleilao, pestana),
    executa cada scraper SEM LIMITADORES (max_properties=None),
    salva os resultados no banco PostgreSQL,
    e retorna um dicionário com total de imóveis coletados por scraper.
    
    Returns:
        Dict com estatísticas de cada scraper e total geral
    """
    from app.scrapers.portalzuk_scraper import PortalZukScraper
    from app.scrapers.superbid_scraper import SuperbidScraper
    from app.scrapers.megaleiloes_scraper import MegaleiloesScraper
    from app.scrapers.leilaovip_scraper import LeilaoVipScraper
    from app.scrapers.inovaleilao_scraper import InovaLeilaoScraper
    from app.scrapers.pestana_scraper import PestanaScraper
    
    results = {
        "started_at": datetime.now().isoformat(),
        "scrapers_processed": 0,
        "total_properties_collected": 0,
        "properties_by_scraper": {},
        "errors": [],
    }
    
    # Define scrapers with their configurations
    scrapers_config = [
        {"name": "Portal Zuk", "scraper": PortalZukScraper, "method": "scrape_listings", "kwargs": {"max_properties": None}},
        {"name": "Superbid", "scraper": SuperbidScraper, "method": "scrape_properties", "kwargs": {"max_properties": None}},
        {"name": "Mega Leilões", "scraper": MegaleiloesScraper, "method": "scrape_properties", "kwargs": {"max_properties": None}},
        {"name": "Leilão VIP", "scraper": LeilaoVipScraper, "method": "scrape_properties", "kwargs": {"max_properties": None}},
        {"name": "Inova Leilão", "scraper": InovaLeilaoScraper, "method": "scrape_properties", "kwargs": {"max_properties": None}},
        {"name": "Pestana Leilões", "scraper": PestanaScraper, "method": "scrape_properties", "kwargs": {"max_properties": None}},
    ]
    
    # Run scrapers SEQUENTIALLY to avoid OOM
    for config in scrapers_config:
        try:
            logger.info(f"Starting scraper: {config['name']}")
            scraper = config["scraper"]()
            method = getattr(scraper, config["method"])
            result = method(**config["kwargs"])
            
            # Handle different return types
            properties = []
            if hasattr(result, 'complete_properties'):
                # ScrapingResult object
                properties = result.complete_properties
            elif isinstance(result, list):
                # List of Property objects or Dict objects
                if result and isinstance(result[0], Property):
                    properties = result
                elif result and isinstance(result[0], dict):
                    # Convert dict to Property objects (PestanaScraper case)
                    properties = []
                    for prop_dict in result:
                        try:
                            # Convert category string to enum
                            category = None
                            if prop_dict.get('category'):
                                try:
                                    category = PropertyCategory(prop_dict['category'])
                                except ValueError:
                                    category = PropertyCategory.OUTRO
                            
                            # Convert auction_type string to enum
                            auction_type = None
                            if prop_dict.get('auction_type'):
                                try:
                                    auction_type = AuctionType(prop_dict['auction_type'])
                                except ValueError:
                                    auction_type = AuctionType.OUTROS
                            
                            # Generate ID if not present
                            prop_id = prop_dict.get('id')
                            if not prop_id:
                                source_url = prop_dict.get('source_url', '')
                                if source_url:
                                    normalized_url = normalize_url(source_url)
                                    prop_id = f"pestana-{hashlib.md5(normalized_url.encode()).hexdigest()[:16]}"
                                else:
                                    prop_id = f"pestana-{uuid.uuid4().hex[:16]}"
                            
                            prop = Property(
                                id=prop_id,
                                title=prop_dict.get('title', 'Imóvel em Leilão'),
                                address=prop_dict.get('address'),
                                city=prop_dict.get('city', 'Não informado'),
                                state=prop_dict.get('state', 'SP'),
                                neighborhood=prop_dict.get('neighborhood'),
                                category=category,
                                auction_type=auction_type,
                                evaluation_value=prop_dict.get('evaluation_value'),
                                minimum_bid=prop_dict.get('minimum_bid'),
                                first_auction_value=prop_dict.get('first_auction_value'),
                                second_auction_value=prop_dict.get('second_auction_value'),
                                discount_percentage=prop_dict.get('discount_percentage'),
                                area_total=prop_dict.get('area_total'),
                                bedrooms=prop_dict.get('bedrooms'),
                                bathrooms=prop_dict.get('bathrooms'),
                                parking_spaces=prop_dict.get('parking_spaces'),
                                image_url=prop_dict.get('image_url'),
                                property_url=prop_dict.get('source_url'),
                                source_url=prop_dict.get('source_url'),
                                auctioneer_name=config['name'],
                                auctioneer_id=prop_dict.get('auctioneer_id', 'pestana_leiloes'),
                                auctioneer_url=prop_dict.get('auctioneer_url', 'https://www.pestanaleiloes.com.br'),
                                created_at=datetime.utcnow(),
                                updated_at=datetime.utcnow(),
                            )
                            properties.append(prop)
                        except Exception as e:
                            logger.error(f"Error converting dict to Property in {config['name']}: {e}")
                            continue
            else:
                properties = []
            
            # Add properties to PostgreSQL database
            # Verify we're using PostgreSQL, not SQLite or in-memory
            if not isinstance(db, PostgresDatabase):
                logger.warning(f"Database is not PostgreSQL! Type: {type(db)}. Properties may not be saved to Supabase.")
            
            saved_count = 0
            error_count = 0
            
            for prop in properties:
                try:
                    # Ensure property has a valid ID (use MD5 hash of source_url if needed)
                    if not prop.id or prop.id.strip() == "":
                        if prop.source_url:
                            normalized_url = normalize_url(prop.source_url)
                            prop.id = f"{config['name'].lower().replace(' ', '_')}-{hashlib.md5(normalized_url.encode()).hexdigest()[:16]}"
                            logger.debug(f"Generated ID for property: {prop.id} from URL: {prop.source_url[:50]}")
                        else:
                            prop.id = f"{config['name'].lower().replace(' ', '_')}-{uuid.uuid4().hex[:16]}"
                            logger.warning(f"Property without source_url, generated random ID: {prop.id}")
                    
                    # Ensure source_url is set for deduplication
                    if not prop.source_url:
                        prop.source_url = prop.property_url or prop.auctioneer_url or ""
                    
                    # Set dedup_key for better deduplication
                    if prop.source_url:
                        prop.dedup_key = normalize_url(prop.source_url)
                    
                    # Set timestamps if not set
                    if not prop.created_at:
                        prop.created_at = datetime.utcnow()
                    if not prop.updated_at:
                        prop.updated_at = datetime.utcnow()
                    
                    # Save to PostgreSQL using db.add_property (which uses psycopg)
                    db.add_property(prop, upsert=True)
                    saved_count += 1
                    logger.debug(f"Saved property to PostgreSQL: {prop.id} - {prop.title[:50]}")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error saving property {prop.id if prop.id else 'unknown'} to PostgreSQL: {str(e)}")
                    logger.debug(f"Property details: title={prop.title[:50]}, source_url={prop.source_url[:100] if prop.source_url else 'N/A'}")
                    continue
            
            results["properties_by_scraper"][config["name"]] = saved_count
            results["total_properties_collected"] += saved_count
            results["scrapers_processed"] += 1
            
            if error_count > 0:
                results["errors"].append(f"{config['name']}: {error_count} properties failed to save")
            
            logger.info(f"Completed {config['name']}: {saved_count} properties saved to PostgreSQL, {error_count} errors")
            
            # Clean up to free memory
            del scraper
            del result
            del properties
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error in {config['name']}: {str(e)}")
            results["errors"].append(f"{config['name']}: {str(e)}")
            results["properties_by_scraper"][config["name"]] = 0
            results["scrapers_processed"] += 1
    
    results["completed_at"] = datetime.now().isoformat()
    results["duration_seconds"] = (datetime.fromisoformat(results["completed_at"]) - datetime.fromisoformat(results["started_at"])).total_seconds()
    
    # Verify database type and log final status
    if isinstance(db, PostgresDatabase):
        logger.info("All properties saved to PostgreSQL Supabase database")
        # PostgreSQL doesn't need save_to_disk() - it's already persisted
    else:
        logger.warning(f"Database is not PostgreSQL! Type: {type(db)}. Calling save_to_disk() as fallback.")
        try:
            db.save_to_disk()
        except AttributeError:
            logger.warning("Database does not have save_to_disk() method")
    
    logger.info(f"Scraping completed: {results['total_properties_collected']} total properties collected across {results['scrapers_processed']} scrapers")
    
    return results
