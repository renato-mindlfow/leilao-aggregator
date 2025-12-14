"""
Scraper for Superbid auction website.
https://www.superbid.net

Uses __NEXT_DATA__ JSON parsing for reliable data extraction.
"""
import logging
import re
import json
import time
import random
import html
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

import requests

from app.models.property import Property, PropertyCategory, AuctionType

logger = logging.getLogger(__name__)


@dataclass
class ScrapingResult:
    """Result of a scraping operation with complete and incomplete properties."""
    complete_properties: List[Property] = field(default_factory=list)
    incomplete_properties: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_scraped: int = 0
    total_complete: int = 0
    total_incomplete: int = 0


class SuperbidScraper:
    """Scraper for Superbid auction website using __NEXT_DATA__ JSON parsing."""
    
    BASE_URL = "https://www.superbid.net"
    CATEGORY_URL = "https://www.superbid.net/categorias/imoveis/imoveis-residenciais"
    
    # Required fields for a complete property
    REQUIRED_FIELDS = ['title', 'auctioneer_url', 'image_url', 'city', 'state', 'price']
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        
    @property
    def name(self) -> str:
        return "Superbid"
        
    def _delay(self, min_seconds: float = 1.0, max_seconds: float = 2.0):
        """Add a random delay between requests to be polite."""
        time.sleep(random.uniform(min_seconds, max_seconds))
        
    def _extract_next_data(self, html_content: str) -> Optional[Dict]:
        """Extract __NEXT_DATA__ JSON from HTML page."""
        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html_content,
            re.DOTALL
        )
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse __NEXT_DATA__: {e}")
        return None
        
    def _clean_text(self, text: str) -> str:
        """Clean text by fixing encoding issues and removing HTML."""
        if not text:
            return ""
        text = html.unescape(text)
        text = text.replace('Â²', '²').replace('Â', '').replace('Ã³', 'ó')
        text = text.replace('Ã£', 'ã').replace('Ã©', 'é').replace('Ã­', 'í')
        text = text.replace('Ãº', 'ú').replace('Ã§', 'ç').replace('Ã¡', 'á')
        text = text.replace('Ãª', 'ê').replace('Ã´', 'ô').replace('Ã', 'À')
        text = re.sub(r'<[^>]+>', ' ', text)
        text = ' '.join(text.split())
        return text.strip()
        
    def _extract_address_from_description(self, description: str) -> Optional[str]:
        """Extract full address from property description."""
        if not description:
            return None
        match = re.search(r'Localiza[çc][ãa]o:\s*([^<\n]+)', description, re.IGNORECASE)
        if match:
            return self._clean_text(match.group(1))
        return None
        
    def _extract_area_from_text(self, text: str) -> Optional[float]:
        """Extract area in m² from text."""
        if not text:
            return None
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', text, re.IGNORECASE)
        if match:
            area_str = match.group(1).replace(',', '.')
            try:
                return float(area_str)
            except ValueError:
                pass
        return None
        
    def _determine_category(self, title: str) -> PropertyCategory:
        """Determine property category from title."""
        title_lower = title.lower()
        if 'apartamento' in title_lower or 'apto' in title_lower:
            return PropertyCategory.APARTAMENTO
        elif 'casa' in title_lower or 'sobrado' in title_lower:
            return PropertyCategory.CASA
        elif 'terreno' in title_lower or 'lote' in title_lower:
            return PropertyCategory.TERRENO
        elif 'comercial' in title_lower or 'loja' in title_lower or 'sala' in title_lower:
            return PropertyCategory.COMERCIAL
        elif 'rural' in title_lower or 'fazenda' in title_lower or 'sítio' in title_lower:
            return PropertyCategory.RURAL
        elif 'galpão' in title_lower or 'galpao' in title_lower:
            return PropertyCategory.GALPAO
        return PropertyCategory.OUTRO
        
    def _parse_location_from_title(self, title: str) -> Tuple[str, str, str]:
        """Parse city, state, and neighborhood from title."""
        city = ""
        state = ""
        neighborhood = ""
        
        # Look for state code (2 letters after /)
        state_match = re.search(r'/([A-Z]{2})(?:\s|$|-)', title)
        if state_match:
            state = state_match.group(1)
            
        # Look for city - pattern: "City/STATE" at the end or before " - "
        # Try pattern: word(s) before /STATE
        city_match = re.search(r'([A-Za-zÀ-ÿ\s]+)/[A-Z]{2}(?:\s|$|-)', title)
        if city_match:
            city = city_match.group(1).strip()
            # Clean up - remove leading commas or spaces
            city = re.sub(r'^[,\s]+', '', city)
            # If city has multiple words, take only the last part (actual city name)
            if ',' in city:
                city = city.split(',')[-1].strip()
            
        # Look for neighborhood - usually after m² and before city
        neighborhood_match = re.search(r'm[²2],?\s*([^,/]+),\s*[A-Za-zÀ-ÿ\s]+/[A-Z]{2}', title)
        if neighborhood_match:
            neighborhood = neighborhood_match.group(1).strip()
            
        return city, state, neighborhood
        
    def _validate_property(self, prop_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate that a property has all required fields."""
        missing_fields = []
        
        for field_name in self.REQUIRED_FIELDS:
            value = prop_data.get(field_name)
            if value is None or value == "" or value == 0:
                missing_fields.append(field_name)
                
        return len(missing_fields) == 0, missing_fields
        
    def _verify_url(self, url: str) -> bool:
        """Verify that a URL is valid and returns 200."""
        try:
            response = self.session.head(url, allow_redirects=True, timeout=10)
            if response.status_code == 200:
                final_url = response.url
                return '/oferta/' in final_url
            return False
        except Exception as e:
            logger.warning(f"Failed to verify URL {url}: {e}")
            return False
            
    def get_property_ids_from_category(self, page: int = 1, page_size: int = 30) -> List[Dict]:
        """Get property IDs and basic info from category page."""
        url = f"{self.CATEGORY_URL}?searchType=opened&pageNumber={page}&pageSize={page_size}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = self._extract_next_data(response.text)
            if not data:
                logger.error("Failed to extract __NEXT_DATA__ from category page")
                return []
                
            offers_list = data.get('props', {}).get('pageProps', {}).get('offersList', {})
            offers = offers_list.get('offers', [])
            
            logger.info(f"Found {len(offers)} offers on page {page}")
            return offers
            
        except Exception as e:
            logger.error(f"Failed to get property IDs from category page {page}: {e}")
            return []
            
    def _create_slug(self, title: str) -> str:
        """Create URL slug from title."""
        import unicodedata
        slug = unicodedata.normalize('NFKD', title)
        slug = slug.encode('ascii', 'ignore').decode('ascii')
        slug = slug.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        slug = re.sub(r'-+', '-', slug)
        return slug
        
    def scrape_property_detail(self, offer_id: int, offer_data: Dict = None) -> Optional[Dict[str, Any]]:
        """Scrape detailed property information from individual property page."""
        base_urls_to_try = []
        
        if offer_data:
            title = offer_data.get('product', {}).get('shortDesc', '')
            if title:
                slug = self._create_slug(title)
                base_urls_to_try.append(f"{self.BASE_URL}/oferta/{slug}-{offer_id}")
        
        base_urls_to_try.append(f"{self.BASE_URL}/oferta/{offer_id}")
        
        for url in base_urls_to_try:
            try:
                self._delay(0.5, 1.0)
                response = self.session.get(url, allow_redirects=True, timeout=30)
                
                if response.status_code == 200 and '/oferta/' in response.url:
                    final_url = response.url
                    data = self._extract_next_data(response.text)
                    
                    if data:
                        return self._parse_property_from_next_data(data, final_url)
                        
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                continue
                
        logger.warning(f"Could not find property page for offer ID {offer_id}")
        return None
        
    def _parse_property_from_next_data(self, data: Dict, url: str) -> Optional[Dict[str, Any]]:
        """Parse property data from __NEXT_DATA__ JSON."""
        try:
            offer_details = data.get('props', {}).get('pageProps', {}).get('offerDetails', {})
            offers = offer_details.get('offers', [])
            
            if not offers:
                return None
                
            offer = offers[0]
            product = offer.get('product', {})
            auction = offer.get('auction', {})
            event_pipeline = auction.get('eventPipeline', {})
            stages = event_pipeline.get('stages', [])
            
            title = self._clean_text(product.get('shortDesc', ''))
            description = self._clean_text(offer.get('offerDescription', {}).get('offerDescription', ''))
            address = self._extract_address_from_description(description)
            
            city, state, neighborhood = self._parse_location_from_title(title)
            
            if not address:
                address = f"{neighborhood}, {city}/{state}" if neighborhood else f"{city}/{state}"
                
            gallery = product.get('galleryJson', [])
            image_url = ""
            if gallery:
                for img in gallery:
                    if img.get('highlight'):
                        image_url = img.get('link', '')
                        break
                if not image_url and gallery:
                    image_url = gallery[0].get('link', '')
                    
            first_auction_value = None
            second_auction_value = None
            
            if stages:
                if len(stages) >= 1:
                    first_auction_value = stages[0].get('initialBidValue')
                if len(stages) >= 2:
                    second_auction_value = stages[1].get('initialBidValue')
                    
            if not first_auction_value:
                first_auction_value = offer.get('price')
                
            area = self._extract_area_from_text(title) or self._extract_area_from_text(description)
            category = self._determine_category(title)
            is_occupied = 'ocupad' in title.lower() or 'ocupad' in description.lower()
            
            discount = None
            if first_auction_value and second_auction_value and first_auction_value > 0:
                discount = round((1 - second_auction_value / first_auction_value) * 100, 1)
                
            return {
                'id': str(offer.get('id')),
                'title': title,
                'description': description[:500] if description else title,
                'category': category,
                'auction_type': AuctionType.EXTRAJUDICIAL,
                'state': state,
                'city': city,
                'neighborhood': neighborhood,
                'address': address,
                'area': area,
                'price': first_auction_value,
                'first_auction_value': first_auction_value,
                'second_auction_value': second_auction_value,
                'discount_percentage': discount,
                'image_url': image_url,
                'auctioneer_url': url,
                'auctioneer_name': self.name,
                'is_occupied': is_occupied,
                'raw_data': offer,
            }
            
        except Exception as e:
            logger.error(f"Failed to parse property from __NEXT_DATA__: {e}")
            return None
            
    def scrape_properties(self, max_properties: int = 10, verify_urls: bool = True) -> ScrapingResult:
        """
        Scrape properties from Superbid.
        
        Args:
            max_properties: Maximum number of properties to scrape
            verify_urls: Whether to verify each URL works before adding
            
        Returns:
            ScrapingResult with complete and incomplete properties
        """
        result = ScrapingResult()
        seen_ids = set()
        
        page = 1
        while result.total_complete < max_properties:
            logger.info(f"Fetching category page {page}...")
            offers = self.get_property_ids_from_category(page=page)
            
            if not offers:
                logger.info("No more offers found")
                break
                
            for offer in offers:
                if result.total_complete >= max_properties:
                    break
                    
                offer_id = offer.get('id')
                if not offer_id or offer_id in seen_ids:
                    continue
                    
                seen_ids.add(offer_id)
                result.total_scraped += 1
                
                logger.info(f"Scraping property {offer_id}...")
                
                try:
                    prop_data = self.scrape_property_detail(offer_id, offer)
                    
                    if not prop_data:
                        result.errors.append(f"Failed to scrape property {offer_id}")
                        continue
                        
                    is_valid, missing_fields = self._validate_property(prop_data)
                    
                    if not is_valid:
                        logger.warning(f"Property {offer_id} is incomplete, missing: {missing_fields}")
                        prop_data['missing_fields'] = missing_fields
                        result.incomplete_properties.append(prop_data)
                        result.total_incomplete += 1
                        continue
                        
                    if verify_urls:
                        if not self._verify_url(prop_data['auctioneer_url']):
                            logger.warning(f"Property {offer_id} has invalid URL")
                            prop_data['missing_fields'] = ['invalid_url']
                            result.incomplete_properties.append(prop_data)
                            result.total_incomplete += 1
                            continue
                            
                    prop = Property(
                        id=f"superbid-{prop_data['id']}",
                        title=prop_data['title'],
                        description=prop_data['description'],
                        category=prop_data['category'],
                        auction_type=prop_data['auction_type'],
                        state=prop_data['state'],
                        city=prop_data['city'],
                        neighborhood=prop_data['neighborhood'],
                        address=prop_data['address'],
                        area_total=prop_data['area'],
                        evaluation_value=prop_data['first_auction_value'],
                        first_auction_value=prop_data['first_auction_value'],
                        second_auction_value=prop_data['second_auction_value'],
                        discount_percentage=prop_data['discount_percentage'],
                        image_url=prop_data['image_url'],
                        auctioneer_url=prop_data['auctioneer_url'],
                        auctioneer_name=self.name,
                        auctioneer_id="superbid",
                        source_url=prop_data['auctioneer_url'],
                        accepts_financing=False,
                        accepts_fgts=False,
                        accepts_installments=True,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                    )
                    
                    result.complete_properties.append(prop)
                    result.total_complete += 1
                    logger.info(f"Successfully scraped property {offer_id}: {prop_data['title'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"Error processing property {offer_id}: {e}")
                    result.errors.append(f"Error processing {offer_id}: {str(e)}")
                    
            page += 1
            self._delay(1.0, 2.0)
            
        logger.info(f"Scraping complete: {result.total_complete} complete, {result.total_incomplete} incomplete, {len(result.errors)} errors")
        return result


def scrape_superbid_properties(max_properties: int = 10) -> ScrapingResult:
    """Scrape properties from Superbid."""
    scraper = SuperbidScraper()
    return scraper.scrape_properties(max_properties=max_properties)
