#!/usr/bin/env python3
"""
BASE CLASS PARA SCRAPERS COM PLAYWRIGHT + STEALTH
Usado para sites com proteção Cloudflare/anti-bot.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

logger = logging.getLogger(__name__)

class PlaywrightBaseScraper:
    """Base class para scrapers que precisam de Playwright com stealth."""
    
    # Configurações para override nas subclasses
    BASE_URL: str = ""
    AUCTIONEER_ID: str = ""
    AUCTIONEER_NAME: str = ""
    LISTING_URL: str = ""  # URL da listagem de imóveis
    
    # Seletores CSS (override nas subclasses)
    SELECTORS = {
        "property_cards": "div.property, div.imovel, article.lote",
        "property_link": "a[href*='imovel'], a[href*='lote'], a[href*='detalhe']",
        "title": "h1, h2.title, .property-title",
        "price": ".price, .valor, .lance, [class*='price'], [class*='valor']",
        "location": ".location, .endereco, .cidade, [class*='location'], [class*='cidade']",
        "image": "img.property-image, img.foto, .gallery img, .carousel img",
        "area": ".area, .metros, [class*='area'], [class*='m2']",
        "description": ".description, .descricao, [class*='description']",
    }
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.properties: List[Dict] = []
    
    async def _setup_browser(self):
        """Configura browser com stealth mode."""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
                '--disable-web-security',
                '--disable-infobars',
                '--disable-notifications',
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            extra_http_headers={
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        self.page = await self.context.new_page()
        
        # Injetar scripts de stealth
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)
        
        logger.info(f"✅ Browser configurado com stealth mode")
    
    async def _close_browser(self):
        """Fecha o browser."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def _wait_for_cloudflare(self):
        """Aguarda bypass do Cloudflare."""
        try:
            # Aguardar possível challenge do Cloudflare
            await asyncio.sleep(3)
            
            # Verificar se ainda está na página de challenge
            content = await self.page.content()
            if 'challenge' in content.lower() or 'checking your browser' in content.lower():
                logger.info("  ⏳ Aguardando Cloudflare...")
                await asyncio.sleep(5)
            
            return True
        except Exception as e:
            logger.error(f"  ❌ Erro ao aguardar Cloudflare: {e}")
            return False
    
    async def _scroll_page(self):
        """Scroll para carregar conteúdo lazy-loaded."""
        try:
            await self.page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 300;
                        const timer = setInterval(() => {
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if (totalHeight >= document.body.scrollHeight) {
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                        setTimeout(() => { clearInterval(timer); resolve(); }, 10000);
                    });
                }
            """)
            await asyncio.sleep(2)
        except:
            pass
    
    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse de preço em formato brasileiro."""
        if not price_str:
            return None
        try:
            clean = re.sub(r'[R$\s.]', '', price_str)
            clean = clean.replace(',', '.')
            return float(clean)
        except:
            return None
    
    def _extract_state_city(self, location: str) -> tuple:
        """Extrai estado e cidade de string de localização."""
        if not location:
            return None, None
        
        # Padrões comuns: "Cidade - UF", "Cidade/UF", "Cidade, UF"
        patterns = [
            r'(.+?)\s*[-/,]\s*([A-Z]{2})$',
            r'([A-Z]{2})\s*[-/,]\s*(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, location.strip())
            if match:
                groups = match.groups()
                if len(groups[0]) == 2:
                    return groups[0], groups[1].strip()
                else:
                    return groups[1], groups[0].strip()
        
        return None, location.strip()
    
    def _determine_category(self, text: str) -> str:
        """Determina categoria do imóvel."""
        if not text:
            return "Outro"
        
        text_lower = text.lower()
        categories = {
            "Apartamento": ["apartamento", "apto", "apt"],
            "Casa": ["casa", "sobrado", "residência", "residencia"],
            "Terreno": ["terreno", "lote", "área", "area"],
            "Comercial": ["comercial", "loja", "sala", "galpão", "galpao"],
            "Rural": ["rural", "fazenda", "sítio", "sitio", "chácara", "chacara"],
        }
        
        for category, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                return category
        
        return "Outro"
    
    async def _extract_property_data(self, card) -> Optional[Dict]:
        """Extrai dados de um card de propriedade. Override nas subclasses."""
        raise NotImplementedError("Subclasses devem implementar _extract_property_data")
    
    async def _scrape_listing_page(self) -> List[Dict]:
        """Faz scraping da página de listagem. Override nas subclasses se necessário."""
        properties = []
        
        try:
            # Navegar para página de listagem
            logger.info(f"  🌐 Navegando para {self.LISTING_URL}")
            await self.page.goto(self.LISTING_URL, wait_until='networkidle', timeout=60000)
            
            # Aguardar Cloudflare
            await self._wait_for_cloudflare()
            
            # Aguardar mais tempo para SPAs carregarem
            await asyncio.sleep(3)
            
            # Scroll para carregar tudo
            await self._scroll_page()
            
            # Aguardar mais um pouco após scroll
            await asyncio.sleep(2)
            
            # Encontrar cards de propriedades
            cards = await self.page.query_selector_all(self.SELECTORS["property_cards"])
            logger.info(f"  📦 Encontrados {len(cards)} cards de propriedades")
            
            for card in cards:
                try:
                    prop_data = await self._extract_property_data(card)
                    if prop_data:
                        properties.append(prop_data)
                except Exception as e:
                    logger.debug(f"  ⚠️ Erro ao extrair card: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"  ❌ Erro no scraping: {e}")
        
        return properties
    
    async def scrape_async(self, max_properties: int = None) -> List[Dict]:
        """Executa scraping assíncrono."""
        try:
            await self._setup_browser()
            
            logger.info(f"🔍 Iniciando scraping: {self.AUCTIONEER_NAME}")
            
            properties = await self._scrape_listing_page()
            
            if max_properties:
                properties = properties[:max_properties]
            
            # Adicionar metadados
            for prop in properties:
                prop["auctioneer_id"] = self.AUCTIONEER_ID
                prop["auctioneer_name"] = self.AUCTIONEER_NAME
                prop["auctioneer_url"] = self.BASE_URL
                prop["scraped_at"] = datetime.now().isoformat()
            
            logger.info(f"✅ Scraping concluído: {len(properties)} propriedades")
            
            return properties
            
        except Exception as e:
            logger.error(f"❌ Erro fatal no scraping: {e}")
            return []
        finally:
            await self._close_browser()
    
    def scrape(self, max_properties: int = None) -> List[Dict]:
        """Wrapper síncrono para scrape_async."""
        return asyncio.run(self.scrape_async(max_properties))

