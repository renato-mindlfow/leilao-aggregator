"""
Scraper for Leilão VIP auction website.
https://www.leilaovip.com.br

Uses requests + BeautifulSoup for HTML parsing.
"""
import logging
import re
import time
import random
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

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


class LeilaoVipScraper:
    """Scraper for Leilão VIP auction website."""
    
    BASE_URL = "https://www.leilaovip.com.br"
    SEARCH_URL = "https://www.leilaovip.com.br/pesquisa"
    
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
        return "Leilao VIP"
        
    def _delay(self, min_seconds: float = 1.0, max_seconds: float = 2.0):
        """Add a random delay between requests to be polite."""
        time.sleep(random.uniform(min_seconds, max_seconds))
        
    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace."""
        if not text:
            return ""
        text = ' '.join(text.split())
        return text.strip()
        
    @staticmethod
    def _parse_brl(price_str: str) -> Optional[float]:
        """Parse Brazilian Real format to float.
        
        Examples:
            '232.837,09' -> 232837.09
            '5.000,00' -> 5000.00
            'R$ 1.234,56' -> 1234.56
        """
        try:
            cleaned = re.sub(r'[R$\s]', '', price_str)
            cleaned = cleaned.replace('.', '').replace(',', '.')
            return float(cleaned)
        except (ValueError, AttributeError):
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
        elif 'comercial' in title_lower or 'loja' in title_lower or 'sala' in title_lower or 'galpão' in title_lower:
            return PropertyCategory.COMERCIAL
        elif 'rural' in title_lower or 'fazenda' in title_lower or 'sítio' in title_lower or 'gleba' in title_lower:
            return PropertyCategory.RURAL
        elif 'prédio' in title_lower or 'predio' in title_lower:
            return PropertyCategory.COMERCIAL
        return PropertyCategory.OUTRO
        
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
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to verify URL {url}: {e}")
            return False
            
    def get_property_links_from_homepage(self) -> List[str]:
        """Get property links from homepage."""
        try:
            response = self.session.get(self.BASE_URL, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '/evento/anuncio/' in href:
                    if href.startswith('/'):
                        href = f"{self.BASE_URL}{href}"
                    if href not in links:
                        links.append(href)
                        
            logger.info(f"Found {len(links)} property links on homepage")
            return links
            
        except Exception as e:
            logger.error(f"Failed to get property links from homepage: {e}")
            return []
            
    def get_property_links_from_agenda(self, segment: str = "Imóveis") -> List[str]:
        """Get property links from agenda page."""
        try:
            url = f"{self.BASE_URL}/agenda"
            params = {'segmento': segment}
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '/evento/anuncio/' in href:
                    if href.startswith('/'):
                        href = f"{self.BASE_URL}{href}"
                    if href not in links:
                        links.append(href)
                        
            logger.info(f"Found {len(links)} property links on agenda page")
            return links
            
        except Exception as e:
            logger.error(f"Failed to get property links from agenda page: {e}")
            return []
            
    def scrape_property_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed property information from individual property page."""
        try:
            self._delay(0.5, 1.0)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title from h1
            h1 = soup.find('h1')
            if not h1:
                logger.warning(f"No title found for {url}")
                return None
                
            title_text = self._clean_text(h1.get_text())
            
            # Parse title - format: "LOTE X: Casa com 204,75 m² - Paulicéia PIRACICABA SP"
            # where Paulicéia is neighborhood and PIRACICABA is city
            title = title_text
            city = ""
            state = ""
            neighborhood = ""
            
            # Try to extract city and state from page text (more reliable)
            page_text = soup.get_text()
            city_match = re.search(r'Cidade:\s*([^\n<]+)', page_text, re.IGNORECASE)
            if city_match:
                city = self._clean_text(city_match.group(1))
                
            state_match = re.search(r'Estado:\s*([A-Z]{2})', page_text, re.IGNORECASE)
            if state_match:
                state = state_match.group(1).upper()
                
            # If city/state not found in page text, try to extract from title
            if not city or not state:
                # Pattern: "... CITY STATE" at the end where CITY is all uppercase
                location_match = re.search(r'([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇa-zàáâãéêíóôõúç]+)\s+([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s]+)\s+([A-Z]{2})\s*$', title_text)
                if location_match:
                    neighborhood = location_match.group(1).strip()
                    if not city:
                        city = location_match.group(2).strip()
                    if not state:
                        state = location_match.group(3).strip()
                    # Remove location from title
                    title = title_text[:location_match.start()].strip()
                else:
                    # Fallback: try simpler pattern "CITY STATE" at the end
                    simple_match = re.search(r'([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇa-zàáâãéêíóôõúç\s]+)\s+([A-Z]{2})\s*$', title_text)
                    if simple_match:
                        if not city:
                            city = simple_match.group(1).strip()
                        if not state:
                            state = simple_match.group(2).strip()
                        title = title_text[:simple_match.start()].strip()
                
            # Clean up title - remove "LOTE X:" prefix
            title = re.sub(r'^LOTE\s*\d+:\s*', '', title, flags=re.IGNORECASE)
            
            # Extract image URL
            image_url = ""
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src', '')
                if 'armazupleilaovipprd.blob.core.windows.net' in src or 'armazviplprd.blob.core.windows.net' in src:
                    image_url = src
                    break
                    
            # Extract prices from the description section
            first_auction_value = None
            second_auction_value = None
            
            # Strategy 1: Look for "1º Leilão" followed by date and price on next lines
            # The format is: "1º Leilão\n12/12/2025 16:00\nR$ 883.813,48"
            first_match = re.search(r'1[ºo°]\s*Leil[aã]o\s*(\d{2}/\d{2}/\d{4}\s*\d{2}:\d{2})?\s*R\$\s*([\d.,]+)', page_text, re.IGNORECASE)
            if first_match:
                first_auction_value = self._parse_brl(first_match.group(2))
                
            # Strategy 2: Look for "Lance Inicial: R$ XXX"
            if not first_auction_value:
                lance_match = re.search(r'Lance\s*Inicial[:\s]*R\$\s*([\d.,]+)', page_text, re.IGNORECASE)
                if lance_match:
                    first_auction_value = self._parse_brl(lance_match.group(1))
                
            # Pattern for 2nd auction: "2º Leilão\n15/12/2025 16:00\nR$ 499.095,01"
            second_match = re.search(r'2[ºo°]\s*Leil[aã]o\s*(\d{2}/\d{2}/\d{4}\s*\d{2}:\d{2})?\s*R\$\s*([\d.,]+)', page_text, re.IGNORECASE)
            if second_match:
                second_auction_value = self._parse_brl(second_match.group(2))
                
            # If no first auction value, try to find any large price (> 10000)
            if not first_auction_value:
                all_prices = re.findall(r'R\$\s*([\d.,]+)', page_text)
                for price_str in all_prices:
                    price = self._parse_brl(price_str)
                    if price and price > 10000:
                        first_auction_value = price
                        break
                    
            # Extract address from description
            address = ""
            address_match = re.search(r'Endere[çc]o:\s*([^\n<]+)', page_text, re.IGNORECASE)
            if address_match:
                address = self._clean_text(address_match.group(1))
                
            # Extract area
            area = self._extract_area_from_text(title_text) or self._extract_area_from_text(page_text)
            
            # Determine category
            category = self._determine_category(title)
            
            # Determine auction type
            auction_type = AuctionType.EXTRAJUDICIAL
            if 'judicial' in page_text.lower() and 'extrajudicial' not in page_text.lower():
                auction_type = AuctionType.JUDICIAL
                
            # Check if occupied
            is_occupied = 'ocupad' in page_text.lower()
            
            # Calculate discount
            discount = None
            if first_auction_value and second_auction_value and first_auction_value > 0:
                discount = round((1 - second_auction_value / first_auction_value) * 100, 1)
                
            # Extract property ID from URL
            prop_id = url.split('/')[-1]
            
            return {
                'id': prop_id,
                'title': title if title else title_text,
                'description': title_text[:500],
                'category': category,
                'auction_type': auction_type,
                'state': state,
                'city': city.title() if city else "",
                'neighborhood': neighborhood.title() if neighborhood else "",
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
            }
            
        except Exception as e:
            logger.error(f"Failed to scrape property detail from {url}: {e}")
            return None
            
    def scrape_properties(self, max_properties: int = None, verify_urls: bool = True) -> ScrapingResult:
        """
        Scrape properties from Leilão VIP.
        
        Args:
            max_properties: Maximum number of properties to scrape
            verify_urls: Whether to verify each URL works before adding
            
        Returns:
            ScrapingResult with complete and incomplete properties
        """
        result = ScrapingResult()
        seen_urls = set()
        
        # Get links from homepage first
        logger.info("Fetching property links from homepage...")
        links = self.get_property_links_from_homepage()
        
        # If not enough links, try agenda page
        if len(links) < max_properties:
            logger.info("Fetching additional links from agenda page...")
            agenda_links = self.get_property_links_from_agenda()
            for link in agenda_links:
                if link not in links:
                    links.append(link)
                    
        if not links:
            logger.info("No property links found")
            return result
            
        for url in links:
            if result.total_complete >= max_properties:
                break
                
            if url in seen_urls:
                continue
                
            seen_urls.add(url)
            result.total_scraped += 1
            
            logger.info(f"Scraping property from {url}...")
            
            try:
                prop_data = self.scrape_property_detail(url)
                
                if not prop_data:
                    result.errors.append(f"Failed to scrape property from {url}")
                    continue
                    
                is_valid, missing_fields = self._validate_property(prop_data)
                
                if not is_valid:
                    logger.warning(f"Property from {url} is incomplete, missing: {missing_fields}")
                    prop_data['missing_fields'] = missing_fields
                    result.incomplete_properties.append(prop_data)
                    result.total_incomplete += 1
                    continue
                    
                if verify_urls:
                    if not self._verify_url(prop_data['auctioneer_url']):
                        logger.warning(f"Property from {url} has invalid URL")
                        prop_data['missing_fields'] = ['invalid_url']
                        result.incomplete_properties.append(prop_data)
                        result.total_incomplete += 1
                        continue
                        
                prop = Property(
                    id=f"leilaovip-{prop_data['id']}",
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
                    auctioneer_id="leilaovip",
                    source_url=prop_data['auctioneer_url'],
                    accepts_financing=False,
                    accepts_fgts=False,
                    accepts_installments=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                
                result.complete_properties.append(prop)
                result.total_complete += 1
                logger.info(f"Successfully scraped property: {prop_data['title'][:50]}...")
                
            except Exception as e:
                logger.error(f"Error processing property from {url}: {e}")
                result.errors.append(f"Error processing {url}: {str(e)}")
            
        logger.info(f"Scraping complete: {result.total_complete} complete, {result.total_incomplete} incomplete, {len(result.errors)} errors")
        return result


def scrape_leilaovip_properties(max_properties: int = None) -> ScrapingResult:
    """Scrape properties from Leilão VIP."""
    scraper = LeilaoVipScraper()
    return scraper.scrape_properties(max_properties=max_properties)
