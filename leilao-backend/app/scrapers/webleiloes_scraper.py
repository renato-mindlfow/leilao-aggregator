"""
Web Leilões Scraper
Scrapes real estate properties from webleiloes.com.br
Uses Playwright with Stealth configuration to bypass Cloudflare
"""

import asyncio
import re
import logging
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.structure_validator import structure_validator

logger = logging.getLogger(__name__)


class WebLeiloesScraper:
    """Scraper for Web Leilões website using Playwright with Stealth."""
    
    BASE_URL = "https://www.webleiloes.com.br"
    IMOVEIS_URL = f"{BASE_URL}/imoveis"
    AUCTIONEER_ID = "web_leiloes"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.properties: List[Dict] = []
        self.incomplete_properties: List[Dict] = []
    
    async def _setup_browser(self):
        """Setup Playwright browser with stealth configuration."""
        playwright = await async_playwright().start()
        
        browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--window-size=1920,1080',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            extra_http_headers={
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
        )
        
        page = await context.new_page()
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)
        
        self.browser = browser
        self.page = page
        self.playwright = playwright
        
        return page
    
    async def _close_browser(self):
        """Close the browser."""
        if self.page:
            await self.page.close()
            self.page = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse Brazilian currency format to float."""
        if not price_str:
            return None
        try:
            clean = re.sub(r'[R$\s]', '', price_str)
            clean = clean.replace('.', '').replace(',', '.')
            return float(clean)
        except (ValueError, AttributeError):
            return None
    
    def _extract_state_city(self, location_str: str) -> tuple:
        """Extract state and city from location string."""
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
        if not title:
            return 'Outro'
        
        title_lower = title.lower()
        if 'apartamento' in title_lower:
            return 'Apartamento'
        elif 'casa' in title_lower:
            return 'Casa'
        elif 'terreno' in title_lower:
            return 'Terreno'
        elif 'comercial' in title_lower or 'loja' in title_lower:
            return 'Comercial'
        return 'Comercial'
    
    def scrape_properties(self, max_properties: Optional[int] = None) -> List[Dict]:
        """Scrape properties from Web Leilões."""
        return asyncio.run(self._scrape_properties_async(max_properties))
    
    async def _scrape_properties_async(self, max_properties: Optional[int] = None) -> List[Dict]:
        """Scrape properties from Web Leilões (async version)."""
        logger.info(f"Iniciando scraping do Web Leilões (max {max_properties} imóveis)...")
        
        try:
            await self._setup_browser()
            
            logger.info(f"Navegando para {self.IMOVEIS_URL}")
            await self.page.goto(self.IMOVEIS_URL, wait_until='networkidle', timeout=60000)
            
            await asyncio.sleep(5)
            
            await self._scroll_to_load_content()
            
            # Encontrar links de imóveis
            property_links = await self.page.query_selector_all("a[href*='/imovel'], a[href*='/lote'], a[href*='/leilao']")
            
            seen_urls = set()
            unique_links = []
            for link in property_links:
                href = await link.get_attribute('href')
                if href:
                    full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)
                        unique_links.append(full_url)
            
            logger.info(f"Encontrados {len(unique_links)} links únicos de propriedades")
            
            for i, url in enumerate(unique_links[:max_properties] if max_properties else unique_links):
                logger.info(f"Scraping propriedade {i+1}/{min(len(unique_links), max_properties or len(unique_links))}: {url}")
                property_data = await self._scrape_property_page(url)
                
                if property_data:
                    if self._is_complete(property_data):
                        self.properties.append(property_data)
                        logger.info(f"  ✅ Adicionado: {property_data['title']}")
                    else:
                        self.incomplete_properties.append(property_data)
                        logger.warning(f"  ⚠️ Incompleto: {property_data.get('title', 'Unknown')}")
                
                await asyncio.sleep(2)
            
            logger.info(f"\nScraping completo!")
            logger.info(f"Propriedades completas: {len(self.properties)}")
            
            try:
                structure_validator.update_validation_metrics(
                    auctioneer_id=self.AUCTIONEER_ID,
                    success=len(self.properties) > 0,
                    properties_count=len(self.properties)
                )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao atualizar métricas: {e}")
            
            return self.properties
            
        except Exception as e:
            logger.error(f"❌ Erro durante scraping: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            
            try:
                structure_validator.update_validation_metrics(
                    auctioneer_id=self.AUCTIONEER_ID,
                    success=False,
                    properties_count=0
                )
            except:
                pass
            
            return []
        finally:
            await self._close_browser()
    
    async def _scroll_to_load_content(self):
        """Scroll page to load lazy-loaded content."""
        if not self.page:
            return
        
        try:
            await self.page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 100;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            
                            if(totalHeight >= scrollHeight){
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            await asyncio.sleep(2)
        except Exception as e:
            logger.debug(f"Erro ao fazer scroll: {e}")
    
    async def _scrape_property_page(self, url: str) -> Optional[Dict]:
        """Scrape a single property page."""
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            property_data = {
                'source_url': url,
                'url': url,
                'auctioneer_url': url,
                'auctioneer_name': 'Web Leilões',
                'auctioneer_id': self.AUCTIONEER_ID,
            }
            
            # Extrair título
            try:
                title_elem = await self.page.query_selector("h1, h2.title, .title")
                if title_elem:
                    property_data['title'] = await title_elem.inner_text()
                    property_data['title'] = property_data['title'].strip()
                else:
                    property_data['title'] = None
            except Exception as e:
                logger.debug(f"Erro ao extrair título: {e}")
                property_data['title'] = None
            
            # Extrair localização
            page_visible_text = await self.page.evaluate("() => document.body.innerText")
            
            location_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[-/]\s*([A-Z]{2})', page_visible_text)
            if location_match:
                property_data['city'] = location_match.group(1).strip()
                property_data['state'] = location_match.group(2).strip()
            else:
                property_data['state'] = None
                property_data['city'] = None
            
            if property_data.get('title'):
                property_data['category'] = self._determine_category(property_data['title'])
            
            # Extrair imagem
            try:
                img_elem = await self.page.query_selector("img[src*='webleiloes'], .property-image img")
                if img_elem:
                    property_data['image_url'] = await img_elem.get_attribute('src')
                else:
                    property_data['image_url'] = None
            except Exception as e:
                logger.debug(f"Erro ao extrair imagem: {e}")
                property_data['image_url'] = None
            
            # Extrair preço
            page_text = await self.page.content()
            price_match = re.search(r'Lance\s+(?:mínimo|inicial):?\s*R\$\s*([\d.,]+)', page_text, re.IGNORECASE)
            if not price_match:
                price_match = re.search(r'R\$\s*([\d]{1,3}(?:\.[\d]{3})*(?:,\d{2})?)', page_visible_text)
            
            if price_match:
                property_data['price'] = self._parse_price(price_match.group(1))
                property_data['second_auction_value'] = property_data['price']
            else:
                property_data['price'] = None
                property_data['second_auction_value'] = None
            
            # Tipo de leilão
            if 'judicial' in page_text.lower():
                property_data['auction_type'] = 'Judicial'
            else:
                property_data['auction_type'] = 'Extrajudicial'
            
            return property_data
            
        except Exception as e:
            logger.error(f"  ❌ Erro ao fazer scraping da propriedade: {e}")
            return None
    
    def _is_complete(self, property_data: Dict) -> bool:
        """Check if property has all required fields."""
        required_fields = ['title', 'source_url']
        important_fields = ['state', 'city', 'price']
        
        for field in required_fields:
            if not property_data.get(field):
                return False
        
        important_count = sum(1 for field in important_fields if property_data.get(field))
        return important_count >= 2


if __name__ == "__main__":
    scraper = WebLeiloesScraper(headless=True)
    properties = scraper.scrape_properties(max_properties=5)
    print(f"\nTotal: {len(properties)} imóveis extraídos")

