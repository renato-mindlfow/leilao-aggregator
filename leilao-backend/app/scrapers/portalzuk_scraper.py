"""
Portal Zuk scraper with URL validation and multi-state support.
Extracts property data from Portal Zuk listing pages and validates URLs.
Scrapes across all Brazilian states to maximize property collection.
"""
import logging
import re
import uuid
import requests
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup

from app.models.property import Property, PropertyCategory, AuctionType

logger = logging.getLogger(__name__)


class PortalZukScraper:
    """Scraper for Portal Zuk auction website with URL validation."""
    
    # Rate limiting configuration
    DEFAULT_DELAY = 0.5  # Delay between requests in seconds (reduced for faster scraping)
    MAX_RETRIES = 3  # Maximum retries for failed requests
    BACKOFF_FACTOR = 2.0  # Exponential backoff multiplier
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        self.current_delay = self.DEFAULT_DELAY
        self.consecutive_429s = 0
        
    @property
    def name(self) -> str:
        return "Portal Zuk"
        
    @property
    def base_url(self) -> str:
        return "https://www.portalzuk.com.br"
        
    def get_property_listings_url(self, page: int = 1, state: str = "sp") -> str:
        """Return the URL for property listings page."""
        if page > 1:
            return f"{self.base_url}/leilao-de-imoveis/u/todos-imoveis/{state}?page={page}"
        return f"{self.base_url}/leilao-de-imoveis/u/todos-imoveis/{state}"
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """
        Validate a property URL by following redirects.
        Returns dict with:
        - is_valid: True if URL points to a specific property page
        - final_url: The URL after following redirects
        - status: 'ok', 'redirects_to_listing', 'not_found', 'error'
        """
        try:
            response = self.session.get(url, allow_redirects=True, timeout=10)
            final_url = response.url
            
            # Check if the final URL is a specific property page
            if '/imovel/' in final_url and '/leilao-de-imoveis/' not in final_url:
                return {
                    'is_valid': True,
                    'final_url': final_url,
                    'status': 'ok'
                }
            elif '/leilao-de-imoveis/' in final_url:
                return {
                    'is_valid': False,
                    'final_url': final_url,
                    'status': 'redirects_to_listing'
                }
            elif response.status_code == 404:
                return {
                    'is_valid': False,
                    'final_url': final_url,
                    'status': 'not_found'
                }
            else:
                return {
                    'is_valid': True,
                    'final_url': final_url,
                    'status': 'ok'
                }
        except Exception as e:
            logger.error(f"Error validating URL {url}: {e}")
            return {
                'is_valid': False,
                'final_url': url,
                'status': 'error'
            }
    
    def get_page(self, url: str, retry_count: int = 0) -> str:
        """
        Fetch a page using requests with retry logic for rate limiting.
        
        Args:
            url: The URL to fetch
            retry_count: Current retry attempt (used internally)
            
        Returns:
            The page HTML content
            
        Raises:
            requests.HTTPError: If the request fails after all retries
        """
        try:
            response = self.session.get(url, timeout=30)
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                self.consecutive_429s += 1
                
                if retry_count < self.MAX_RETRIES:
                    # Check for Retry-After header
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        # Exponential backoff
                        wait_time = self.current_delay * (self.BACKOFF_FACTOR ** retry_count)
                    
                    logger.warning(f"Rate limited (429). Waiting {wait_time:.1f}s before retry {retry_count + 1}/{self.MAX_RETRIES}")
                    time.sleep(wait_time)
                    
                    # Increase base delay for future requests
                    self.current_delay = min(self.current_delay * 1.5, 10.0)
                    
                    return self.get_page(url, retry_count + 1)
                else:
                    logger.error(f"Max retries exceeded for {url}")
                    response.raise_for_status()
            
            # Reset consecutive 429 counter on success
            self.consecutive_429s = 0
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            if retry_count < self.MAX_RETRIES and not isinstance(e, requests.exceptions.HTTPError):
                wait_time = self.current_delay * (self.BACKOFF_FACTOR ** retry_count)
                logger.warning(f"Request error: {e}. Waiting {wait_time:.1f}s before retry {retry_count + 1}/{self.MAX_RETRIES}")
                time.sleep(wait_time)
                return self.get_page(url, retry_count + 1)
            raise
    
    @staticmethod
    def calculate_discount(evaluation_value: Optional[float], auction_value: Optional[float]) -> Optional[float]:
        """Calculate discount percentage."""
        if not evaluation_value or not auction_value or evaluation_value <= 0:
            return None
        discount = ((evaluation_value - auction_value) / evaluation_value) * 100
        return round(max(0, discount), 1)
    
    # All Brazilian states with properties on Portal Zuk
    BRAZILIAN_STATES = [
        'sp', 'rj', 'rs', 'mg', 'go', 'pr', 'ba', 'ce', 'pe', 'sc',
        'ms', 'mt', 'pa', 'pb', 'ma', 'rn', 'df', 'al', 'am', 'se',
        'pi', 'ro', 'to', 'es', 'rr'
    ]
    
    def scrape_listings(self, max_properties: int = 50, state: str = "all") -> List[Property]:
        """
        Scrape property listings from Portal Zuk across multiple states.
        
        Portal Zuk uses JavaScript-based pagination which requires too much memory
        for cloud deployment. Instead, we scrape the first page of each state
        to collect properties from across Brazil.
        
        Args:
            max_properties: Maximum number of properties to scrape
            state: Brazilian state code (e.g., 'sp', 'rj') or 'all' for all states
            
        Returns:
            List of Property objects with validated URLs
        """
        properties = []
        seen_urls = set()
        
        # Determine which states to scrape
        if state == "all":
            states_to_scrape = self.BRAZILIAN_STATES
        else:
            states_to_scrape = [state]
        
        try:
            for current_state in states_to_scrape:
                if len(properties) >= max_properties:
                    logger.info(f"Reached max_properties limit: {max_properties}")
                    break
                
                # Fetch listing page for this state
                url = self.get_property_listings_url(state=current_state)
                logger.info(f"Scraping Portal Zuk {current_state.upper()} from: {url}")
                
                try:
                    html = self.get_page(url)
                except Exception as e:
                    logger.error(f"Error fetching {current_state}: {e}")
                    continue
                    
                soup = BeautifulSoup(html, 'lxml')
                
                # Find all property cards
                property_links = soup.find_all('a', href=re.compile(r'/imovel/'))
                
                # Filter to unique URLs
                new_links = []
                for link in property_links:
                    href = link.get('href', '')
                    if href and href not in seen_urls:
                        seen_urls.add(href)
                        new_links.append(link)
                
                logger.info(f"State {current_state.upper()}: Found {len(new_links)} unique property links")
                
                # Process each property link
                for link in new_links:
                    if len(properties) >= max_properties:
                        break
                        
                    try:
                        href = link.get('href', '')
                        if not href:
                            continue
                        
                        # Make URL absolute if needed
                        if href.startswith('/'):
                            property_url = f"{self.base_url}{href}"
                        elif not href.startswith('http'):
                            property_url = f"{self.base_url}/{href}"
                        else:
                            property_url = href
                        
                        logger.info(f"Processing property {len(properties)+1}/{max_properties}: {property_url}")
                        
                        # Validate the URL
                        validation = self.validate_url(property_url)
                        
                        if not validation['is_valid']:
                            logger.warning(f"Skipping invalid URL: {property_url} (status: {validation['status']})")
                            continue
                        
                        # Use the final URL after redirects
                        final_url = validation['final_url']
                        
                        # Fetch property page to extract details
                        prop = self.scrape_property_details(final_url)
                        
                        if prop:
                            properties.append(prop)
                            logger.info(f"Successfully scraped: {prop.title}")
                        
                        # Delay between requests to avoid rate limiting
                        time.sleep(self.current_delay)
                        
                    except Exception as e:
                        logger.error(f"Error processing property link: {e}")
                        continue
                
                # Delay between states
                time.sleep(self.current_delay)
            
        except Exception as e:
            logger.error(f"Error scraping Portal Zuk listings: {e}")
        
        logger.info(f"Scraped {len(properties)} valid properties from Portal Zuk across {len(states_to_scrape)} states")
        return properties
    
    def scrape_property_details(self, url: str) -> Optional[Property]:
        """
        Scrape detailed information for a single property.
        
        Args:
            url: The property page URL
            
        Returns:
            Property object or None if scraping fails
        """
        try:
            # Fetch property page using requests
            html = self.get_page(url)
            soup = BeautifulSoup(html, 'lxml')
            
            # Extract title from h1
            title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else "Imóvel em Leilão"
            
            # Extract address from the page
            address_elem = soup.find('address') or soup.find(string=re.compile(r'Rua|Avenida|Alameda|Estrada|Travessa', re.I))
            address_text = ""
            if address_elem:
                if hasattr(address_elem, 'get_text'):
                    address_text = address_elem.get_text(strip=True)
                else:
                    # It's a NavigableString, get parent's text
                    parent = address_elem.parent
                    if parent:
                        address_text = parent.get_text(strip=True)
            
            # Parse location from URL (format: /imovel/sp/city/neighborhood/address/id)
            url_parts = url.split('/')
            state = ""
            city = ""
            neighborhood = ""
            
            if 'imovel' in url_parts:
                imovel_idx = url_parts.index('imovel')
                if len(url_parts) > imovel_idx + 1:
                    state = url_parts[imovel_idx + 1].upper()
                if len(url_parts) > imovel_idx + 2:
                    city = url_parts[imovel_idx + 2].replace('-', ' ').title()
                if len(url_parts) > imovel_idx + 3:
                    neighborhood = url_parts[imovel_idx + 3].replace('-', ' ').title()
            
            # Extract category from title or page content
            page_text = soup.get_text().lower()
            category = self._determine_category(title, page_text)
            
            # Extract auction type
            auction_type = self._determine_auction_type(page_text)
            
            # Extract area
            area = self._extract_area_from_page(soup)
            
            # Extract prices
            prices = self._extract_prices(soup)
            
            # Extract image URL
            image_url = self._extract_image_url(soup)
            
            # Extract auction dates
            dates = self._extract_dates(soup)
            
            # Check for payment options
            accepts_financing = 'financiamento' in page_text or 'financia' in page_text
            accepts_fgts = 'fgts' in page_text
            accepts_installments = 'parcelamento' in page_text or 'parcela' in page_text or '30x' in page_text
            
            # Calculate discount
            discount = None
            if prices.get('evaluation') and prices.get('second_auction'):
                discount = self.calculate_discount(prices['evaluation'], prices['second_auction'])
            elif prices.get('first_auction') and prices.get('second_auction'):
                discount = self.calculate_discount(prices['first_auction'], prices['second_auction'])
            
            # Build full title with address
            full_title = f"{title} - {address_text}" if address_text else title
            if city and state:
                full_title = f"{full_title} - {city}/{state}"
            
            prop = Property(
                id=str(uuid.uuid4()),
                title=full_title[:200],
                description=full_title,
                category=category,
                auction_type=auction_type,
                state=state or "SP",
                city=city or "São Paulo",
                neighborhood=neighborhood or "",
                address=address_text or "",
                area_total=area,
                evaluation_value=prices.get('evaluation'),
                first_auction_value=prices.get('first_auction'),
                second_auction_value=prices.get('second_auction'),
                discount_percentage=discount,
                image_url=image_url,
                auctioneer_url=url,
                auctioneer_name=self.name,
                auctioneer_id="portal_zuk",
                source_url=url,  # This is the validated URL
                first_auction_date=dates.get('first'),
                second_auction_date=dates.get('second'),
                accepts_financing=accepts_financing,
                accepts_fgts=accepts_fgts,
                accepts_installments=accepts_installments,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            
            return prop
            
        except Exception as e:
            logger.error(f"Error scraping property details from {url}: {e}")
            return None
    
    def _determine_category(self, title: str, page_text: str) -> PropertyCategory:
        """Determine property category from title and page text.
        
        IMPORTANT: Title-based signals take precedence over page text to avoid
        miscategorization when page text contains multiple property type keywords.
        For example, a "Casa à venda" listing might have "apartamento" mentioned
        elsewhere on the page, but the title clearly indicates it's a Casa.
        """
        import re
        title_lower = title.lower() if title else ""
        combined = f"{title} {page_text}".lower()
        
        # STEP 1: Check title first (highest priority, most reliable signal)
        # Check for Casa keywords in title
        casa_keywords = ['casa', 'sobrado', 'residência', 'residencia', 'chácara', 'chacara', 'sítio', 'sitio']
        for keyword in casa_keywords:
            if re.search(rf'\b{keyword}\b', title_lower):
                return PropertyCategory.CASA
        
        # Check for Apartamento keywords in title
        apto_keywords = ['apartamento', 'apto', 'flat', 'cobertura', 'kitnet', 'loft', 'studio']
        for keyword in apto_keywords:
            if re.search(rf'\b{keyword}\b', title_lower):
                return PropertyCategory.APARTAMENTO
        
        # Check for Terreno keywords in title
        terreno_keywords = ['terreno', 'lote', 'gleba']
        for keyword in terreno_keywords:
            if re.search(rf'\b{keyword}\b', title_lower):
                return PropertyCategory.TERRENO
        
        # Check for Comercial keywords in title
        comercial_keywords = ['comercial', 'loja', 'sala', 'galpão', 'galpao', 'escritório', 'escritorio', 'prédio', 'predio']
        for keyword in comercial_keywords:
            if re.search(rf'\b{keyword}\b', title_lower):
                return PropertyCategory.COMERCIAL
        
        # Check for Estacionamento keywords in title
        estac_keywords = ['garagem', 'vaga', 'estacionamento', 'box']
        for keyword in estac_keywords:
            if re.search(rf'\b{keyword}\b', title_lower):
                return PropertyCategory.ESTACIONAMENTO
        
        # STEP 2: Fall back to combined text (title + page text) if title didn't match
        # Same order: Casa before Apartamento to avoid false positives
        for keyword in casa_keywords:
            if re.search(rf'\b{keyword}\b', combined):
                return PropertyCategory.CASA
        
        for keyword in apto_keywords:
            if re.search(rf'\b{keyword}\b', combined):
                return PropertyCategory.APARTAMENTO
        
        for keyword in terreno_keywords:
            if re.search(rf'\b{keyword}\b', combined):
                return PropertyCategory.TERRENO
        
        for keyword in comercial_keywords:
            if re.search(rf'\b{keyword}\b', combined):
                return PropertyCategory.COMERCIAL
        
        for keyword in estac_keywords:
            if re.search(rf'\b{keyword}\b', combined):
                return PropertyCategory.ESTACIONAMENTO
        
        return PropertyCategory.OUTROS
    
    def _determine_auction_type(self, page_text: str) -> AuctionType:
        """Determine auction type from page text."""
        text_lower = page_text.lower()
        
        if 'extrajudicial' in text_lower:
            return AuctionType.EXTRAJUDICIAL
        elif 'judicial' in text_lower:
            return AuctionType.JUDICIAL
        elif 'sfi' in text_lower or 'alienação fiduciária' in text_lower:
            return AuctionType.LEILAO_SFI
        elif 'venda direta' in text_lower:
            return AuctionType.VENDA_DIRETA
        else:
            return AuctionType.OUTROS
    
    def _extract_area_from_page(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract area from page."""
        # Look for area patterns in the page
        page_text = soup.get_text()
        
        # Try different patterns
        patterns = [
            r'Metragem total\s*([\d.,]+)\s*m[²2]',
            r'Área Total\s*([\d.,]+)\s*m[²2]',
            r'([\d.,]+)\s*m[²2]\s*total',
            r'([\d.,]+)\s*m[²2]\s*útil',
            r'([\d.,]+)\s*m[²2]\s*construída',
            r'([\d.,]+)\s*m[²2]\s*terreno',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                area_str = match.group(1).replace('.', '').replace(',', '.')
                try:
                    return float(area_str)
                except ValueError:
                    continue
        
        return None
    
    @staticmethod
    def _parse_brl(price_str: str) -> Optional[float]:
        """Parse Brazilian Real format to float.
        
        Examples:
            '232.837,09' -> 232837.09
            '5.000,00' -> 5000.00
            '1.234' -> 1234.0
        """
        try:
            # Remove dots (thousands separator) and replace comma with dot (decimal)
            cleaned = price_str.replace('.', '').replace(',', '.')
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    
    def _extract_prices(self, soup: BeautifulSoup) -> Dict[str, Optional[float]]:
        """Extract prices from page using context-aware extraction.
        
        This method looks for specific patterns like '1º Leilão' and '2º Leilão'
        followed by dates and prices, rather than just grabbing all prices on the page.
        This prevents incorrectly extracting 'incremento mínimo' or other values.
        """
        prices = {
            'evaluation': None,
            'first_auction': None,
            'second_auction': None
        }
        
        # Normalize page text (collapse whitespace)
        page_text = ' '.join(soup.get_text(separator=' ').split())
        
        # Strategy 1: Look for auction values with date context
        # Pattern: "1º Leilão DD/MM/YY às HHhMM" followed by R$ value
        # This is the most reliable pattern on Portal Zuk
        
        # Extract 1º Leilão value with date context
        pattern_1_with_date = r'1[ºo°]\s*Leil[aã]o\s*(\d{2}/\d{2}/\d{2,4})\s*(?:às\s*)?(?:\d{1,2}[h:]\d{2})?\s*R\$\s*([\d.,]+)'
        m1_date = re.search(pattern_1_with_date, page_text, re.I)
        
        if m1_date:
            prices['first_auction'] = self._parse_brl(m1_date.group(2))
            logger.debug(f"Found 1º Leilão with date: R$ {m1_date.group(2)}")
        
        # Extract 2º Leilão value with date context
        pattern_2_with_date = r'2[ºo°]\s*Leil[aã]o\s*(\d{2}/\d{2}/\d{2,4})\s*(?:às\s*)?(?:\d{1,2}[h:]\d{2})?\s*(?:[↓▼]?\s*\d{1,2}\s*%\s*)?R\$\s*([\d.,]+)'
        m2_date = re.search(pattern_2_with_date, page_text, re.I)
        
        if m2_date:
            prices['second_auction'] = self._parse_brl(m2_date.group(2))
            logger.debug(f"Found 2º Leilão with date: R$ {m2_date.group(2)}")
        
        # Strategy 2: If date-based extraction didn't work, try simpler patterns
        # but be more careful about context
        if not prices['first_auction']:
            # Look for "1º Leilão" followed by R$ within a reasonable distance
            pattern_1_simple = r'1[ºo°]\s*Leil[aã]o[^R]*R\$\s*([\d.,]+)'
            m1_simple = re.search(pattern_1_simple, page_text, re.I)
            if m1_simple:
                val = self._parse_brl(m1_simple.group(1))
                # Sanity check: auction values should be > 10000 typically
                if val and val > 10000:
                    prices['first_auction'] = val
                    logger.debug(f"Found 1º Leilão (simple): R$ {m1_simple.group(1)}")
        
        if not prices['second_auction']:
            # Look for "2º Leilão" followed by R$ within a reasonable distance
            pattern_2_simple = r'2[ºo°]\s*Leil[aã]o[^R]*R\$\s*([\d.,]+)'
            m2_simple = re.search(pattern_2_simple, page_text, re.I)
            if m2_simple:
                val = self._parse_brl(m2_simple.group(1))
                # Sanity check: auction values should be > 10000 typically
                if val and val > 10000:
                    prices['second_auction'] = val
                    logger.debug(f"Found 2º Leilão (simple): R$ {m2_simple.group(1)}")
        
        # Strategy 3: Look for "valor de avaliação" or similar for evaluation value
        eval_pattern = r'(?:valor\s+de\s+)?avalia[çc][aã]o[:\s]*R\$\s*([\d.,]+)'
        m_eval = re.search(eval_pattern, page_text, re.I)
        if m_eval:
            val = self._parse_brl(m_eval.group(1))
            if val and val > 10000:
                prices['evaluation'] = val
                logger.debug(f"Found Avaliação: R$ {m_eval.group(1)}")
        
        # If no explicit evaluation value, use first auction as evaluation
        if not prices['evaluation'] and prices['first_auction']:
            prices['evaluation'] = prices['first_auction']
        
        # Validation: Check for anomalies
        prices = self._validate_prices(prices)
        
        return prices
    
    def _validate_prices(self, prices: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
        """Validate extracted prices and detect anomalies.
        
        This helps catch cases where incorrect values were extracted,
        such as 'incremento mínimo' being mistaken for auction value.
        """
        first = prices.get('first_auction')
        second = prices.get('second_auction')
        
        if first and second:
            # Check 1: Second auction should be less than or equal to first
            if second > first:
                logger.warning(f"Price anomaly: 2º Leilão ({second}) > 1º Leilão ({first}). Swapping values.")
                prices['first_auction'], prices['second_auction'] = second, first
                first, second = second, first
            
            # Check 2: Discount should be reasonable (typically 5-60%)
            if first > 0:
                discount = ((first - second) / first) * 100
                
                if discount > 80:
                    # Unusually high discount - likely an extraction error
                    # The "second auction" value might be incremento mínimo
                    logger.warning(f"Price anomaly: Discount of {discount:.1f}% is unusually high. "
                                   f"Clearing 2º Leilão value as it may be incorrect.")
                    prices['second_auction'] = None
                elif discount < 0:
                    logger.warning(f"Price anomaly: Negative discount detected. Clearing 2º Leilão.")
                    prices['second_auction'] = None
        
        # Check 3: Values should be reasonable for real estate (> 10000)
        for key in ['first_auction', 'second_auction', 'evaluation']:
            val = prices.get(key)
            if val and val < 10000:
                logger.warning(f"Price anomaly: {key} value ({val}) is too low for real estate. Clearing.")
                prices[key] = None
        
        return prices
    
    def _extract_image_url(self, soup: BeautifulSoup) -> str:
        """Extract main image URL from page."""
        # Look for property images
        img_patterns = [
            'img[src*="imagens.portalzuk"]',
            'figure img',
            'img[src*="mini"]',
            'img[src*="detalhe"]',
        ]
        
        for pattern in img_patterns:
            img = soup.select_one(pattern)
            if img:
                src = img.get('src') or img.get('data-src')
                if src and 'logo' not in src.lower():
                    return src
        
        return ""
    
    def _extract_dates(self, soup: BeautifulSoup) -> Dict[str, Optional[datetime]]:
        """Extract auction dates from page."""
        dates = {
            'first': None,
            'second': None
        }
        
        page_text = soup.get_text()
        
        # Look for date patterns
        date_pattern = r'(\d{2}/\d{2}/\d{2,4})\s*(?:às\s*)?(\d{1,2}[h:]\d{2})?'
        matches = re.findall(date_pattern, page_text)
        
        for i, match in enumerate(matches[:2]):
            date_str = match[0]
            time_str = match[1] if match[1] else ""
            
            try:
                if len(date_str.split('/')[-1]) == 2:
                    date_obj = datetime.strptime(date_str, '%d/%m/%y')
                else:
                    date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                
                if i == 0:
                    dates['first'] = date_obj
                else:
                    dates['second'] = date_obj
            except ValueError:
                continue
        
        return dates


def scrape_portal_zuk(max_properties: int = 500, state: str = "all") -> List[Property]:
    """
    Convenience function to scrape Portal Zuk properties.
    
    Args:
        max_properties: Maximum number of properties to scrape (default 500 for comprehensive collection)
        state: Brazilian state code or 'all' for all states
        
    Returns:
        List of Property objects with validated URLs
    """
    scraper = PortalZukScraper()
    return scraper.scrape_listings(max_properties=max_properties, state=state)
