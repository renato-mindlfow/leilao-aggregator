"""
Pestana Leilões Scraper
Scrapes real estate properties from pestanaleiloes.com.br
Uses Selenium for JavaScript-rendered content
"""

import time
import re
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class PestanaScraper:
    """Scraper for Pestana Leilões website."""
    
    BASE_URL = "https://www.pestanaleiloes.com.br"
    IMOVEIS_URL = f"{BASE_URL}/procurar-bens?tipoBem=462&lotePage=1&loteQty=12"
    
    def __init__(self):
        self.driver = None
        self.properties = []
        self.incomplete_properties = []
    
    def _setup_driver(self):
        """Setup headless Chrome driver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
    
    def _close_driver(self):
        """Close the driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse Brazilian currency format to float."""
        if not price_str:
            return None
        try:
            # Remove "R$", spaces, and convert Brazilian format
            clean = re.sub(r'[R$\s]', '', price_str)
            clean = clean.replace('.', '').replace(',', '.')
            return float(clean)
        except (ValueError, AttributeError):
            return None
    
    def _extract_state_city(self, location_str: str) -> tuple:
        """Extract state and city from location string like 'Fraiburgo - SC'."""
        if not location_str:
            return None, None
        
        parts = location_str.split(' - ')
        if len(parts) >= 2:
            city = parts[0].strip()
            state = parts[-1].strip()
            return state, city
        return None, location_str.strip()
    
    def _determine_category(self, title: str) -> str:
        """Determine property category from title."""
        title_lower = title.lower()
        if 'apartamento' in title_lower:
            return 'Apartamento'
        elif 'casa' in title_lower:
            return 'Casa'
        elif 'terreno' in title_lower:
            return 'Terreno'
        elif 'prédio' in title_lower or 'predio' in title_lower:
            return 'Comercial'
        elif 'loja' in title_lower or 'sala' in title_lower or 'comercial' in title_lower:
            return 'Comercial'
        elif 'galpão' in title_lower or 'galpao' in title_lower:
            return 'Comercial'
        elif 'área rural' in title_lower or 'fazenda' in title_lower or 'sítio' in title_lower:
            return 'Terreno'
        return 'Comercial'
    
    def scrape_properties(self, max_properties: int = None) -> List[Dict]:
        """Scrape properties from Pestana Leilões."""
        print(f"Starting Pestana Leilões scraper (max {max_properties} properties)...")
        
        try:
            self._setup_driver()
            
            # Navigate to real estate listings
            print(f"Navigating to {self.IMOVEIS_URL}")
            self.driver.get(self.IMOVEIS_URL)
            
            # Wait for page to load
            time.sleep(5)
            
            # Wait for property cards to appear
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/agenda-de-leiloes/']"))
                )
            except TimeoutException:
                print("Timeout waiting for property cards")
                return []
            
            # Find all property links
            property_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/agenda-de-leiloes/']")
            
            # Filter to unique property URLs
            seen_urls = set()
            unique_links = []
            for link in property_links:
                href = link.get_attribute('href')
                if href and '/agenda-de-leiloes/' in href and href not in seen_urls:
                    # Check if it's a property page (has two path segments after agenda-de-leiloes)
                    parts = href.split('/agenda-de-leiloes/')
                    if len(parts) > 1 and '/' in parts[1]:
                        seen_urls.add(href)
                        unique_links.append(href)
            
            print(f"Found {len(unique_links)} unique property links")
            
            # Scrape each property
            for i, url in enumerate(unique_links[:max_properties]):
                print(f"Scraping property {i+1}/{min(len(unique_links), max_properties)}: {url}")
                property_data = self._scrape_property_page(url)
                
                if property_data:
                    if self._is_complete(property_data):
                        self.properties.append(property_data)
                        print(f"  Added: {property_data['title']}")
                    else:
                        self.incomplete_properties.append(property_data)
                        print(f"  Incomplete: {property_data.get('title', 'Unknown')}")
                
                # Be polite to the server
                time.sleep(2)
            
            print(f"\nScraping complete!")
            print(f"Complete properties: {len(self.properties)}")
            print(f"Incomplete properties: {len(self.incomplete_properties)}")
            
            return self.properties
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            return []
        finally:
            self._close_driver()
    
    def _scrape_property_page(self, url: str) -> Optional[Dict]:
        """Scrape a single property page."""
        try:
            self.driver.get(url)
            time.sleep(3)
            
            property_data = {
                'source_url': url,
                'auctioneer_url': url,
                'auctioneer_name': 'Pestana Leiloes',
                'auctioneer_id': 'pestana_leiloes',
            }
            
            # Extract title - use h1 in main content area (not header)
            try:
                # The property title is in an h1 tag within main content
                title_elem = self.driver.find_element(By.CSS_SELECTOR, "main h1")
                property_data['title'] = title_elem.text.strip()
            except NoSuchElementException:
                try:
                    # Fallback to h2 with title attribute
                    title_elem = self.driver.find_element(By.CSS_SELECTOR, "h2[title]")
                    property_data['title'] = title_elem.get_attribute('title') or title_elem.text
                except NoSuchElementException:
                    property_data['title'] = None
            
            # Extract location from title (format: "Type - City - State")
            if property_data.get('title'):
                state, city = self._extract_state_city(property_data['title'])
                property_data['state'] = state
                property_data['city'] = city
                property_data['category'] = self._determine_category(property_data['title'])
            
            # Extract image
            try:
                img_elem = self.driver.find_element(By.CSS_SELECTOR, "img[src*='ged.pestanaleiloes.com.br']")
                property_data['image_url'] = img_elem.get_attribute('src')
            except NoSuchElementException:
                property_data['image_url'] = None
            
            # Extract prices
            page_text = self.driver.page_source
            
            # Look for "Lance mínimo" or "Lance inicial" (with or without colon)
            lance_match = re.search(r'Lance\s+(?:mínimo|inicial):?\s*R\$\s*([\d.,]+)', page_text)
            if lance_match:
                property_data['second_auction_value'] = self._parse_price(lance_match.group(1))
            
            # Look for evaluation value
            avaliacao_match = re.search(r'Avaliação:\s*R\$\s*([\d.,]+)', page_text)
            if avaliacao_match:
                property_data['evaluation_value'] = self._parse_price(avaliacao_match.group(1))
            else:
                # If no evaluation, use lance value as both
                property_data['evaluation_value'] = property_data.get('second_auction_value')
            
            # Set first auction value (usually same as evaluation)
            property_data['first_auction_value'] = property_data.get('evaluation_value')
            
            # Calculate discount
            if property_data.get('evaluation_value') and property_data.get('second_auction_value'):
                discount = ((property_data['evaluation_value'] - property_data['second_auction_value']) / property_data['evaluation_value']) * 100
                property_data['discount_percentage'] = round(discount, 1)
            else:
                property_data['discount_percentage'] = 0
            
            # Determine auction type (most Pestana properties are extrajudicial/retomado)
            if 'judicial' in page_text.lower():
                property_data['auction_type'] = 'Judicial'
            else:
                property_data['auction_type'] = 'Extrajudicial'
            
            # Extract area if available
            area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m²', page_text)
            if area_match:
                property_data['area_total'] = float(area_match.group(1).replace(',', '.'))
            else:
                property_data['area_total'] = None
            
            return property_data
            
        except Exception as e:
            print(f"  Error scraping property: {e}")
            return None
    
    def _is_complete(self, property_data: Dict) -> bool:
        """Check if property has all required fields."""
        required_fields = ['title', 'state', 'city', 'second_auction_value', 'image_url', 'source_url']
        for field in required_fields:
            if not property_data.get(field):
                return False
        return True


def main():
    """Test the scraper."""
    scraper = PestanaScraper()
    properties = scraper.scrape_properties(max_properties=10)
    
    print("\n" + "="*50)
    print("SCRAPED PROPERTIES:")
    print("="*50)
    
    for i, prop in enumerate(properties, 1):
        print(f"\n{i}. {prop.get('title', 'Unknown')}")
        print(f"   Location: {prop.get('city')}, {prop.get('state')}")
        print(f"   Category: {prop.get('category')}")
        print(f"   Price: R$ {prop.get('second_auction_value', 0):,.2f}")
        print(f"   Discount: {prop.get('discount_percentage', 0)}%")
        print(f"   URL: {prop.get('source_url')}")
        print(f"   Image: {prop.get('image_url', 'N/A')[:50]}...")


if __name__ == "__main__":
    main()
