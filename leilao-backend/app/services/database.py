"""
In-memory database for the auction aggregator MVP.
Now with JSON persistence to survive restarts.
For production, this should be replaced with PostgreSQL.
"""

from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import uuid
import json
import os
import logging
from app.models.property import Property, PropertyCreate, PropertyFilter, PropertyCategory, AuctionType
from app.models.auctioneer import Auctioneer, AuctioneerCreate

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """
    Normalize a URL for deduplication purposes.
    - Lowercase scheme and netloc
    - Strip trailing slash from path
    - Remove tracking query params (utm_*)
    - Keep other query params that might identify the property
    """
    if not url:
        return ""
    url = url.strip()
    try:
        parsed = urlparse(url)
        
        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        
        # Strip trailing slash from path
        path = parsed.path.rstrip("/")
        
        # Remove tracking query params but keep others
        query_params = []
        for k, v in parse_qsl(parsed.query, keep_blank_values=True):
            if not k.lower().startswith("utm_"):
                query_params.append((k, v))
        query = urlencode(query_params, doseq=True)
        
        normalized = urlunparse((scheme, netloc, path, "", query, ""))
        return normalized
    except Exception:
        return url.lower().strip().rstrip("/")

# Persistence file paths
DATA_DIR = os.environ.get("DATA_DIR", "/tmp/leilohub_data")
PROPERTIES_FILE = os.path.join(DATA_DIR, "properties.json")
AUCTIONEERS_FILE = os.path.join(DATA_DIR, "auctioneers.json")


