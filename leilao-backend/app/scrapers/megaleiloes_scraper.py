"""
Scraper for Mega Leiloes auction website.
https://www.megaleiloes.com.br

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


class MegaleiloesScraper:
    """Scraper for Mega Leiloes auction website using requests + BeautifulSoup."""
    
    BASE_URL = "https://www.megaleiloes.com.br"
    LISTING_URL = "https://www.megaleiloes.com.br/imoveis"
    
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
        return "Mega Leiloes"
        
    def _delay(self, min_seconds: float = 1.0, max_seconds: float = 2.0):
        """Add a random delay between requests to be polite."""
        time.sleep(random.uniform(min_seconds, max_seconds))
        
    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace."""
        if not text:
            return ""
        text = ' '.join(text.split())
        return text.strip()
        
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from text like 'R$ 11.126.448,58'."""
        if not price_text:
            return None
        price_text = price_text.replace('R$', '').strip()
        price_text = price_text.replace('.', '').replace(',', '.')
        try:
            return float(price_text)
        except ValueError:
            return None
            
    def _extract_area(self, text: str) -> Optional[float]:
        """Extract area in m2 from text."""
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
        elif 'comercial' in title_lower or 'loja' in title_lower or 'sala' in title_lower or 'prédio' in title_lower:
            return PropertyCategory.COMERCIAL
        elif 'rural' in title_lower or 'fazenda' in title_lower or 'sítio' in title_lower:
            return PropertyCategory.RURAL
        elif 'galpão' in title_lower or 'galpao' in title_lower:
            return PropertyCategory.COMERCIAL
        return PropertyCategory.OUTRO
        
    def _parse_location(self, location_text: str) -> Tuple[str, str, str]:
        """Parse city, state, and address from location text."""
        city = ""
        state = ""
        address = location_text
        
        if not location_text:
            return city, state, address
            
        parts = location_text.split(',')
        if len(parts) >= 2:
            last_part = parts[-1].strip()
            state_match = re.search(r'\b([A-Z]{2})\b', last_part)
            if state_match:
                state = state_match.group(1)
                city_part = parts[-2].strip() if len(parts) >= 2 else ""
                city = city_part
                
        return city, state, address
        
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
            
    def get_property_links_from_listing(self, page: int = 1) -> List[str]:
        """Get property links from listing page."""
        url = f"{self.LISTING_URL}?pagina={page}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '/imoveis/' in href and '-x' in href.lower() or '-j' in href.lower():
                    if href.startswith('/'):
                        href = self.BASE_URL + href
                    if href not in links and 'pagina=' not in href:
                        links.append(href)
                        
            logger.info(f"Found {len(links)} property links on page {page}")
            return links
            
        except Exception as e:
            logger.error(f"Failed to get property links from page {page}: {e}")
            return []
            
    def scrape_property_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed property information from individual property page."""
        try:
            self._delay(0.5, 1.0)
            response = self.session.get(url, allow_redirects=True, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: status {response.status_code}")
                return None
                
            final_url = response.url
            soup = BeautifulSoup(response.text, 'html.parser')
            
            h1_tag = soup.find('h1')
            title = self._clean_text(h1_tag.get_text()) if h1_tag else ""
            
            if not title:
                logger.warning(f"No title found for {url}")
                return None
                
            lot_code = ""
            code_match = re.search(r'([XJ]\d+)', url, re.IGNORECASE)
            if code_match:
                lot_code = code_match.group(1).upper()
                
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                if 'cdn1.megaleiloes.com.br/batches/' in src:
                    images.append(src)
                    
            image_url = images[0] if images else ""
            
            location_text = ""
            for text in soup.stripped_strings:
                if 'Localização' in text:
                    continue
                if re.search(r'\b[A-Z]{2}\b', text) and ',' in text:
                    location_text = text
                    break
                    
            location_div = soup.find(string=re.compile(r'Localização'))
            if location_div:
                parent = location_div.find_parent()
                if parent:
                    next_sibling = parent.find_next_sibling()
                    if next_sibling:
                        location_text = self._clean_text(next_sibling.get_text())
                        
            city, state, address = self._parse_location(location_text)
            
            if not city or not state:
                breadcrumb = soup.find('ol')
                if breadcrumb:
                    items = breadcrumb.find_all('li')
                    for item in items:
                        text = item.get_text().strip()
                        if len(text) == 2 and text.isupper():
                            state = text
                        elif text and text not in ['Mega Leilões', 'Imóveis'] and len(text) > 2:
                            city = text
                            
            if not state:
                state_match = re.search(r'/([a-z]{2})/', url)
                if state_match:
                    state = state_match.group(1).upper()
                    
            if not city:
                city_match = re.search(r'/[a-z]{2}/([^/]+)/', url)
                if city_match:
                    city = city_match.group(1).replace('-', ' ').title()
                    
            price = None
            # First try to extract from JavaScript variable (most reliable)
            js_price_match = re.search(r"var\s+product_price\s*=\s*['\"](\d+(?:\.\d+)?)['\"]", response.text)
            if js_price_match:
                try:
                    price = float(js_price_match.group(1))
                except ValueError:
                    pass
            
            # Fallback to other patterns if JS variable not found
            if not price or price <= 0:
                price_patterns = [
                    r'R\$\s*([\d.,]+)',
                    r'Valor inicial.*?R\$\s*([\d.,]+)',
                ]
                
                for pattern in price_patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        price = self._parse_price(match.group(1))
                        if price and price > 0:
                            break
                        
            area = self._extract_area(title)
            category = self._determine_category(title)
            
            auction_type = AuctionType.EXTRAJUDICIAL
            if 'judicial' in response.text.lower():
                auction_type = AuctionType.JUDICIAL
                
            is_occupied = 'ocupad' in title.lower() or 'ocupad' in response.text.lower()
            
            return {
                'id': lot_code or str(hash(url))[-8:],
                'title': title,
                'description': title,
                'category': category,
                'auction_type': auction_type,
                'state': state,
                'city': city,
                'neighborhood': '',
                'address': address or location_text,
                'area': area,
                'price': price,
                'first_auction_value': price,
                'second_auction_value': None,
                'discount_percentage': None,
                'image_url': image_url,
                'auctioneer_url': final_url,
                'auctioneer_name': self.name,
                'is_occupied': is_occupied,
            }
            
        except Exception as e:
            logger.error(f"Failed to scrape property from {url}: {e}")
            return None
            
    def scrape_properties(self, max_properties: int = None, verify_urls: bool = True) -> ScrapingResult:
        """
        Scrape properties from Mega Leiloes.
        
        Args:
            max_properties: Maximum number of properties to scrape
            verify_urls: Whether to verify each URL works before adding
            
        Returns:
            ScrapingResult with complete and incomplete properties
        """
        result = ScrapingResult()
        seen_urls = set()
        
        page = 1
        while result.total_complete < max_properties:
            logger.info(f"Fetching listing page {page}...")
            links = self.get_property_links_from_listing(page=page)
            
            if not links:
                logger.info("No more links found")
                break
                
            for link in links:
                if result.total_complete >= max_properties:
                    break
                    
                if link in seen_urls:
                    continue
                    
                seen_urls.add(link)
                result.total_scraped += 1
                
                logger.info(f"Scraping property from {link}...")
                
                try:
                    prop_data = self.scrape_property_detail(link)
                    
                    if not prop_data:
                        result.errors.append(f"Failed to scrape property from {link}")
                        continue
                        
                    is_valid, missing_fields = self._validate_property(prop_data)
                    
                    if not is_valid:
                        logger.warning(f"Property from {link} is incomplete, missing: {missing_fields}")
                        prop_data['missing_fields'] = missing_fields
                        result.incomplete_properties.append(prop_data)
                        result.total_incomplete += 1
                        continue
                        
                    if verify_urls:
                        if not self._verify_url(prop_data['auctioneer_url']):
                            logger.warning(f"Property from {link} has invalid URL")
                            prop_data['missing_fields'] = ['invalid_url']
                            result.incomplete_properties.append(prop_data)
                            result.total_incomplete += 1
                            continue
                            
                    prop = Property(
                        id=f"megaleiloes-{prop_data['id']}",
                        title=prop_data['title'],
                        description=prop_data['description'],
                        category=prop_data['category'],
                        auction_type=prop_data['auction_type'],
                        state=prop_data['state'],
                        city=prop_data['city'],
                        neighborhood=prop_data['neighborhood'],
                        address=prop_data['address'],
                        area_total=prop_data['area'],
                        evaluation_value=prop_data['price'],
                        first_auction_value=prop_data['price'],
                        second_auction_value=prop_data['second_auction_value'],
                        discount_percentage=prop_data['discount_percentage'],
                        image_url=prop_data['image_url'],
                        auctioneer_url=prop_data['auctioneer_url'],
                        auctioneer_name=self.name,
                        auctioneer_id="megaleiloes",
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
                    logger.error(f"Error processing property from {link}: {e}")
                    result.errors.append(f"Error processing {link}: {str(e)}")
                    
            page += 1
            self._delay(1.0, 2.0)
            
        logger.info(f"Scraping complete: {result.total_complete} complete, {result.total_incomplete} incomplete, {len(result.errors)} errors")
        return result


def scrape_megaleiloes_properties(max_properties: int = None) -> ScrapingResult:
    """Scrape properties from Mega Leiloes."""
    scraper = MegaleiloesScraper()
    return scraper.scrape_properties(max_properties=max_properties)
