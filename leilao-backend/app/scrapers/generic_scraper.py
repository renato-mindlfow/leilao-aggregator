"""
Generic scraper that can be configured for different auction websites.
Uses configurable CSS selectors to extract data.
"""
import logging
import re
import uuid
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper
from app.models.property import Property, PropertyCategory, AuctionType

logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    """Configuration for a generic scraper."""
    name: str
    base_url: str
    listings_url_template: str  # Use {page} for page number
    
    # CSS selectors for listing cards
    card_selector: str = 'div[class*="card"], article, div[class*="item"], div[class*="lote"]'
    title_selector: str = 'h2, h3, h4, [class*="title"], [class*="titulo"]'
    link_selector: str = 'a[href]'
    image_selector: str = 'img'
    location_selector: str = '[class*="location"], [class*="endereco"], [class*="cidade"]'
    price_selector: str = '[class*="price"], [class*="valor"], [class*="lance"]'
    category_selector: str = '[class*="category"], [class*="tipo"], [class*="categoria"]'
    auction_type_selector: str = '[class*="type"], [class*="modalidade"]'
    area_selector: str = '[class*="area"], [class*="metragem"]'
    next_page_selector: str = 'a[class*="next"], button[class*="next"], [aria-label*="próxima"]'
    
    # URL patterns to identify property links
    property_url_patterns: list[str] = None
    
    def __post_init__(self):
        if self.property_url_patterns is None:
            self.property_url_patterns = ['/oferta/', '/imovel/', '/lote/', '/item/', '/detalhes/']


