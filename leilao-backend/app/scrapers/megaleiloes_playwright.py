#!/usr/bin/env python3
"""
SCRAPER PLAYWRIGHT PARA MEGA LEILÕES
Validado visualmente em 2026-01-07.
SPA React - requer aguardar carregamento.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)

# Filtro de imóveis
IMOVEIS_KEYWORDS = ['apartamento', 'casa', 'terreno', 'sala', 'galpão', 'fazenda', 'sítio', 'chácara', 'imóvel', 'cobertura']
REJEITAR_KEYWORDS = ['veículo', 'carro', 'moto', 'caminhão', 'máquina', 'trator', 'ônibus']

class MegaLeiloesPlaywrightScraper:
    """Scraper para Mega Leilões usando Playwright."""
    
    BASE_URL = "https://www.megaleiloes.com.br"
    IMOVEIS_URL = "https://www.megaleiloes.com.br/imoveis"
    AUCTIONEER_ID = "megaleiloes"
    AUCTIONEER_NAME = "Mega Leilões"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def _setup_browser(self):
        """Configura browser com stealth."""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
        )
        
        self.page = await context.new_page()
        
        # Stealth
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        """)
    
    async def _close_browser(self):
        if self.browser:
            await self.browser.close()
    
    def _is_imovel(self, text: str) -> bool:
        """Verifica se é imóvel (não veículo)."""
        text_lower = text.lower()
        for kw in REJEITAR_KEYWORDS:
            if kw in text_lower:
                return False
        for kw in IMOVEIS_KEYWORDS:
            if kw in text_lower:
                return True
        return False
    
    def _parse_price(self, price_str: str) -> Optional[float]:
        if not price_str:
            return None
        try:
            clean = re.sub(r'[R$\s.]', '', price_str)
            clean = clean.replace(',', '.')
            return float(clean)
        except:
            return None
    
    def _extract_state_city(self, location: str) -> tuple:
        if not location:
            return None, None
        match = re.match(r'^(.+?)\s*[-/,]\s*([A-Z]{2})$', location.strip())
        if match:
            return match.group(2), match.group(1).strip()
        return None, location.strip()
    
    def _determine_category(self, text: str) -> str:
        text_lower = text.lower() if text else ""
        if any(x in text_lower for x in ['apartamento', 'apto', 'cobertura']):
            return "Apartamento"
        if any(x in text_lower for x in ['casa', 'sobrado']):
            return "Casa"
        if any(x in text_lower for x in ['terreno', 'lote']):
            return "Terreno"
        if any(x in text_lower for x in ['sala', 'galpão', 'comercial']):
            return "Comercial"
        if any(x in text_lower for x in ['fazenda', 'sítio', 'chácara']):
            return "Rural"
        return "Outro"
    
    async def _scroll_page(self):
        """Scroll para carregar conteúdo lazy-loaded."""
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
    
    async def scrape_async(self, max_properties: int = None, max_pages: int = 5) -> List[Dict]:
        """Executa scraping."""
        properties = []
        
        try:
            await self._setup_browser()
            
            current_page = 1
            while current_page <= max_pages:
                # URL com paginação
                url = self.IMOVEIS_URL
                if current_page > 1:
                    url = f"{self.IMOVEIS_URL}?pagina={current_page}"
                
                logger.info(f"📄 Mega Leilões - Página {current_page}: {url}")
                
                await self.page.goto(url, wait_until='networkidle', timeout=60000)
                
                # Aguardar SPA React carregar (15s conforme validação)
                logger.info("  ⏳ Aguardando React carregar (15s)...")
                await asyncio.sleep(15)
                
                # Scroll para carregar mais
                await self._scroll_page()
                
                # Encontrar cards
                cards = await self.page.query_selector_all(".card, [class*='card']")
                logger.info(f"  📦 {len(cards)} cards encontrados")
                
                if not cards:
                    break
                
                page_count = 0
                for card in cards:
                    try:
                        # Extrair texto do card
                        card_text = await card.inner_text()
                        
                        # Filtrar apenas imóveis
                        if not self._is_imovel(card_text):
                            continue
                        
                        prop = await self._extract_property(card)
                        if prop and prop.get("source_url"):
                            if not any(p.get("source_url") == prop["source_url"] for p in properties):
                                properties.append(prop)
                                page_count += 1
                    except:
                        continue
                
                logger.info(f"  ✅ {page_count} imóveis extraídos")
                
                if max_properties and len(properties) >= max_properties:
                    break
                
                if page_count == 0:
                    break
                
                current_page += 1
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
        finally:
            await self._close_browser()
        
        logger.info(f"✅ Total: {len(properties)} imóveis de Mega Leilões")
        return properties[:max_properties] if max_properties else properties
    
    async def _extract_property(self, card) -> Optional[Dict]:
        """Extrai dados de um card."""
        try:
            prop = {
                "auctioneer_id": self.AUCTIONEER_ID,
                "auctioneer_name": self.AUCTIONEER_NAME,
                "auctioneer_url": self.BASE_URL,
                "scraped_at": datetime.now().isoformat(),
            }
            
            # Link
            link = await card.query_selector("a[href*='/imovel'], a")
            if link:
                href = await link.get_attribute("href")
                if href:
                    prop["source_url"] = href if href.startswith("http") else self.BASE_URL + href
                    prop["url"] = prop["source_url"]
            
            if not prop.get("source_url"):
                return None
            
            # Título
            title_elem = await card.query_selector(".card-title, h3, h4, [class*='title']")
            if title_elem:
                prop["title"] = await title_elem.inner_text()
            
            # Preço
            price_elem = await card.query_selector("[class*='price'], [class*='valor'], .lance")
            if price_elem:
                price_text = await price_elem.inner_text()
                prop["first_auction_value"] = self._parse_price(price_text)
            
            # Localização
            loc_elem = await card.query_selector("[class*='location'], [class*='cidade'], [class*='local']")
            if loc_elem:
                loc_text = await loc_elem.inner_text()
                state, city = self._extract_state_city(loc_text)
                prop["state"] = state
                prop["city"] = city
            
            # Imagem
            img = await card.query_selector("img")
            if img:
                src = await img.get_attribute("src") or await img.get_attribute("data-src")
                if src and 'logo' not in src.lower():
                    prop["image_url"] = src if src.startswith("http") else self.BASE_URL + src
            
            # Categoria
            prop["category"] = self._determine_category(prop.get("title", ""))
            prop["auction_type"] = "Extrajudicial"
            
            return prop
        except:
            return None
    
    def scrape(self, max_properties: int = None) -> List[Dict]:
        """Wrapper síncrono."""
        return asyncio.run(self.scrape_async(max_properties))

