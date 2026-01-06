"""
Base scraper class for auction websites.
All specific scrapers should inherit from this class.
"""
import logging
import time
import re
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from bs4 import BeautifulSoup

from app.models.property import Property, PropertyCategory, AuctionType

logger = logging.getLogger(__name__)

# Lazy imports para Selenium - só importa quando necessário
if TYPE_CHECKING:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException


class BaseScraper(ABC):
    """Base class for all auction website scrapers."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver: Optional['webdriver.Chrome'] = None
        self.wait: Optional['WebDriverWait'] = None
    
    def _ensure_selenium(self):
        """Lazy import of Selenium - only import when needed."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, NoSuchElementException
            from webdriver_manager.chrome import ChromeDriverManager
            
            # Store in class for reuse
            BaseScraper._selenium_imported = True
            BaseScraper._webdriver = webdriver
            BaseScraper._Service = Service
            BaseScraper._Options = Options
            BaseScraper._By = By
            BaseScraper._WebDriverWait = WebDriverWait
            BaseScraper._EC = EC
            BaseScraper._TimeoutException = TimeoutException
            BaseScraper._NoSuchElementException = NoSuchElementException
            BaseScraper._ChromeDriverManager = ChromeDriverManager
        except ImportError as e:
            raise ImportError(
                "Selenium is required for BaseScraper. Install it with: pip install selenium webdriver-manager"
            ) from e
        
    def setup_driver(self) -> None:
        """Setup Chrome WebDriver with headless options."""
        self._ensure_selenium()
        Options = BaseScraper._Options
        Service = BaseScraper._Service
        ChromeDriverManager = BaseScraper._ChromeDriverManager
        webdriver = BaseScraper._webdriver
        
        options = Options()
        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        WebDriverWait = BaseScraper._WebDriverWait
        self.wait = WebDriverWait(self.driver, 10)
        
    def close_driver(self) -> None:
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None
            
    def get_page(self, url: str, wait_time: float = 2.0) -> str:
        """Navigate to a URL and return the page source."""
        if not self.driver:
            self.setup_driver()
        
        self.driver.get(url)
        time.sleep(wait_time)  # Wait for dynamic content to load
        return self.driver.page_source
    
    def scroll_to_bottom(self, pause_time: float = 1.0) -> None:
        """Scroll to the bottom of the page to load lazy content."""
        if not self.driver:
            return
            
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
    def wait_for_element(self, by: str, value: str, timeout: int = 10) -> bool:
        """Wait for an element to be present on the page."""
        self._ensure_selenium()
        By = BaseScraper._By
        WebDriverWait = BaseScraper._WebDriverWait
        EC = BaseScraper._EC
        TimeoutException = BaseScraper._TimeoutException
        
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False
            
    @staticmethod
    def parse_currency(value: str) -> Optional[float]:
        """Parse Brazilian currency string to float."""
        if not value:
            return None
        # Remove currency symbol, dots (thousands separator), and replace comma with dot
        cleaned = re.sub(r'[R$\s]', '', value)
        cleaned = cleaned.replace('.', '').replace(',', '.')
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None
            
    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """Parse Brazilian date string to datetime."""
        if not date_str:
            return None
        
        # Common date formats in Brazilian auction sites
        formats = [
            '%d/%m/%Y',
            '%d/%m/%Y %H:%M',
            '%d/%m/%Y às %H:%M',
            '%d/%m/%y',
            '%d-%m-%Y',
            '%Y-%m-%d',
        ]
        
        # Clean the date string
        date_str = date_str.strip()
        date_str = re.sub(r'\s+', ' ', date_str)
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
        
    @staticmethod
    def extract_area(text: str) -> Optional[float]:
        """Extract area in m² from text."""
        if not text:
            return None
        # Match patterns like "100m²", "100 m²", "100,5m²", "100.5 m2"
        match = re.search(r'([\d.,]+)\s*m[²2]', text, re.IGNORECASE)
        if match:
            area_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                return float(area_str)
            except ValueError:
                return None
        return None
        
    @staticmethod
    def normalize_category(category: str) -> str:
        """Normalize property category to standard values."""
        if not category:
            return "Outros"
            
        category_lower = category.lower().strip()
        
        if any(term in category_lower for term in ['apartamento', 'apto', 'flat', 'cobertura', 'kitnet', 'loft']):
            return "Apartamento"
        elif any(term in category_lower for term in ['casa', 'sobrado', 'residência', 'residencia', 'chácara', 'chacara', 'sítio', 'sitio', 'fazenda']):
            return "Casa"
        elif any(term in category_lower for term in ['comercial', 'loja', 'sala', 'galpão', 'galpao', 'prédio', 'predio', 'escritório', 'escritorio', 'ponto']):
            return "Comercial"
        elif any(term in category_lower for term in ['terreno', 'lote', 'área', 'area', 'gleba']):
            return "Terreno"
        elif any(term in category_lower for term in ['garagem', 'vaga', 'estacionamento', 'box']):
            return "Estacionamento"
        else:
            return "Outros"
            
    @staticmethod
    def normalize_auction_type(auction_type: str) -> str:
        """Normalize auction type to standard values."""
        if not auction_type:
            return "Outros"
            
        type_lower = auction_type.lower().strip()
        
        if 'judicial' in type_lower:
            return "Judicial"
        elif 'extrajudicial' in type_lower:
            return "Extrajudicial"
        elif 'sfi' in type_lower or 'alienação fiduciária' in type_lower:
            return "Leilão SFI"
        elif 'venda direta' in type_lower or 'venda online' in type_lower:
            return "Venda Direta"
        else:
            return "Outros"
            
    @staticmethod
    def calculate_discount(evaluation_value: Optional[float], auction_value: Optional[float]) -> Optional[float]:
        """Calculate discount percentage."""
        if not evaluation_value or not auction_value or evaluation_value <= 0:
            return None
        discount = ((evaluation_value - auction_value) / evaluation_value) * 100
        return round(max(0, discount), 1)
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the auctioneer."""
        pass
        
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL of the auction website."""
        pass
        
    @abstractmethod
    def get_property_listings_url(self, page: int = 1) -> str:
        """Return the URL for property listings page."""
        pass
        
    @abstractmethod
    def scrape_listings(self, max_pages: int = 5) -> list[Property]:
        """Scrape property listings from the website."""
        pass
        
    @abstractmethod
    def scrape_property_details(self, url: str) -> Optional[Property]:
        """Scrape detailed information for a single property."""
        pass