# Pre-configured scrapers for known auction sites
SCRAPER_CONFIGS = {
    "Superbid": ScraperConfig(
        name="Superbid",
        base_url="https://www.superbid.net",
        listings_url_template="https://www.superbid.net/imoveis?page={page}",
        card_selector='div[class*="offer-card"], div[class*="product-card"]',
    ),
    "Portal Zuk": ScraperConfig(
        name="Portal Zuk",
        base_url="https://www.portalzuk.com.br",
        listings_url_template="https://www.portalzuk.com.br/imoveis?pagina={page}",
        card_selector='div[class*="card"], article[class*="imovel"]',
    ),
    "Mega Leilões": ScraperConfig(
        name="Mega Leilões",
        base_url="https://www.megaleiloes.com.br",
        listings_url_template="https://www.megaleiloes.com.br/imoveis?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "Caixa": ScraperConfig(
        name="Caixa",
        base_url="https://venda-imoveis.caixa.gov.br",
        listings_url_template="https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp?sltTipoBusca=imoveis&page={page}",
        card_selector='div[class*="card"], tr[class*="imovel"]',
    ),
    "Leilão VIP": ScraperConfig(
        name="Leilão VIP",
        base_url="https://www.leilaovip.com.br",
        listings_url_template="https://www.leilaovip.com.br/imoveis?page={page}",
        card_selector='div[class*="card"], div[class*="anuncio"]',
    ),
    "Bom Valor": ScraperConfig(
        name="Bom Valor",
        base_url="https://mercado.bomvalor.com.br",
        listings_url_template="https://mercado.bomvalor.com.br/imoveis?page={page}",
        card_selector='div[class*="card"], article',
    ),
    "Inova Leilão": ScraperConfig(
        name="Inova Leilão",
        base_url="https://www.inovaleilao.com.br",
        listings_url_template="https://www.inovaleilao.com.br/lotes?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "Pestana Leilões": ScraperConfig(
        name="Pestana Leilões",
        base_url="https://www.pestanaleiloes.com.br",
        listings_url_template="https://www.pestanaleiloes.com.br/agenda-de-leiloes?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "MP Leilão": ScraperConfig(
        name="MP Leilão",
        base_url="https://www.mpleilao.com.br",
        listings_url_template="https://www.mpleilao.com.br/leilao?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "123 Leilões": ScraperConfig(
        name="123 Leilões",
        base_url="https://www.123leiloes.com.br",
        listings_url_template="https://www.123leiloes.com.br/imoveis?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "Impacto Leilões": ScraperConfig(
        name="Impacto Leilões",
        base_url="https://www.impactoleiloes.com.br",
        listings_url_template="https://www.impactoleiloes.com.br/lotes?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "Zalli Leilões": ScraperConfig(
        name="Zalli Leilões",
        base_url="https://www.zallileiloes.com.br",
        listings_url_template="https://www.zallileiloes.com.br/lotes?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "Hammer": ScraperConfig(
        name="Hammer",
        base_url="https://www.hammer.lel.br",
        listings_url_template="https://www.hammer.lel.br/busca?page={page}",
        card_selector='div[class*="card"], div[class*="item"]',
    ),
    "Leilão Eletrônico": ScraperConfig(
        name="Leilão Eletrônico",
        base_url="https://www.leilaoeletronico.com.br",
        listings_url_template="https://www.leilaoeletronico.com.br/lotes?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "Topo Leilões": ScraperConfig(
        name="Topo Leilões",
        base_url="https://topoleiloes.com.br",
        listings_url_template="https://topoleiloes.com.br/lotes?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "Sublime Leilões": ScraperConfig(
        name="Sublime Leilões",
        base_url="https://www.sublimeleiloes.com.br",
        listings_url_template="https://www.sublimeleiloes.com.br/lotes?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "Silas Leiloeiro": ScraperConfig(
        name="Silas Leiloeiro",
        base_url="https://silasleiloeiro.lel.br",
        listings_url_template="https://silasleiloeiro.lel.br/busca?page={page}",
        card_selector='div[class*="card"], div[class*="item"]',
    ),
    "Roberto Fernandes": ScraperConfig(
        name="Roberto Fernandes",
        base_url="https://robertofernandesleiloes.com.br",
        listings_url_template="https://robertofernandesleiloes.com.br/lotes?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "Maurício Mariz": ScraperConfig(
        name="Maurício Mariz",
        base_url="https://mauriciomarizleiloes.com.br",
        listings_url_template="https://mauriciomarizleiloes.com.br/lotes?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
    "Taba Leilões": ScraperConfig(
        name="Taba Leilões",
        base_url="https://tabaleiloes.com.br",
        listings_url_template="https://tabaleiloes.com.br/lotes?page={page}",
        card_selector='div[class*="card"], div[class*="lote"]',
    ),
}


class GenericScraper(BaseScraper):
    """Generic scraper that uses configurable selectors."""
    
    def __init__(self, config: ScraperConfig, headless: bool = True):
        super().__init__(headless=headless)
        self.config = config
        
    @property
    def name(self) -> str:
        return self.config.name
        
    @property
    def base_url(self) -> str:
        return self.config.base_url
        
    def get_property_listings_url(self, page: int = 1) -> str:
        return self.config.listings_url_template.format(page=page)
        
    def scrape_listings(self, max_pages: int = 5) -> list[Property]:
        """Scrape property listings using configured selectors."""
        properties = []
        
        for page in range(1, max_pages + 1):
            try:
                url = self.get_property_listings_url(page)
                logger.info(f"Scraping {self.name} page {page}: {url}")
                
                html = self.get_page(url, wait_time=3.0)
                soup = BeautifulSoup(html, 'lxml')
                
                # Find property cards using configured selector
                cards = soup.select(self.config.card_selector)
                
                if not cards:
                    logger.warning(f"No cards found on {self.name} page {page}")
                    # Try broader selectors
                    cards = soup.find_all(['div', 'article'], class_=re.compile(r'.*card.*|.*item.*|.*lote.*', re.I))
                
                logger.info(f"Found {len(cards)} cards on page {page}")
                
                for card in cards:
                    try:
                        prop = self._parse_card(card)
                        if prop:
                            properties.append(prop)
                    except Exception as e:
                        logger.error(f"Error parsing card on {self.name}: {e}")
                        continue
                        
                # Check for next page
                next_btn = soup.select_one(self.config.next_page_selector)
                if not next_btn or next_btn.get('disabled'):
                    break
                    
            except Exception as e:
                logger.error(f"Error scraping {self.name} page {page}: {e}")
                continue
                
        logger.info(f"Scraped {len(properties)} properties from {self.name}")
        return properties
        
    def _parse_card(self, card) -> Optional[Property]:
        """Parse a property card using configured selectors."""
        try:
            # Extract title
            title_elem = card.select_one(self.config.title_selector)
            title = title_elem.get_text(strip=True) if title_elem else "Imóvel em Leilão"
            
            # Extract link
            link_elem = card.select_one(self.config.link_selector)
            url = ""
            if link_elem:
                href = link_elem.get('href', '')
                # Check if it's a property URL
                is_property_url = any(pattern in href for pattern in self.config.property_url_patterns)
                if is_property_url or not url:
                    url = href if href.startswith('http') else f"{self.base_url}{href}"
            
            # Skip if no valid URL
            if not url or url == self.base_url:
                return None
                
            # Extract image (improved detection - ignore logos, small images)
            image_url = self._extract_valid_image(card)
                    
            # Extract location
            location_elem = card.select_one(self.config.location_selector)
            location_text = location_elem.get_text(strip=True) if location_elem else ""
            state, city, neighborhood, address = self._parse_location(location_text)
            
            # Extract price
            price_elem = card.select_one(self.config.price_selector)
            price_text = price_elem.get_text(strip=True) if price_elem else ""
            price = self.parse_currency(price_text)
            
            # Extract category
            category_elem = card.select_one(self.config.category_selector)
            category_text = category_elem.get_text(strip=True) if category_elem else ""
            category = self.normalize_category(category_text or title)
            
            # Extract auction type
            type_elem = card.select_one(self.config.auction_type_selector)
            type_text = type_elem.get_text(strip=True) if type_elem else ""
            auction_type = self.normalize_auction_type(type_text)
            
            # Extract area
            area_elem = card.select_one(self.config.area_selector)
            area_text = area_elem.get_text(strip=True) if area_elem else card.get_text()
            area = self.extract_area(area_text)
            
            # Extract auction dates from card text
            card_text = card.get_text()
            first_auction_date, second_auction_date = self._extract_auction_dates(card_text)
            
            # Check for payment options in card text
            card_text = card.get_text().lower()
            accepts_financing = 'financiamento' in card_text or 'financia' in card_text
            accepts_fgts = 'fgts' in card_text
            accepts_installments = 'parcelamento' in card_text or 'parcela' in card_text
            
            # Extract discount if present
            discount_match = re.search(r'(\d+)\s*%\s*(de\s+)?desconto', card_text, re.I)
            discount = float(discount_match.group(1)) if discount_match else None
            
            # Map category string to PropertyCategory enum
            category_enum = PropertyCategory.OUTROS
            category_lower = category.lower() if category else ""
            if "apartamento" in category_lower:
                category_enum = PropertyCategory.APARTAMENTO
            elif "casa" in category_lower:
                category_enum = PropertyCategory.CASA
            elif "comercial" in category_lower or "loja" in category_lower or "sala" in category_lower:
                category_enum = PropertyCategory.COMERCIAL
            elif "terreno" in category_lower or "lote" in category_lower:
                category_enum = PropertyCategory.TERRENO
            elif "estacionamento" in category_lower or "garagem" in category_lower or "vaga" in category_lower:
                category_enum = PropertyCategory.ESTACIONAMENTO
            
            # Map auction type string to AuctionType enum
            auction_type_enum = AuctionType.OUTROS
            auction_type_lower = auction_type.lower() if auction_type else ""
            if "judicial" in auction_type_lower and "extra" not in auction_type_lower:
                auction_type_enum = AuctionType.JUDICIAL
            elif "extrajudicial" in auction_type_lower:
                auction_type_enum = AuctionType.EXTRAJUDICIAL
            elif "sfi" in auction_type_lower:
                auction_type_enum = AuctionType.LEILAO_SFI
            elif "venda direta" in auction_type_lower:
                auction_type_enum = AuctionType.VENDA_DIRETA
            
            prop = Property(
                id=str(uuid.uuid4()),
                title=title[:200] if title else "Imóvel em Leilão",
                description=title,
                category=category_enum,
                auction_type=auction_type_enum,
                state=state or "SP",
                city=city or "São Paulo",
                neighborhood=neighborhood or "",
                address=address or location_text,
                area_total=area,
                evaluation_value=price,
                first_auction_value=price,
                second_auction_value=price * 0.7 if price else None,
                discount_percentage=discount,
                first_auction_date=first_auction_date,
                second_auction_date=second_auction_date,
                image_url=image_url,
                auctioneer_url=url,
                auctioneer_name=self.name,
                auctioneer_id=self.name.lower().replace(" ", "_"),
                source_url=url,
                accepts_financing=accepts_financing,
                accepts_fgts=accepts_fgts,
                accepts_installments=accepts_installments,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            
            return prop
            
        except Exception as e:
            logger.error(f"Error parsing card: {e}")
            return None
            
    def _parse_location(self, location_text: str) -> tuple[str, str, str, str]:
        """Parse location text into state, city, neighborhood, address."""
        state = ""
        city = ""
        neighborhood = ""
        address = location_text
        
        if not location_text:
            return state, city, neighborhood, address
            
        # Brazilian states
        states = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 
                  'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 
                  'SP', 'SE', 'TO']
        
        # Try to extract state (2 letter code)
        for s in states:
            if f' {s}' in location_text.upper() or f'-{s}' in location_text.upper() or f'/{s}' in location_text.upper():
                state = s
                break
                
        # Try to extract city - usually before the state
        parts = re.split(r'[-,/]', location_text)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) >= 2:
            # Last part is usually state, second to last is city
            for i, part in enumerate(parts):
                if part.upper() in states:
                    if i > 0:
                        city = parts[i-1]
                    break
            else:
                # No state found, assume last is city
                city = parts[-1]
                
            if len(parts) >= 3:
                neighborhood = parts[-3] if len(parts) >= 3 else ""
            if len(parts) >= 4:
                address = ', '.join(parts[:-2])
                
        return state, city, neighborhood, address
        
    def _extract_valid_image(self, card) -> Optional[str]:
        """
        Extract a valid property image, ignoring logos and small images.
        
        Args:
            card: BeautifulSoup element containing property card
            
        Returns:
            Image URL or None
        """
        # Try to find images
        img_elements = card.select('img')
        
        best_image = None
        best_size = 0
        
        for img in img_elements:
            # Get image URL
            image_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ""
            if not image_url:
                continue
            
            # Make URL absolute
            if not image_url.startswith('http'):
                image_url = f"{self.base_url}{image_url}"
            
            # Skip if URL contains logo-related keywords
            image_url_lower = image_url.lower()
            if any(keyword in image_url_lower for keyword in ['logo', 'icon', 'banner', 'header', 'footer', 'avatar']):
                continue
            
            # Get image dimensions if available
            width = None
            height = None
            try:
                width_attr = img.get('width') or img.get('data-width')
                height_attr = img.get('height') or img.get('data-height')
                if width_attr:
                    width = int(str(width_attr).replace('px', ''))
                if height_attr:
                    height = int(str(height_attr).replace('px', ''))
            except (ValueError, TypeError):
                pass
            
            # Skip if image is too small (likely icon/logo) - less than 200px
            if width and width < 200:
                continue
            if height and height < 200:
                continue
            
            # Prefer larger images
            image_size = (width or 0) * (height or 0)
            if image_size > best_size:
                best_size = image_size
                best_image = image_url
        
        return best_image
    
    def _extract_auction_dates(self, text: str) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Extract auction dates from text.
        
        Common patterns:
        - "1ª Praça: 15/01/2025"
        - "Data do Leilão: 20/01/2025"
        - "Encerramento: 25/01/2025 às 14h"
        - "1ª Praça 15/01/2025"
        - "2ª Praça: 20/01/2025"
        
        Returns:
            (first_auction_date, second_auction_date) tuple
        """
        first_date = None
        second_date = None
        
        # Patterns for first auction date
        first_patterns = [
            r'1[ªa]\s*pra[çc]a[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'primeira\s*pra[çc]a[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'data\s*do\s*leil[ãa]o[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'leil[ãa]o[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ]
        
        for pattern in first_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                first_date = self.parse_date(date_str)
                if first_date:
                    break
        
        # Patterns for second auction date
        second_patterns = [
            r'2[ªa]\s*pra[çc]a[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'segunda\s*pra[çc]a[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'encerramento[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ]
        
        for pattern in second_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                second_date = self.parse_date(date_str)
                if second_date:
                    break
        
        return first_date, second_date
    
    def scrape_property_details(self, url: str) -> Optional[Property]:
        """Scrape detailed information for a single property."""
        # For now, return None - detailed scraping can be implemented per-site
        return None


def create_scraper(name: str, headless: bool = True) -> Optional[GenericScraper]:
    """Create a scraper for a known auction site."""
    config = SCRAPER_CONFIGS.get(name)
    if config:
        return GenericScraper(config, headless=headless)
    return None


def get_all_scrapers(headless: bool = True) -> list[GenericScraper]:
    """Get scrapers for all configured auction sites."""
    return [GenericScraper(config, headless=headless) for config in SCRAPER_CONFIGS.values()]
