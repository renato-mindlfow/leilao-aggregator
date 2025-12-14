"""
Scraper for Inova Leilao auction website.
https://www.inovaleilao.com.br

Uses requests + BeautifulSoup for HTML parsing.
This is a regional auctioneer based in Pernambuco (PE).
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


class InovaLeilaoScraper:
    """Scraper for Inova Leilao auction website."""
    
    BASE_URL = "https://www.inovaleilao.com.br"
    
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
        return "Inova Leilao"
        
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
        if 'apartamento' in title_lower or 'apto' in title_lower or 'aptº' in title_lower:
            return PropertyCategory.APARTAMENTO
        elif 'casa' in title_lower or 'sobrado' in title_lower or 'unid. hab' in title_lower:
            return PropertyCategory.CASA
        elif 'terreno' in title_lower or 'lote' in title_lower:
            return PropertyCategory.TERRENO
        elif 'comercial' in title_lower or 'loja' in title_lower or 'sala' in title_lower or 'galpão' in title_lower or 'galpao' in title_lower or 'prédio' in title_lower or 'predio' in title_lower:
            return PropertyCategory.COMERCIAL
        elif 'rural' in title_lower or 'fazenda' in title_lower or 'sítio' in title_lower or 'sitio' in title_lower or 'gleba' in title_lower:
            return PropertyCategory.RURAL
        elif 'imóvel' in title_lower or 'imovel' in title_lower:
            return PropertyCategory.OUTRO
        return PropertyCategory.OUTRO
        
    def _extract_area_from_text(self, text: str) -> Optional[float]:
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
        
    def _extract_location_from_title(self, title: str) -> Tuple[str, str]:
        """Extract city and neighborhood from title.
        
        Inova Leilao titles often end with neighborhood name like:
        "Aptº 2.901, c/ 52,10m², 02qtos - Boa Viagem"
        
        Since this is a regional auctioneer in Pernambuco, most properties are in Recife area.
        """
        city = "Recife"  # Default city for this regional auctioneer
        neighborhood = ""
        
        # Try to extract neighborhood from title (usually after the last dash)
        if ' - ' in title:
            parts = title.split(' - ')
            if len(parts) >= 2:
                neighborhood = parts[-1].strip()
                # Check if neighborhood contains city name
                if '/' in neighborhood:
                    loc_parts = neighborhood.split('/')
                    neighborhood = loc_parts[0].strip()
                    if len(loc_parts) > 1:
                        # Extract city from "City/PE" format
                        city = loc_parts[0].strip()
                        
        return city, neighborhood
        
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
                # Look for auction links (leiloes/...) - these are the main property pages
                if href.startswith('leiloes/') and 'bens-moveis' not in href.lower():
                    full_url = f"{self.BASE_URL}/{href}"
                    if full_url not in links:
                        links.append(full_url)
                        
            logger.info(f"Found {len(links)} property links on homepage")
            return links
            
        except Exception as e:
            logger.error(f"Failed to get property links from homepage: {e}")
            return []
            
    def scrape_property_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed property information from individual property page."""
        try:
            self._delay(0.5, 1.0)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title from h2 or h3
            title_tag = soup.find('h2') or soup.find('h3')
            if not title_tag:
                logger.warning(f"No title found for {url}")
                return None
                
            title_text = self._clean_text(title_tag.get_text())
            
            # Remove "Lote XXX - " prefix if present
            title = re.sub(r'^Lote\s*\d+\s*-\s*', '', title_text, flags=re.IGNORECASE)
            
            # Extract location from title
            city, neighborhood = self._extract_location_from_title(title)
            state = "PE"  # This is a Pernambuco regional auctioneer
            
            # Extract image URL from carousel
            image_url = ""
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src', '')
                if '/arquivos/leiloes/' in src and 'logo' not in src.lower() and '600x400' not in src:
                    if src.startswith('/'):
                        image_url = f"{self.BASE_URL}{src}"
                    elif src.startswith('http'):
                        image_url = src
                    else:
                        image_url = f"{self.BASE_URL}/{src}"
                    break
                    
            # If no image found in carousel, try to find any property image
            if not image_url:
                for img in img_tags:
                    src = img.get('src', '')
                    if 'arquivos' in src and 'logo' not in src.lower():
                        if src.startswith('/'):
                            image_url = f"{self.BASE_URL}{src}"
                        elif src.startswith('http'):
                            image_url = src
                        else:
                            image_url = f"{self.BASE_URL}/{src}"
                        break
            
            # Extract prices from table
            first_auction_value = None
            second_auction_value = None
            evaluation_value = None
            
            # Look for price table
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    row_text = ' '.join([self._clean_text(cell.get_text()) for cell in cells])
                    
                    # Extract 1st auction price
                    if '1º' in row_text or '1o' in row_text:
                        price_match = re.search(r'R\$\s*([\d.,]+)', row_text)
                        if price_match:
                            first_auction_value = self._parse_brl(price_match.group(1))
                            
                    # Extract 2nd auction price
                    if '2º' in row_text or '2o' in row_text:
                        price_match = re.search(r'R\$\s*([\d.,]+)', row_text)
                        if price_match:
                            second_auction_value = self._parse_brl(price_match.group(1))
                            
            # Look for evaluation value in dl/dd tags
            dl_tags = soup.find_all('dl')
            for dl in dl_tags:
                dt = dl.find('dt')
                dd = dl.find('dd')
                if dt and dd:
                    label = self._clean_text(dt.get_text()).lower()
                    if 'avaliação' in label or 'avaliacao' in label:
                        price_match = re.search(r'R\$\s*([\d.,]+)', dd.get_text())
                        if price_match:
                            evaluation_value = self._parse_brl(price_match.group(1))
                            
            # If no evaluation value found, use first auction value
            if not evaluation_value:
                evaluation_value = first_auction_value
                
            # Extract area
            area = self._extract_area_from_text(title_text)
            
            # Try to extract area from description if not in title
            if not area:
                article = soup.find('article')
                if article:
                    area = self._extract_area_from_text(article.get_text())
                    
            # Determine category
            category = self._determine_category(title)
            
            # Determine auction type from page text
            page_text = soup.get_text().lower()
            auction_type = AuctionType.JUDICIAL  # Default for TJPE auctions
            if 'extrajudicial' in page_text:
                auction_type = AuctionType.EXTRAJUDICIAL
                
            # Check if occupied
            is_occupied = 'ocupad' in page_text
            
            # Calculate discount
            discount = None
            if evaluation_value and second_auction_value and evaluation_value > 0:
                discount = round((1 - second_auction_value / evaluation_value) * 100, 1)
                
            # Extract property ID from URL
            prop_id = url.split('/')[-1]
            
            return {
                'id': prop_id,
                'title': title if title else title_text,
                'description': title_text[:500],
                'category': category,
                'auction_type': auction_type,
                'state': state,
                'city': city,
                'neighborhood': neighborhood,
                'address': "",
                'area': area,
                'price': first_auction_value,
                'first_auction_value': first_auction_value,
                'second_auction_value': second_auction_value,
                'evaluation_value': evaluation_value,
                'discount_percentage': discount,
                'image_url': image_url,
                'auctioneer_url': url,
                'auctioneer_name': self.name,
                'is_occupied': is_occupied,
            }
            
        except Exception as e:
            logger.error(f"Failed to scrape property detail from {url}: {e}")
            return None
            
    def scrape_properties(self, max_properties: int = 10, verify_urls: bool = True) -> ScrapingResult:
        """
        Scrape properties from Inova Leilao.
        
        Args:
            max_properties: Maximum number of properties to scrape
            verify_urls: Whether to verify each URL works before adding
            
        Returns:
            ScrapingResult with complete and incomplete properties
        """
        result = ScrapingResult()
        seen_urls = set()
        
        # Get links from homepage
        logger.info("Fetching property links from homepage...")
        links = self.get_property_links_from_homepage()
        
        if not links:
            logger.info("No property links found")
            return result
            
        # Filter to only include real estate properties (exclude vehicles, equipment, etc.)
        property_links = []
        for link in links:
            link_lower = link.lower()
            # Skip non-property items
            if any(skip in link_lower for skip in ['veiculo', 'carro', 'moto', 'bmw', 'fiat', 'equipamento', 'maquina', 'sucata', 'bens-moveis']):
                continue
            property_links.append(link)
            
        logger.info(f"Filtered to {len(property_links)} property links (excluding vehicles/equipment)")
            
        for url in property_links:
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
                    id=f"inovaleilao-{prop_data['id']}",
                    title=prop_data['title'],
                    description=prop_data['description'],
                    category=prop_data['category'],
                    auction_type=prop_data['auction_type'],
                    state=prop_data['state'],
                    city=prop_data['city'],
                    neighborhood=prop_data['neighborhood'],
                    address=prop_data['address'],
                    area_total=prop_data['area'],
                    evaluation_value=prop_data['evaluation_value'],
                    first_auction_value=prop_data['first_auction_value'],
                    second_auction_value=prop_data['second_auction_value'],
                    discount_percentage=prop_data['discount_percentage'],
                    image_url=prop_data['image_url'],
                    auctioneer_url=prop_data['auctioneer_url'],
                    auctioneer_name=self.name,
                    auctioneer_id="inovaleilao",
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


def scrape_inovaleilao_properties(max_properties: int = 10) -> ScrapingResult:
    """Scrape properties from Inova Leilao."""
    scraper = InovaLeilaoScraper()
    return scraper.scrape_properties(max_properties=max_properties)