class InMemoryDatabase:
    def __init__(self):
        self.properties: Dict[str, Property] = {}
        self.auctioneers: Dict[str, Auctioneer] = {}
        # Index for O(1) deduplication lookups: normalized_source_url -> property_id
        self.properties_by_source: Dict[str, str] = {}
        
        # Try to load from persistence first
        if self._load_from_disk():
            logger.info(f"Loaded {len(self.properties)} properties and {len(self.auctioneers)} auctioneers from disk")
            # Rebuild the URL index after loading from disk
            self._rebuild_url_index()
        else:
            # Fall back to sample data if no persistence exists
            logger.info("No persistence found, initializing with sample data")
            self._initialize_sample_auctioneers()
            self._load_sample_properties()
    
    def _rebuild_url_index(self):
        """Rebuild the URL index from existing properties."""
        self.properties_by_source.clear()
        for prop_id, prop in self.properties.items():
            source_url = prop.source_url or prop.auctioneer_url or ""
            if source_url:
                normalized = normalize_url(source_url)
                # If there's a collision, keep the first one (oldest)
                if normalized not in self.properties_by_source:
                    self.properties_by_source[normalized] = prop_id
        logger.info(f"Rebuilt URL index with {len(self.properties_by_source)} unique URLs")
    
    def _initialize_sample_auctioneers(self):
        """Initialize with all auctioneers that have real data in the system."""
        now = datetime.utcnow()
        
        # Portal Zuk - 30 properties
        portal_zuk_id = "portal_zuk"
        self.auctioneers[portal_zuk_id] = Auctioneer(
            id=portal_zuk_id,
            name="Portal Zuk",
            website="https://www.portalzuk.com.br",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        # Superbid - 10 properties
        superbid_id = "superbid"
        self.auctioneers[superbid_id] = Auctioneer(
            id=superbid_id,
            name="Superbid",
            website="https://www.superbid.net",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        # Mega Leilões - 10 properties
        megaleiloes_id = "mega_leiloes"
        self.auctioneers[megaleiloes_id] = Auctioneer(
            id=megaleiloes_id,
            name="Mega Leiloes",
            website="https://www.megaleiloes.com.br",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        # Leilão VIP - 8 properties
        leilaovip_id = "leilao_vip"
        self.auctioneers[leilaovip_id] = Auctioneer(
            id=leilaovip_id,
            name="Leilao VIP",
            website="https://www.leilaovip.com.br",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        # Inova Leilão - 10 properties (Pernambuco/Alagoas regional auctioneer)
        inovaleilao_id = "inovaleilao"
        self.auctioneers[inovaleilao_id] = Auctioneer(
            id=inovaleilao_id,
            name="Inova Leilao",
            website="https://www.inovaleilao.com.br",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        # Pestana Leilões - 10 properties (major RS/SC/SP auctioneer)
        pestana_id = "pestana_leiloes"
        self.auctioneers[pestana_id] = Auctioneer(
            id=pestana_id,
            name="Pestana Leiloes",
            website="https://www.pestanaleiloes.com.br",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        # Silas Leiloeiro (S&A Leilões) - 10 properties (Rio de Janeiro auctioneer)
        silas_id = "silas_leiloeiro"
        self.auctioneers[silas_id] = Auctioneer(
            id=silas_id,
            name="Silas Leiloeiro",
            website="https://www.silasleiloeiro.lel.br",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        # Roberto Fernandes Leilões - 3 properties (Rio Grande do Norte auctioneer)
        roberto_id = "roberto_fernandes"
        self.auctioneers[roberto_id] = Auctioneer(
            id=roberto_id,
            name="Roberto Fernandes Leiloes",
            website="https://www.robertofernandesleiloes.com.br",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        # Mauricio Mariz Leilões - 1 property (Rio de Janeiro auctioneer)
        mauricio_id = "mauricio_mariz"
        self.auctioneers[mauricio_id] = Auctioneer(
            id=mauricio_id,
            name="Mauricio Mariz Leiloes",
            website="https://www.mauriciomarizleiloes.com.br",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    
    # Property methods
    def create_property(self, property_data: PropertyCreate) -> Property:
        from app.services.geocoding import get_geocoding_service
        
        property_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Generate deduplication key
        dedup_key = self._generate_dedup_key(property_data)
        
        # Get coordinates for the property
        geocoding = get_geocoding_service()
        coords = geocoding.geocode(property_data.city, property_data.state)
        latitude = coords[0] if coords else None
        longitude = coords[1] if coords else None
        
        # Get property data and exclude latitude/longitude to avoid duplicates
        prop_dict = property_data.model_dump()
        prop_dict.pop('latitude', None)
        prop_dict.pop('longitude', None)
        
        property_obj = Property(
            id=property_id,
            **prop_dict,
            created_at=now,
            updated_at=now,
            dedup_key=dedup_key,
            latitude=latitude,
            longitude=longitude,
        )
        
        self.properties[property_id] = property_obj
        
        # Update auctioneer property count
        if property_data.auctioneer_id in self.auctioneers:
            self.auctioneers[property_data.auctioneer_id].property_count += 1
        
        return property_obj
    
    def get_property(self, property_id: str) -> Optional[Property]:
        return self.properties.get(property_id)
    
    def get_properties(
        self,
        filters: Optional[PropertyFilter] = None,
        skip: int = 0,
        limit: int = 18,
    ) -> tuple[List[Property], int]:
        """Get properties with optional filtering and pagination."""
        properties = list(self.properties.values())
        
        if filters:
            # Filter by state
            if filters.state:
                properties = [p for p in properties if p.state.lower() == filters.state.lower()]
            
            # Filter by city
            if filters.city:
                properties = [p for p in properties if p.city.lower() == filters.city.lower()]
            
            # Filter by neighborhood
            if filters.neighborhood:
                properties = [p for p in properties if p.neighborhood and filters.neighborhood.lower() in p.neighborhood.lower()]
            
            # Filter by category
            if filters.category:
                properties = [p for p in properties if p.category == filters.category]
            
            # Filter by auction type
            if filters.auction_type:
                properties = [p for p in properties if p.auction_type == filters.auction_type]
            
            # Filter by value range
            if filters.min_value:
                properties = [p for p in properties if p.second_auction_value and p.second_auction_value >= filters.min_value]
            
            if filters.max_value:
                properties = [p for p in properties if p.second_auction_value and p.second_auction_value <= filters.max_value]
            
            # Filter by minimum discount
            if filters.min_discount:
                properties = [p for p in properties if p.discount_percentage and p.discount_percentage >= filters.min_discount]
            
            # Filter by auctioneer
            if filters.auctioneer_id:
                properties = [p for p in properties if p.auctioneer_id == filters.auctioneer_id]
            
            # Search term
            if filters.search_term:
                search_lower = filters.search_term.lower()
                properties = [
                    p for p in properties
                    if search_lower in p.title.lower()
                    or (p.description and search_lower in p.description.lower())
                    or (p.address and search_lower in p.address.lower())
                    or search_lower in p.city.lower()
                ]
            
            # Exclude duplicates unless explicitly requested
            if not filters.include_duplicates:
                properties = [p for p in properties if not p.is_duplicate]
        
        # Sort by discount percentage (highest first)
        properties.sort(key=lambda p: p.discount_percentage or 0, reverse=True)
        
        total = len(properties)
        paginated = properties[skip:skip + limit]
        
        return paginated, total
    
    def delete_property(self, property_id: str) -> bool:
        if property_id in self.properties:
            prop = self.properties[property_id]
            if prop.auctioneer_id in self.auctioneers:
                self.auctioneers[prop.auctioneer_id].property_count -= 1
            del self.properties[property_id]
            return True
        return False
    
    def add_property(self, prop: Property, auto_save: bool = False, upsert: bool = True) -> Property:
        """
        Add or update a Property object in the database.
        Used by scrapers that return Property objects.
        Deduplicates based on normalized source_url using O(1) index lookup.
        
        Args:
            prop: Property object to add
            auto_save: If True, save to disk after adding (use sparingly for batch operations)
            upsert: If True, update existing properties instead of skipping them
            
        Returns:
            The existing property (updated if upsert=True), or the newly added property
        """
        # Get the source URL for deduplication
        source_url = prop.source_url or prop.auctioneer_url or ""
        normalized = normalize_url(source_url)
        
        # O(1) lookup using the URL index
        if normalized and normalized in self.properties_by_source:
            existing_id = self.properties_by_source[normalized]
            existing = self.properties.get(existing_id)
            if existing:
                if upsert:
                    # Update existing property with new data
                    self._update_property_from_scraper(existing, prop)
                    logger.debug(f"Updated existing property: {normalized} (id: {existing_id})")
                else:
                    logger.debug(f"Duplicate detected (skip): {normalized} already exists as {existing_id}")
                return existing
        
        # Set last_seen_at for new properties
        prop.last_seen_at = datetime.utcnow()
        prop.is_active = True
        
        # Add to database
        self.properties[prop.id] = prop
        
        # Update the URL index
        if normalized:
            self.properties_by_source[normalized] = prop.id
        
        # Update auctioneer property count
        if prop.auctioneer_id and prop.auctioneer_id in self.auctioneers:
            self.auctioneers[prop.auctioneer_id].property_count += 1
        
        # Auto-save if requested
        if auto_save:
            self.save_to_disk()
        
        return prop
    
    def _update_property_from_scraper(self, existing: Property, new_prop: Property) -> None:
        """
        Update an existing property with data from a new scraper run.
        Tracks value changes and updates last_seen_at.
        """
        now = datetime.utcnow()
        
        # Track value changes
        value_changed = False
        if new_prop.first_auction_value and existing.first_auction_value != new_prop.first_auction_value:
            existing.previous_first_auction_value = existing.first_auction_value
            existing.first_auction_value = new_prop.first_auction_value
            value_changed = True
            logger.info(f"Property {existing.id}: first_auction_value changed from {existing.previous_first_auction_value} to {new_prop.first_auction_value}")
        
        if new_prop.second_auction_value and existing.second_auction_value != new_prop.second_auction_value:
            existing.previous_second_auction_value = existing.second_auction_value
            existing.second_auction_value = new_prop.second_auction_value
            value_changed = True
            logger.info(f"Property {existing.id}: second_auction_value changed from {existing.previous_second_auction_value} to {new_prop.second_auction_value}")
        
        if value_changed:
            existing.value_changed_at = now
        
        # Update other fields that might have changed
        if new_prop.first_auction_date:
            existing.first_auction_date = new_prop.first_auction_date
        if new_prop.second_auction_date:
            existing.second_auction_date = new_prop.second_auction_date
        if new_prop.discount_percentage:
            existing.discount_percentage = new_prop.discount_percentage
        if new_prop.image_url:
            existing.image_url = new_prop.image_url
        if new_prop.evaluation_value:
            existing.evaluation_value = new_prop.evaluation_value
        
        # Update lifecycle fields
        existing.last_seen_at = now
        existing.updated_at = now
        existing.is_active = True
        
        # If property was previously deactivated, reactivate it
        if existing.deactivated_at:
            logger.info(f"Property {existing.id} reactivated (was deactivated at {existing.deactivated_at})")
            existing.deactivated_at = None
    
    def mark_inactive_properties(self, auctioneer_id: str, seen_urls: set, scrape_time: datetime = None) -> dict:
        """
        Mark properties as inactive if they weren't seen in the latest scraper run.
        This handles properties that have been removed from the auctioneer's site
        (e.g., auction passed, suspended, sold, etc.)
        
        Args:
            auctioneer_id: The auctioneer whose properties to check
            seen_urls: Set of normalized source_urls that were seen in this scraper run
            scrape_time: Time of the scraper run (defaults to now)
            
        Returns:
            dict with statistics about deactivated properties
        """
        if scrape_time is None:
            scrape_time = datetime.utcnow()
        
        deactivated = 0
        already_inactive = 0
        
        for prop in self.properties.values():
            if prop.auctioneer_id != auctioneer_id:
                continue
            if prop.is_duplicate:
                continue
            
            source_url = prop.source_url or prop.auctioneer_url or ""
            normalized = normalize_url(source_url)
            
            if normalized not in seen_urls:
                if prop.is_active:
                    prop.is_active = False
                    prop.deactivated_at = scrape_time
                    prop.updated_at = scrape_time
                    deactivated += 1
                    logger.info(f"Property {prop.id} marked as inactive (not seen in scraper run)")
                else:
                    already_inactive += 1
        
        logger.info(f"Marked {deactivated} properties as inactive for auctioneer {auctioneer_id}")
        
        return {
            "auctioneer_id": auctioneer_id,
            "deactivated": deactivated,
            "already_inactive": already_inactive,
            "scrape_time": scrape_time.isoformat(),
        }
    
    def _generate_dedup_key(self, property_data: PropertyCreate) -> str:
        """Generate a deduplication key based on address and city."""
        address = (property_data.address or "").lower().strip()
        city = property_data.city.lower().strip()
        state = property_data.state.lower().strip()
        return f"{address}|{city}|{state}"
    
    def cleanup_duplicates(self) -> dict:
        """
        Clean up duplicate properties in the database.
        Groups properties by normalized (auctioneer_id, source_url) key,
        keeps the canonical record (most complete data), and marks others as duplicates.
        
        Returns:
            dict with cleanup statistics
        """
        from collections import defaultdict
        
        # Group properties by normalized dedup key
        groups = defaultdict(list)
        for prop in self.properties.values():
            source_url = prop.source_url or prop.auctioneer_url or ""
            normalized = normalize_url(source_url)
            key = f"{prop.auctioneer_id}:{normalized}"
            groups[key].append(prop)
        
        duplicates_found = 0
        duplicates_marked = 0
        
        for key, props in groups.items():
            if len(props) <= 1:
                continue
            
            duplicates_found += len(props) - 1
            
            # Choose canonical record: prefer one with more complete data
            def completeness_score(p):
                score = 0
                if p.area_total:
                    score += 1
                if p.latitude and p.longitude:
                    score += 1
                if p.image_url:
                    score += 1
                if p.evaluation_value:
                    score += 1
                if p.first_auction_date:
                    score += 1
                if p.description:
                    score += 1
                return score
            
            # Sort by completeness (descending), then by created_at (ascending, keep oldest)
            sorted_props = sorted(props, key=lambda p: (-completeness_score(p), p.created_at or datetime.utcnow()))
            canonical = sorted_props[0]
            
            # Mark others as duplicates
            for p in sorted_props[1:]:
                if not p.is_duplicate:
                    p.is_duplicate = True
                    p.original_id = canonical.id
                    duplicates_marked += 1
        
        # Rebuild the URL index to only include canonical records
        self._rebuild_url_index()
        
        # Save changes to disk
        self.save_to_disk()
        
        logger.info(f"Cleanup complete: found {duplicates_found} duplicates, marked {duplicates_marked} as duplicates")
        
        return {
            "duplicates_found": duplicates_found,
            "duplicates_marked": duplicates_marked,
            "total_properties": len(self.properties),
            "unique_properties": len([p for p in self.properties.values() if not p.is_duplicate]),
        }
    
    def reclassify_properties(self) -> dict:
        """
        Reclassify properties based on title keywords.
        Fixes miscategorized properties where title clearly indicates a different category.
        
        Returns:
            dict with reclassification statistics
        """
        reclassified = 0
        
        for prop in self.properties.values():
            if prop.is_duplicate:
                continue
            
            title_lower = prop.title.lower() if prop.title else ""
            current_category = prop.category
            
            # Infer category from title using word boundaries
            inferred_category = None
            
            # Check for Casa keywords in title (highest priority for title-based inference)
            casa_keywords = ['casa', 'sobrado', 'residência', 'residencia', 'chácara', 'chacara', 'sítio', 'sitio']
            for keyword in casa_keywords:
                if keyword in title_lower:
                    # Make sure it's not part of another word (e.g., "casal")
                    import re
                    if re.search(rf'\b{keyword}\b', title_lower):
                        inferred_category = PropertyCategory.CASA
                        break
            
            # Check for Apartamento keywords in title
            if not inferred_category:
                apto_keywords = ['apartamento', 'apto', 'flat', 'cobertura', 'kitnet', 'loft', 'studio']
                for keyword in apto_keywords:
                    if keyword in title_lower:
                        import re
                        if re.search(rf'\b{keyword}\b', title_lower):
                            inferred_category = PropertyCategory.APARTAMENTO
                            break
            
            # Check for Terreno keywords in title
            if not inferred_category:
                terreno_keywords = ['terreno', 'lote', 'gleba']
                for keyword in terreno_keywords:
                    if keyword in title_lower:
                        import re
                        if re.search(rf'\b{keyword}\b', title_lower):
                            inferred_category = PropertyCategory.TERRENO
                            break
            
            # Check for Comercial keywords in title
            if not inferred_category:
                comercial_keywords = ['comercial', 'loja', 'sala comercial', 'galpão', 'galpao', 'escritório', 'escritorio', 'prédio comercial', 'predio comercial']
                for keyword in comercial_keywords:
                    if keyword in title_lower:
                        import re
                        if re.search(rf'\b{keyword}\b', title_lower):
                            inferred_category = PropertyCategory.COMERCIAL
                            break
            
            # If we inferred a category and it differs from current, update it
            if inferred_category and current_category != inferred_category:
                logger.info(f"Reclassifying property {prop.id}: {current_category} -> {inferred_category} (title: {prop.title[:50]}...)")
                prop.category = inferred_category
                reclassified += 1
        
        # Save changes to disk
        self.save_to_disk()
        
        logger.info(f"Reclassification complete: {reclassified} properties reclassified")
        
        return {
            "reclassified": reclassified,
            "total_properties": len(self.properties),
        }
    
    # Auctioneer methods
    def create_auctioneer(self, auctioneer_data: AuctioneerCreate) -> Auctioneer:
        auctioneer_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        auctioneer = Auctioneer(
            id=auctioneer_id,
            **auctioneer_data.model_dump(),
            created_at=now,
            updated_at=now,
        )
        
        self.auctioneers[auctioneer_id] = auctioneer
        return auctioneer
    
    def get_auctioneer(self, auctioneer_id: str) -> Optional[Auctioneer]:
        return self.auctioneers.get(auctioneer_id)
    
    def get_auctioneers(self) -> List[Auctioneer]:
        return list(self.auctioneers.values())
    
    def get_auctioneer_by_website(self, website: str) -> Optional[Auctioneer]:
        for auctioneer in self.auctioneers.values():
            if auctioneer.website == website:
                return auctioneer
        return None
    
    def update_auctioneer_scrape_status(
        self,
        auctioneer_id: str,
        status: str,
        error: Optional[str] = None
    ):
        if auctioneer_id in self.auctioneers:
            self.auctioneers[auctioneer_id].scrape_status = status
            self.auctioneers[auctioneer_id].scrape_error = error
            self.auctioneers[auctioneer_id].last_scrape = datetime.utcnow()
            self.auctioneers[auctioneer_id].updated_at = datetime.utcnow()
    
    # Statistics
    def get_stats(self) -> dict:
        properties = list(self.properties.values())
        unique_properties = [p for p in properties if not p.is_duplicate]
        
        # Count by category
        category_counts = {}
        for cat in PropertyCategory:
            count = len([p for p in unique_properties if p.category == cat])
            if count > 0:
                category_counts[cat.value] = count
        
        # Count by state
        state_counts = {}
        for p in unique_properties:
            state_counts[p.state] = state_counts.get(p.state, 0) + 1
        
        return {
            "total_properties": len(properties),
            "unique_properties": len(unique_properties),
            "duplicate_properties": len(properties) - len(unique_properties),
            "total_auctioneers": len(self.auctioneers),
            "active_auctioneers": len([a for a in self.auctioneers.values() if a.is_active]),
            "category_counts": category_counts,
            "state_counts": dict(sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        }


    def _load_sample_properties(self):
        """Load real properties from Portal Zuk."""
        from app.services.real_data import get_real_properties
        from app.services.ai_deduplication import get_deduplication_service
        
        # Generate real properties from Portal Zuk
        real_properties = get_real_properties()
        
        # Add properties directly to database (they are already Property objects)
        for prop in real_properties:
            self.properties[prop.id] = prop
        
        # Run AI-based deduplication
        dedup_service = get_deduplication_service()
        property_list = list(self.properties.values())
        unique_props, duplicate_props = dedup_service.deduplicate_properties(property_list)
        
        # Mark duplicates in the database
        duplicate_ids = {p.id for p in duplicate_props}
        for prop_id, prop in self.properties.items():
            if prop_id in duplicate_ids:
                prop.is_duplicate = True

    def _load_from_disk(self) -> bool:
        """
        Load properties and auctioneers from JSON files on disk.
        Returns True if data was loaded successfully, False otherwise.
        """
        try:
            if not os.path.exists(PROPERTIES_FILE) or not os.path.exists(AUCTIONEERS_FILE):
                return False
            
            # Load auctioneers
            with open(AUCTIONEERS_FILE, 'r', encoding='utf-8') as f:
                auctioneers_data = json.load(f)
            
            for auc_data in auctioneers_data:
                auc = Auctioneer(
                    id=auc_data['id'],
                    name=auc_data['name'],
                    website=auc_data.get('website'),
                    is_active=auc_data.get('is_active', True),
                    property_count=auc_data.get('property_count', 0),
                    last_scrape=datetime.fromisoformat(auc_data['last_scrape']) if auc_data.get('last_scrape') else None,
                    created_at=datetime.fromisoformat(auc_data['created_at']) if auc_data.get('created_at') else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(auc_data['updated_at']) if auc_data.get('updated_at') else datetime.utcnow(),
                )
                self.auctioneers[auc.id] = auc
            
            # Load properties
            with open(PROPERTIES_FILE, 'r', encoding='utf-8') as f:
                properties_data = json.load(f)
            
            for prop_data in properties_data:
                # Convert category and auction_type strings to enums
                category = None
                if prop_data.get('category'):
                    try:
                        category = PropertyCategory(prop_data['category'])
                    except ValueError:
                        category = PropertyCategory.OUTRO
                
                auction_type = None
                if prop_data.get('auction_type'):
                    try:
                        auction_type = AuctionType(prop_data['auction_type'])
                    except ValueError:
                        auction_type = AuctionType.OUTROS
                
                prop = Property(
                    id=prop_data['id'],
                    title=prop_data.get('title', ''),
                    address=prop_data.get('address'),
                    city=prop_data.get('city', ''),
                    state=prop_data.get('state', ''),
                    neighborhood=prop_data.get('neighborhood'),
                    description=prop_data.get('description'),
                    category=category,
                    auction_type=auction_type,
                    evaluation_value=prop_data.get('evaluation_value'),
                    first_auction_value=prop_data.get('first_auction_value'),
                    second_auction_value=prop_data.get('second_auction_value'),
                    discount_percentage=prop_data.get('discount_percentage'),
                    area_total=prop_data.get('area_total'),
                    area_privativa=prop_data.get('area_privativa'),
                    first_auction_date=datetime.fromisoformat(prop_data['first_auction_date']) if prop_data.get('first_auction_date') else None,
                    second_auction_date=datetime.fromisoformat(prop_data['second_auction_date']) if prop_data.get('second_auction_date') else None,
                    image_url=prop_data.get('image_url'),
                    source_url=prop_data.get('source_url', ''),
                    auctioneer_id=prop_data.get('auctioneer_id', ''),
                    auctioneer_name=prop_data.get('auctioneer_name'),
                    auctioneer_url=prop_data.get('auctioneer_url'),
                    latitude=prop_data.get('latitude'),
                    longitude=prop_data.get('longitude'),
                    accepts_financing=prop_data.get('accepts_financing'),
                    accepts_fgts=prop_data.get('accepts_fgts'),
                    accepts_installments=prop_data.get('accepts_installments'),
                    occupation_status=prop_data.get('occupation_status'),
                    pending_debts=prop_data.get('pending_debts'),
                    created_at=datetime.fromisoformat(prop_data['created_at']) if prop_data.get('created_at') else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(prop_data['updated_at']) if prop_data.get('updated_at') else datetime.utcnow(),
                    is_duplicate=prop_data.get('is_duplicate', False),
                    dedup_key=prop_data.get('dedup_key'),
                    original_id=prop_data.get('original_id'),
                    # Lifecycle fields
                    is_active=prop_data.get('is_active', True),
                    last_seen_at=datetime.fromisoformat(prop_data['last_seen_at']) if prop_data.get('last_seen_at') else None,
                    deactivated_at=datetime.fromisoformat(prop_data['deactivated_at']) if prop_data.get('deactivated_at') else None,
                    # Change tracking fields
                    value_changed_at=datetime.fromisoformat(prop_data['value_changed_at']) if prop_data.get('value_changed_at') else None,
                    previous_first_auction_value=prop_data.get('previous_first_auction_value'),
                    previous_second_auction_value=prop_data.get('previous_second_auction_value'),
                )
                self.properties[prop.id] = prop
            
            return True
        except Exception as e:
            logger.error(f"Error loading from disk: {e}")
            return False

    def save_to_disk(self) -> bool:
        """
        Save properties and auctioneers to JSON files on disk.
        Returns True if saved successfully, False otherwise.
        """
        try:
            # Ensure data directory exists
            os.makedirs(DATA_DIR, exist_ok=True)
            
            # Save auctioneers
            auctioneers_data = []
            for auc in self.auctioneers.values():
                auctioneers_data.append({
                    'id': auc.id,
                    'name': auc.name,
                    'website': auc.website,
                    'is_active': auc.is_active,
                    'property_count': auc.property_count,
                    'last_scrape': auc.last_scrape.isoformat() if auc.last_scrape else None,
                    'created_at': auc.created_at.isoformat() if auc.created_at else None,
                    'updated_at': auc.updated_at.isoformat() if auc.updated_at else None,
                })
            
            with open(AUCTIONEERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(auctioneers_data, f, ensure_ascii=False, indent=2)
            
            # Save properties
            properties_data = []
            for prop in self.properties.values():
                properties_data.append({
                    'id': prop.id,
                    'title': prop.title,
                    'address': prop.address,
                    'city': prop.city,
                    'state': prop.state,
                    'neighborhood': prop.neighborhood,
                    'description': prop.description,
                    'category': prop.category.value if prop.category else None,
                    'auction_type': prop.auction_type.value if prop.auction_type else None,
                    'evaluation_value': prop.evaluation_value,
                    'first_auction_value': prop.first_auction_value,
                    'second_auction_value': prop.second_auction_value,
                    'discount_percentage': prop.discount_percentage,
                    'area_total': prop.area_total,
                    'area_privativa': prop.area_privativa,
                    'first_auction_date': prop.first_auction_date.isoformat() if prop.first_auction_date else None,
                    'second_auction_date': prop.second_auction_date.isoformat() if prop.second_auction_date else None,
                    'image_url': prop.image_url,
                    'source_url': prop.source_url,
                    'auctioneer_id': prop.auctioneer_id,
                    'auctioneer_name': prop.auctioneer_name,
                    'auctioneer_url': prop.auctioneer_url,
                    'latitude': prop.latitude,
                    'longitude': prop.longitude,
                    'accepts_financing': prop.accepts_financing,
                    'accepts_fgts': prop.accepts_fgts,
                    'accepts_installments': prop.accepts_installments,
                    'occupation_status': prop.occupation_status,
                    'pending_debts': prop.pending_debts,
                    'created_at': prop.created_at.isoformat() if prop.created_at else None,
                    'updated_at': prop.updated_at.isoformat() if prop.updated_at else None,
                    'is_duplicate': prop.is_duplicate,
                    'dedup_key': prop.dedup_key,
                    'original_id': prop.original_id,
                    # Lifecycle fields
                    'is_active': getattr(prop, 'is_active', True),
                    'last_seen_at': prop.last_seen_at.isoformat() if getattr(prop, 'last_seen_at', None) else None,
                    'deactivated_at': prop.deactivated_at.isoformat() if getattr(prop, 'deactivated_at', None) else None,
                    # Change tracking fields
                    'value_changed_at': prop.value_changed_at.isoformat() if getattr(prop, 'value_changed_at', None) else None,
                    'previous_first_auction_value': getattr(prop, 'previous_first_auction_value', None),
                    'previous_second_auction_value': getattr(prop, 'previous_second_auction_value', None),
                })
            
            with open(PROPERTIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(properties_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(self.properties)} properties and {len(self.auctioneers)} auctioneers to disk")
            return True
        except Exception as e:
            logger.error(f"Error saving to disk: {e}")
            return False


# Global database instance
db = InMemoryDatabase()
