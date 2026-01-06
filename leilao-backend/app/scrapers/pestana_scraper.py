"""
Pestana Leilões Scraper
Scrapes real estate properties from pestanaleiloes.com.br
Uses Playwright with Stealth configuration to bypass browser detection
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


class PestanaScraper:
    """Scraper for Pestana Leilões website using Playwright with Stealth."""
    
    BASE_URL = "https://www.pestanaleiloes.com.br"
    IMOVEIS_URL = f"{BASE_URL}/procurar-bens?tipoBem=462&lotePage=1&loteQty=50"
    AUCTIONEER_ID = "pestana_leiloes"
    
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
        Scrape properties from Pestana Leilões.
        Método síncrono que chama a versão assíncrona internamente.
        """
        return asyncio.run(self._scrape_properties_async(max_properties))
    
    async def _scrape_properties_async(self, max_properties: Optional[int] = None) -> List[Dict]:
        """Scrape properties from Pestana Leilões (versão assíncrona)."""
        logger.info(f"Iniciando scraping do Pestana Leilões (max {max_properties} imóveis)...")
        
        try:
            await self._setup_browser()
            
            # Navegar para página de imóveis
            logger.info(f"Navegando para {self.IMOVEIS_URL}")
            await self.page.goto(self.IMOVEIS_URL, wait_until='networkidle', timeout=60000)
            
            # Aguardar um pouco para JavaScript carregar
            await asyncio.sleep(3)
            
            # Verificar se não há mensagem de navegador incompatível
            # Aguardar um pouco mais para JavaScript carregar completamente
            await asyncio.sleep(5)
            
            # Verificar se há mensagem de erro
            page_content = await self.page.content()
            page_text = await self.page.evaluate("() => document.body.innerText")
            
            if 'navegador incompatível' in page_content.lower() or 'navegador incompativel' in page_text.lower():
                logger.warning("⚠️ Mensagem de 'Navegador Incompatível' detectada, mas continuando...")
                # Tentar aguardar mais e verificar se o conteúdo carrega mesmo assim
                await asyncio.sleep(5)
                page_text = await self.page.evaluate("() => document.body.innerText")
                if 'navegador incompatível' in page_text.lower() and len(page_text) < 500:
                    logger.error("❌ Bloqueio persistente - página não carregou conteúdo")
                    # Mesmo assim, tentar continuar - pode ser que os elementos estejam lá
                else:
                    logger.info("✅ Conteúdo carregou apesar da mensagem inicial")
            
            # Aguardar elementos de leilões aparecerem
            try:
                # Aguardar por links de leilões ou cards
                await self.page.wait_for_selector(
                    "a[href*='/agenda-de-leiloes/'], .card, [class*='lote'], [class*='imovel']",
                    timeout=30000
                )
                logger.info("✅ Elementos de leilões detectados")
            except PlaywrightTimeoutError:
                logger.warning("⚠️ Timeout aguardando elementos de leilões")
                # Continuar mesmo assim, pode ter carregado
                # Tentar encontrar elementos mesmo sem wait
                await asyncio.sleep(2)
            
            # Scroll para carregar conteúdo lazy
            await self._scroll_to_load_content()
            
            # Encontrar todos os links de propriedades
            property_links = await self.page.query_selector_all("a[href*='/agenda-de-leiloes/']")
            
            # Filtrar URLs únicas
            seen_urls = set()
            unique_links = []
            for link in property_links:
                href = await link.get_attribute('href')
                if href and '/agenda-de-leiloes/' in href and href not in seen_urls:
                    # Verificar se é uma página de propriedade (tem dois segmentos após agenda-de-leiloes)
                    parts = href.split('/agenda-de-leiloes/')
                    if len(parts) > 1 and '/' in parts[1]:
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
            # Scroll suave até o final
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
            await asyncio.sleep(2)  # Aguardar conteúdo carregar
        except Exception as e:
            logger.debug(f"Erro ao fazer scroll: {e}")
    
    async def _scrape_property_page(self, url: str) -> Optional[Dict]:
        """Scrape a single property page."""
        try:
            # Usar 'domcontentloaded' em vez de 'networkidle' para ser mais rápido
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)  # Aguardar JavaScript carregar
            
            property_data = {
                'source_url': url,
                'url': url,
                'auctioneer_url': url,
                'auctioneer_name': 'Pestana Leilões',
                'auctioneer_id': self.AUCTIONEER_ID,
            }
            
            # Extrair título - usar h1 no conteúdo principal
            try:
                title_elem = await self.page.query_selector("main h1")
                if title_elem:
                    property_data['title'] = await title_elem.inner_text()
                    property_data['title'] = property_data['title'].strip()
                else:
                    # Fallback para h2 com atributo title
                    title_elem = await self.page.query_selector("h2[title]")
                    if title_elem:
                        property_data['title'] = await title_elem.get_attribute('title') or await title_elem.inner_text()
                    else:
                        property_data['title'] = None
            except Exception as e:
                logger.debug(f"Erro ao extrair título: {e}")
                property_data['title'] = None
            
            # Extrair localização do título (formato: "Type - City - State")
            if property_data.get('title'):
                state, city = self._extract_state_city(property_data['title'])
                property_data['state'] = state
                property_data['city'] = city
                property_data['category'] = self._determine_category(property_data['title'])
            
            # Extrair imagem
            try:
                img_elem = await self.page.query_selector("img[src*='ged.pestanaleiloes.com.br']")
                if img_elem:
                    property_data['image_url'] = await img_elem.get_attribute('src')
                else:
                    property_data['image_url'] = None
            except Exception as e:
                logger.debug(f"Erro ao extrair imagem: {e}")
                property_data['image_url'] = None
            
            # Extrair preços do conteúdo da página
            page_text = await self.page.content()
            page_visible_text = await self.page.evaluate("() => document.body.innerText")
            
            # Procurar por "Lance mínimo" ou "Lance inicial" no HTML e texto visível
            lance_match = re.search(r'Lance\s+(?:mínimo|inicial):?\s*R\$\s*([\d.,]+)', page_text, re.IGNORECASE)
            if not lance_match:
                lance_match = re.search(r'Lance\s+(?:mínimo|inicial):?\s*R\$\s*([\d.,]+)', page_visible_text, re.IGNORECASE)
            
            if lance_match:
                property_data['price'] = self._parse_price(lance_match.group(1))
                property_data['second_auction_value'] = property_data['price']
            else:
                # Tentar encontrar qualquer valor em R$ no texto
                price_matches = re.findall(r'R\$\s*([\d]{1,3}(?:\.[\d]{3})*(?:,\d{2})?)', page_visible_text)
                if price_matches:
                    # Pegar o menor valor (geralmente é o lance inicial)
                    prices = [self._parse_price(p) for p in price_matches if self._parse_price(p)]
                    if prices:
                        property_data['price'] = min(prices)
                        property_data['second_auction_value'] = property_data['price']
                    else:
                        property_data['price'] = None
                        property_data['second_auction_value'] = None
                else:
                    property_data['price'] = None
                    property_data['second_auction_value'] = None
            
            # Procurar por valor de avaliação
            avaliacao_match = re.search(r'Avaliação:\s*R\$\s*([\d.,]+)', page_text, re.IGNORECASE)
            if avaliacao_match:
                property_data['evaluation_value'] = self._parse_price(avaliacao_match.group(1))
                property_data['evaluated_price'] = property_data['evaluation_value']
            else:
                # Se não tiver avaliação, usar lance como ambos
                property_data['evaluation_value'] = property_data.get('price')
                property_data['evaluated_price'] = property_data.get('price')
            
            # Definir first_auction_value (geralmente igual à avaliação)
            property_data['first_auction_value'] = property_data.get('evaluation_value')
            
            # Calcular desconto
            if property_data.get('evaluation_value') and property_data.get('second_auction_value'):
                discount = ((property_data['evaluation_value'] - property_data['second_auction_value']) / property_data['evaluation_value']) * 100
                property_data['discount_percentage'] = round(discount, 1)
                property_data['discount'] = property_data['discount_percentage']
            else:
                property_data['discount_percentage'] = 0
                property_data['discount'] = 0
            
            # Determinar tipo de leilão
            if 'judicial' in page_text.lower():
                property_data['auction_type'] = 'Judicial'
            else:
                property_data['auction_type'] = 'Extrajudicial'
            
            # Extrair área se disponível
            area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m²', page_text, re.IGNORECASE)
            if area_match:
                property_data['area_total'] = float(area_match.group(1).replace(',', '.'))
                property_data['area'] = property_data['area_total']
            else:
                property_data['area_total'] = None
                property_data['area'] = None
            
            # Extrair data de leilão se disponível
            date_patterns = [
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{1,2}-\d{1,2}-\d{4})',
            ]
            for pattern in date_patterns:
                date_match = re.search(pattern, page_text)
                if date_match:
                    # Converter formato brasileiro para ISO
                    date_str = date_match.group(1).replace('-', '/')
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(date_str, '%d/%m/%Y')
                        property_data['auction_date'] = dt.strftime('%Y-%m-%d')
                        property_data['first_auction_date'] = property_data['auction_date']
                    except:
                        pass
                    break
            
            return property_data
            
        except Exception as e:
            logger.error(f"  ❌ Erro ao fazer scraping da propriedade: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _is_complete(self, property_data: Dict) -> bool:
        """Check if property has all required fields."""
        # Campos mínimos obrigatórios
        required_fields = ['title', 'source_url']
        # Campos importantes mas não obrigatórios
        important_fields = ['state', 'city', 'price']
        
        # Verificar campos obrigatórios
        for field in required_fields:
            if not property_data.get(field):
                return False
        
        # Considerar completo se tiver pelo menos 2 campos importantes
        important_count = sum(1 for field in important_fields if property_data.get(field))
        return important_count >= 2


async def main():
    """Test the scraper."""
    scraper = PestanaScraper(headless=True)
    properties = await scraper.scrape_properties(max_properties=10)
    
    print("\n" + "="*50)
    print("SCRAPED PROPERTIES:")
    print("="*50)
    
    for i, prop in enumerate(properties, 1):
        print(f"\n{i}. {prop.get('title', 'Unknown')}")
        print(f"   Location: {prop.get('city')}, {prop.get('state')}")
        print(f"   Category: {prop.get('category')}")
        print(f"   Price: R$ {prop.get('price', 0) or 0:,.2f}")
        print(f"   Discount: {prop.get('discount_percentage', 0)}%")
        print(f"   URL: {prop.get('source_url')}")
        print(f"   Image: {prop.get('image_url', 'N/A')[:50]}...")


if __name__ == "__main__":
    asyncio.run(main())
