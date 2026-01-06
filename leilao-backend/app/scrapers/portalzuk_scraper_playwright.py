"""
Portal Zukerman Scraper
Scrapes real estate properties from portalzuk.com.br
Uses Playwright with Stealth configuration to bypass browser detection
Adapted from PestanaScraper for Portal Zukerman structure
"""

import asyncio
import re
import logging
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.structure_validator import structure_validator

logger = logging.getLogger(__name__)


class PortalZukScraperPlaywright:
    """Scraper for Portal Zukerman website using Playwright with Stealth."""
    
    BASE_URL = "https://www.portalzuk.com.br"
    IMOVEIS_URL = f"{BASE_URL}/leilao-de-imoveis/u/todos-imoveis/sp"  # Começar com SP
    AUCTIONEER_ID = "portal_zuk"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.properties: List[Dict] = []
        self.incomplete_properties: List[Dict] = []
    
    async def _setup_browser(self):
        """Setup Playwright browser with stealth configuration."""
        playwright = await async_playwright().start()
        
        # Configurações de stealth para evitar detecção
        browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-infobars',
                '--disable-notifications',
            ]
        )
        
        # Criar contexto com configurações de stealth
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            permissions=['geolocation'],
            extra_http_headers={
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        )
        
        # Criar página
        page = await context.new_page()
        
        # Injetar scripts de stealth para ocultar automação
        await page.add_init_script("""
            // Ocultar webdriver - método mais robusto
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            
            // Remover webdriver do navigator
            delete navigator.__proto__.webdriver;
            
            // Sobrescrever plugins com objeto real
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugins = [];
                    for (let i = 0; i < 5; i++) {
                        plugins.push({
                            name: `Plugin ${i}`,
                            description: `Description ${i}`,
                            filename: `plugin${i}.dll`
                        });
                    }
                    return plugins;
                }
            });
            
            // Sobrescrever languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en']
            });
            
            // Sobrescrever permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Ocultar chrome com propriedades completas
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Sobrescrever getBattery
            if (navigator.getBattery) {
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                });
            }
            
            // Sobrescrever platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            
            // Sobrescrever hardwareConcurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // Sobrescrever deviceMemory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            
            // Sobrescrever maxTouchPoints
            Object.defineProperty(navigator, 'maxTouchPoints', {
                get: () => 0
            });
            
            // Adicionar propriedades que navegadores reais têm
            Object.defineProperty(navigator, 'vendor', {
                get: () => 'Google Inc.'
            });
            
            // Sobrescrever onLine
            Object.defineProperty(navigator, 'onLine', {
                get: () => true
            });
            
            // Sobrescrever cookieEnabled
            Object.defineProperty(navigator, 'cookieEnabled', {
                get: () => true
            });
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
            # Remove "R$", spaces, and convert Brazilian format
            clean = re.sub(r'[R$\s]', '', price_str)
            clean = clean.replace('.', '').replace(',', '.')
            return float(clean)
        except (ValueError, AttributeError):
            return None
    
    def _extract_state_city(self, location_str: str) -> tuple:
        """Extract state and city from location string."""
        if not location_str:
            return None, None
        
        # Portal Zuk pode ter formatos diferentes
        # Tentar "City - State" primeiro
        parts = location_str.split(' - ')
        if len(parts) >= 2:
            city = parts[0].strip()
            state = parts[-1].strip()
            return state, city
        
        # Tentar "City, State"
        parts = location_str.split(', ')
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
        elif 'prédio' in title_lower or 'predio' in title_lower:
            return 'Comercial'
        elif 'loja' in title_lower or 'sala' in title_lower or 'comercial' in title_lower:
            return 'Comercial'
        elif 'galpão' in title_lower or 'galpao' in title_lower:
            return 'Comercial'
        elif 'área rural' in title_lower or 'fazenda' in title_lower or 'sítio' in title_lower:
            return 'Terreno'
        return 'Comercial'
    
    def scrape_properties(self, max_properties: Optional[int] = None) -> List[Dict]:
        """
        Scrape properties from Portal Zukerman.
        Método síncrono que chama a versão assíncrona internamente.
        
        Verifica se há um loop de eventos rodando antes de usar asyncio.run().
        - Se não houver loop rodando: usa asyncio.run() normalmente
        - Se houver loop rodando: executa em thread separada para evitar conflito
        
        Nota: Se você estiver em um contexto async, considere usar
        _scrape_properties_async() diretamente com await.
        """
        try:
            # Tenta obter o loop de eventos rodando
            loop = asyncio.get_running_loop()
            # Se chegou aqui, há um loop rodando
            # Não podemos usar asyncio.run() porque já estamos em um loop
            # Executar em thread separada para evitar conflito com o loop existente
            logger.debug("Loop de eventos já está rodando. Executando em thread separada.")
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._scrape_properties_async(max_properties))
                return future.result()
        except RuntimeError:
            # Não há loop rodando, podemos usar asyncio.run() normalmente
            return asyncio.run(self._scrape_properties_async(max_properties))
    
    async def _scrape_properties_async(self, max_properties: Optional[int] = None) -> List[Dict]:
        """Scrape properties from Portal Zukerman (versão assíncrona)."""
        logger.info(f"Iniciando scraping do Portal Zukerman (max {max_properties} imóveis)...")
        
        try:
            await self._setup_browser()
            
            # Navegar para página de imóveis
            logger.info(f"Navegando para {self.IMOVEIS_URL}")
            await self.page.goto(self.IMOVEIS_URL, wait_until='domcontentloaded', timeout=120000)
            
            # Aguardar JavaScript carregar
            await asyncio.sleep(5)
            
            # Verificar se há bloqueio
            page_text = await self.page.evaluate("() => document.body.innerText")
            page_content = await self.page.content()
            
            bloqueios = ['navegador incompatível', 'browser incompatible', 'acesso negado', 'access denied']
            bloqueio_encontrado = any(bloqueio in page_text.lower() or bloqueio in page_content.lower() for bloqueio in bloqueios)
            
            if bloqueio_encontrado:
                logger.warning("⚠️ Possível bloqueio detectado, mas continuando...")
                await asyncio.sleep(5)
            
            # Scroll para carregar conteúdo lazy
            await self._scroll_to_load_content()
            
            # Aguardar elementos de imóveis aparecerem
            try:
                # Portal Zuk usa diferentes seletores
                await self.page.wait_for_selector(
                    "a[href*='/imovel/'], .property-card, [class*='property'], [class*='imovel']",
                    timeout=30000
                )
                logger.info("✅ Elementos de imóveis detectados")
            except PlaywrightTimeoutError:
                logger.warning("⚠️ Timeout aguardando elementos, tentando continuar...")
                await asyncio.sleep(2)
            
            # Encontrar todos os links de propriedades
            # Portal Zuk usa /imovel/ nas URLs
            property_links = await self.page.query_selector_all("a[href*='/imovel/']")
            
            # Filtrar URLs únicas
            seen_urls = set()
            unique_links = []
            for link in property_links:
                href = await link.get_attribute('href')
                if href and '/imovel/' in href and href not in seen_urls:
                    full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                    seen_urls.add(full_url)
                    unique_links.append(full_url)
            
            logger.info(f"Encontrados {len(unique_links)} links únicos de propriedades")
            
            # Scrape cada propriedade
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
                
                # Pausa entre requisições
                await asyncio.sleep(2)
            
            logger.info(f"\nScraping completo!")
            logger.info(f"Propriedades completas: {len(self.properties)}")
            logger.info(f"Propriedades incompletas: {len(self.incomplete_properties)}")
            
            # Atualizar métricas usando structure_validator
            try:
                structure_validator.update_validation_metrics(
                    auctioneer_id=self.AUCTIONEER_ID,
                    success=len(self.properties) > 0,
                    properties_count=len(self.properties)
                )
                logger.info("✅ Métricas de validação atualizadas")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao atualizar métricas: {e}")
            
            return self.properties
            
        except Exception as e:
            logger.error(f"❌ Erro durante scraping: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            
            # Atualizar métricas de falha
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
                'auctioneer_name': 'Portal Zukerman',
                'auctioneer_id': self.AUCTIONEER_ID,
            }
            
            # Extrair título - Portal Zuk pode usar diferentes seletores
            try:
                # Tentar vários seletores comuns
                title_selectors = ["h1", "h2.title", ".property-title", "[class*='title']"]
                title_elem = None
                for selector in title_selectors:
                    title_elem = await self.page.query_selector(selector)
                    if title_elem:
                        break
                
                if title_elem:
                    property_data['title'] = await title_elem.inner_text()
                    property_data['title'] = property_data['title'].strip()
                else:
                    property_data['title'] = None
            except Exception as e:
                logger.debug(f"Erro ao extrair título: {e}")
                property_data['title'] = None
            
            # Extrair localização
            if property_data.get('title'):
                state, city = self._extract_state_city(property_data['title'])
                property_data['state'] = state
                property_data['city'] = city
                property_data['category'] = self._determine_category(property_data['title'])
            
            # Extrair imagem
            try:
                img_selectors = ["img[src*='portalzuk'], img.property-image, .property-image img"]
                img_elem = None
                for selector in img_selectors:
                    img_elem = await self.page.query_selector(selector)
                    if img_elem:
                        break
                
                if img_elem:
                    property_data['image_url'] = await img_elem.get_attribute('src')
                else:
                    property_data['image_url'] = None
            except Exception as e:
                logger.debug(f"Erro ao extrair imagem: {e}")
                property_data['image_url'] = None
            
            # Extrair preços
            page_text = await self.page.content()
            page_visible_text = await self.page.evaluate("() => document.body.innerText")
            
            # Procurar por valores em R$
            price_patterns = [
                r'Lance\s+(?:mínimo|inicial):?\s*R\$\s*([\d.,]+)',
                r'Valor\s+(?:mínimo|inicial):?\s*R\$\s*([\d.,]+)',
                r'R\$\s*([\d]{1,3}(?:\.[\d]{3})*(?:,\d{2})?)',
            ]
            
            price = None
            for pattern in price_patterns:
                match = re.search(pattern, page_visible_text, re.IGNORECASE)
                if match:
                    price = self._parse_price(match.group(1))
                    if price:
                        break
            
            property_data['price'] = price
            property_data['second_auction_value'] = price
            
            # Procurar avaliação
            avaliacao_match = re.search(r'Avaliação:\s*R\$\s*([\d.,]+)', page_visible_text, re.IGNORECASE)
            if avaliacao_match:
                property_data['evaluation_value'] = self._parse_price(avaliacao_match.group(1))
            else:
                property_data['evaluation_value'] = price
            
            property_data['first_auction_value'] = property_data.get('evaluation_value')
            
            # Calcular desconto
            if property_data.get('evaluation_value') and property_data.get('second_auction_value'):
                discount = ((property_data['evaluation_value'] - property_data['second_auction_value']) / property_data['evaluation_value']) * 100
                property_data['discount_percentage'] = round(discount, 1)
            else:
                property_data['discount_percentage'] = 0
            
            # Tipo de leilão
            if 'judicial' in page_text.lower():
                property_data['auction_type'] = 'Judicial'
            else:
                property_data['auction_type'] = 'Extrajudicial'
            
            # Área
            area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m²', page_text, re.IGNORECASE)
            if area_match:
                property_data['area_total'] = float(area_match.group(1).replace(',', '.'))
            else:
                property_data['area_total'] = None
            
            return property_data
            
        except Exception as e:
            logger.error(f"  ❌ Erro ao fazer scraping da propriedade: {e}")
            import traceback
            logger.debug(traceback.format_exc())
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


async def main():
    """Test the scraper."""
    scraper = PortalZukScraperPlaywright(headless=True)
    properties = scraper.scrape_properties(max_properties=10)
    
    print("\n" + "="*50)
    print("SCRAPED PROPERTIES:")
    print("="*50)
    
    for i, prop in enumerate(properties, 1):
        print(f"\n{i}. {prop.get('title', 'Unknown')}")
        print(f"   Location: {prop.get('city')}, {prop.get('state')}")
        print(f"   Category: {prop.get('category')}")
        print(f"   Price: R$ {prop.get('price', 0) or 0:,.2f}")
        print(f"   URL: {prop.get('source_url')}")


if __name__ == "__main__":
    asyncio.run(main())

