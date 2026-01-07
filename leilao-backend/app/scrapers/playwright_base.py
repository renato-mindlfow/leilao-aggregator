#!/usr/bin/env python3
"""
BASE CLASS PARA SCRAPERS COM PLAYWRIGHT + STEALTH + PAGINAÇÃO AUTOMÁTICA
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Set
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

logger = logging.getLogger(__name__)

class PlaywrightBaseScraper:
    """
    Base class para scrapers Playwright com:
    - Stealth mode (bypass anti-bot)
    - Detecção automática de paginação
    - Extração de todas as páginas
    - Filtro de imóveis (não veículos)
    """
    
    # Configurações para override nas subclasses
    BASE_URL: str = ""
    LISTING_URL: str = ""
    AUCTIONEER_ID: str = ""
    AUCTIONEER_NAME: str = ""
    
    # Paginação
    MAX_PAGES: int = 100
    WAIT_TIME: int = 5  # Segundos para aguardar carregamento
    WAIT_BETWEEN_PAGES: int = 2
    
    # Seletores (override nas subclasses)
    SELECTORS = {
        "property_cards": [
            ".card", "[class*='card']", "[class*='imovel']", 
            "[class*='property']", "article", "[class*='item']"
        ],
        "property_link": [
            "a[href*='/imovel']", "a[href*='/lote']", 
            "a[href*='/detalhe']", "a"
        ],
        "title": ["h1", "h2", "h3", "h4", ".title", "[class*='title']"],
        "price": ["[class*='price']", "[class*='valor']", "[class*='lance']"],
        "location": ["[class*='location']", "[class*='cidade']", "[class*='local']"],
        "image": ["img"],
        "pagination": [
            "nav.pagination a", ".pagination a", "[class*='pagination'] a",
            "a[href*='page=']", "a[href*='pagina=']", "a.page-link"
        ],
        "next_page": [
            "a[rel='next']", "a.next", "[class*='next']", 
            "a:has-text('Próxima')", "a:has-text('>')"
        ],
    }
    
    # Parâmetros de paginação comuns
    PAGE_PARAMS = ['page', 'pagina', 'p', 'pg', 'pag']
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        # Paginação
        self.detected_page_param = None
        self.total_pages = None
        self.seen_urls: Set[str] = set()
    
    async def _setup_browser(self):
        """Configura browser com stealth mode."""
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
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
            }
        )
        
        self.page = await self.context.new_page()
        
        # Scripts de stealth
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)
        
        logger.info("✅ Browser configurado com stealth mode")
    
    async def _close_browser(self):
        """Fecha o browser."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
    
    
    async def _scroll_page(self):
        """Scroll para carregar conteúdo lazy-loaded."""
        try:
            await self.page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 500;
                        const maxTime = 10000;
                        const startTime = Date.now();
                        
                        const timer = setInterval(() => {
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            
                            if (totalHeight >= document.body.scrollHeight || Date.now() - startTime > maxTime) {
                                clearInterval(timer);
                                window.scrollTo(0, 0);  // Voltar ao topo
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            await asyncio.sleep(1)
        except:
            pass
    
    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse de preço brasileiro."""
        if not price_str:
            return None
        try:
            match = re.search(r'R\$\s*([\d.,]+)', price_str)
            if match:
                clean = match.group(1).replace('.', '').replace(',', '.')
                return float(clean)
            clean = re.sub(r'[R$\s.]', '', price_str)
            clean = clean.replace(',', '.')
            return float(clean)
        except:
            return None
    
    def _extract_state_city(self, location: str) -> tuple:
        """Extrai estado e cidade."""
        if not location:
            return None, None
        
        location = location.strip()
        patterns = [
            r'^(.+?)\s*[-/,]\s*([A-Z]{2})$',
            r'^([A-Z]{2})\s*[-/,]\s*(.+)$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, location)
            if match:
                g1, g2 = match.groups()
                if len(g1) == 2 and g1.isupper():
                    return g1, g2.strip()
                elif len(g2) == 2 and g2.isupper():
                    return g2, g1.strip()
        
        # Procurar UF no texto
        uf_match = re.search(r'\b([A-Z]{2})\b', location)
        if uf_match:
            return uf_match.group(1), location.replace(uf_match.group(1), '').strip(' -/,')
        
        return None, location
    
    def _determine_category(self, text: str) -> str:
        """Determina categoria do imóvel."""
        if not text:
            return "Outro"
        
        text_lower = text.lower()
        
        if any(x in text_lower for x in ['apartamento', 'apto', 'cobertura', 'flat', 'kitnet']):
            return "Apartamento"
        if any(x in text_lower for x in ['casa', 'sobrado', 'residência']):
            return "Casa"
        if any(x in text_lower for x in ['terreno', 'lote', 'área', 'gleba']):
            return "Terreno"
        if any(x in text_lower for x in ['sala', 'loja', 'galpão', 'prédio', 'comercial']):
            return "Comercial"
        if any(x in text_lower for x in ['fazenda', 'sítio', 'chácara', 'rural']):
            return "Rural"
        
        return "Outro"
    
    async def _find_elements(self, selectors: List[str]):
        """Encontra elementos usando lista de seletores."""
        for selector in selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    return elements
            except:
                continue
        return []
    
    async def _find_element(self, parent, selectors: List[str]):
        """Encontra um elemento dentro de outro."""
        for selector in selectors:
            try:
                elem = await parent.query_selector(selector)
                if elem:
                    return elem
            except:
                continue
        return None
    
    async def _extract_property(self, card) -> Optional[Dict]:
        """
        Extrai dados de um card de propriedade.
        Subclasses podem sobrescrever para customizar.
        """
        try:
            prop = {
                "auctioneer_id": self.AUCTIONEER_ID,
                "auctioneer_name": self.AUCTIONEER_NAME,
                "auctioneer_url": self.BASE_URL,
                "scraped_at": datetime.now().isoformat(),
                "auction_type": "Extrajudicial",
            }
            
            # Link
            link = await self._find_element(card, self.SELECTORS["property_link"])
            if link:
                href = await link.get_attribute("href")
                if href:
                    prop["source_url"] = urljoin(self.BASE_URL, href)
                    prop["url"] = prop["source_url"]
            
            if not prop.get("source_url"):
                return None
            
            # Título
            title_elem = await self._find_element(card, self.SELECTORS["title"])
            if title_elem:
                prop["title"] = await title_elem.inner_text()
            else:
                card_text = await card.inner_text()
                prop["title"] = card_text.split('\n')[0][:100] if card_text else "Imóvel"
            
            if prop.get("title"):
                prop["title"] = ' '.join(prop["title"].split())[:200]
            
            # Preço
            price_elem = await self._find_element(card, self.SELECTORS["price"])
            if price_elem:
                price_text = await price_elem.inner_text()
                prop["first_auction_value"] = self._parse_price(price_text)
            
            if not prop.get("first_auction_value"):
                card_text = await card.inner_text()
                match = re.search(r'R\$\s*([\d.,]+)', card_text)
                if match:
                    prop["first_auction_value"] = self._parse_price(match.group(0))
            
            # Localização
            loc_elem = await self._find_element(card, self.SELECTORS["location"])
            if loc_elem:
                loc_text = await loc_elem.inner_text()
                state, city = self._extract_state_city(loc_text)
                prop["state"] = state
                prop["city"] = city
            
            # Imagem
            img = await self._find_element(card, self.SELECTORS["image"])
            if img:
                src = await img.get_attribute("src") or await img.get_attribute("data-src")
                if src and not any(x in src.lower() for x in ['logo', 'icon', 'placeholder']):
                    prop["image_url"] = urljoin(self.BASE_URL, src)
            
            # Categoria
            prop["category"] = self._determine_category(prop.get("title", ""))
            
            return prop
            
        except Exception as e:
            logger.debug(f"Erro ao extrair card: {e}")
            return None
    
    async def _extract_property_data(self, card) -> Optional[Dict]:
        """Alias para compatibilidade. Subclasses podem sobrescrever."""
        return await self._extract_property(card)
    
    async def _detect_pagination(self) -> Dict:
        """Detecta informações de paginação na página atual."""
        info = {
            "has_pagination": False,
            "total_pages": None,
            "page_param": None,
            "next_url": None,
        }
        
        try:
            # Procurar links de paginação
            for selector in self.SELECTORS.get("pagination", []):
                try:
                    links = await self.page.query_selector_all(selector)
                    if links:
                        info["has_pagination"] = True
                        
                        # Extrair números de página e parâmetro
                        page_numbers = []
                        for link in links:
                            href = await link.get_attribute("href")
                            text = await link.inner_text()
                            
                            if text and text.strip().isdigit():
                                page_numbers.append(int(text.strip()))
                            
                            if href:
                                # Detectar parâmetro
                                for param in self.PAGE_PARAMS:
                                    if f"{param}=" in href.lower():
                                        info["page_param"] = param
                                        self.detected_page_param = param
                                        
                                        # Extrair número
                                        match = re.search(rf'{param}=(\d+)', href, re.I)
                                        if match:
                                            page_numbers.append(int(match.group(1)))
                                        break
                        
                        if page_numbers:
                            info["total_pages"] = max(page_numbers)
                            self.total_pages = info["total_pages"]
                        
                        break
                except:
                    continue
            
            # Procurar botão "próxima"
            for selector in self.SELECTORS.get("next_page", []):
                try:
                    next_btn = await self.page.query_selector(selector)
                    if next_btn:
                        info["has_pagination"] = True
                        href = await next_btn.get_attribute("href")
                        if href:
                            info["next_url"] = href
                        break
                except:
                    continue
            
            # Procurar total de itens no texto
            page_text = await self.page.inner_text("body")
            patterns = [
                r'(\d+)\s*(?:imóve|imoveis|resultado|item|lote)',
                r'de\s+(\d+)',
                r'total[:\s]+(\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_text.lower())
                if match:
                    total = int(match.group(1))
                    if total > 100 and not info["total_pages"]:
                        # Estimar páginas (assumindo ~50 por página)
                        info["total_pages"] = (total // 50) + 1
                        self.total_pages = info["total_pages"]
                    break
            
        except Exception as e:
            logger.debug(f"Erro ao detectar paginação: {e}")
        
        return info
    
    def _get_page_url(self, page_num: int) -> str:
        """Gera URL para página específica."""
        if page_num == 1:
            return self.LISTING_URL
        
        param = self.detected_page_param or 'pagina'
        
        parsed = urlparse(self.LISTING_URL)
        query_params = parse_qs(parsed.query)
        
        # Remover parâmetros de página existentes
        for p in self.PAGE_PARAMS:
            query_params.pop(p, None)
        
        # Adicionar parâmetro de página
        query_params[param] = [str(page_num)]
        
        new_query = urlencode(query_params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
    
    async def scrape_async(self, max_properties: int = None, max_pages: int = None) -> List[Dict]:
        """
        Executa scraping com paginação automática.
        """
        properties = []
        max_pages = max_pages or self.MAX_PAGES
        
        try:
            await self._setup_browser()
            
            logger.info(f"🔍 Iniciando scraping: {self.AUCTIONEER_NAME}")
            logger.info(f"   URL: {self.LISTING_URL}")
            
            # Primeira página
            logger.info(f"\n📄 Página 1: {self.LISTING_URL}")
            await self.page.goto(self.LISTING_URL, wait_until='domcontentloaded', timeout=60000)
            
            # Aguardar carregamento
            logger.info(f"   ⏳ Aguardando {self.WAIT_TIME}s...")
            await asyncio.sleep(self.WAIT_TIME)
            await self._scroll_page()
            
            # Detectar paginação
            pagination_info = await self._detect_pagination()
            logger.info(f"   📊 Paginação: {pagination_info}")
            
            if pagination_info.get("total_pages"):
                max_pages = min(pagination_info["total_pages"], max_pages)
                logger.info(f"   📊 Total de páginas detectado: {max_pages}")
            
            current_page = 1
            consecutive_empty = 0
            
            while current_page <= max_pages:
                if current_page > 1:
                    url = self._get_page_url(current_page)
                    logger.info(f"\n📄 Página {current_page}: {url}")
                    
                    await self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    await asyncio.sleep(self.WAIT_TIME)
                    await self._scroll_page()
                
                # Encontrar cards
                cards = await self._find_elements(self.SELECTORS["property_cards"])
                
                if not cards:
                    logger.warning(f"   ⚠️ Nenhum card encontrado")
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        logger.info("   🛑 2 páginas vazias - encerrando")
                        break
                    current_page += 1
                    continue
                
                consecutive_empty = 0
                logger.info(f"   📦 {len(cards)} cards encontrados")
                
                page_count = 0
                for card in cards:
                    prop = await self._extract_property(card)
                    
                    if prop and prop.get("source_url"):
                        url_key = prop["source_url"]
                        
                        if url_key not in self.seen_urls:
                            self.seen_urls.add(url_key)
                            properties.append(prop)
                            page_count += 1
                
                logger.info(f"   ✅ {page_count} novos imóveis (total: {len(properties)})")
                
                if max_properties and len(properties) >= max_properties:
                    logger.info(f"   🎯 Máximo de {max_properties} atingido")
                    break
                
                current_page += 1
                
                if current_page <= max_pages:
                    await asyncio.sleep(self.WAIT_BETWEEN_PAGES)
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._close_browser()
        
        logger.info(f"\n✅ Total: {len(properties)} imóveis de {self.AUCTIONEER_NAME}")
        
        if max_properties:
            return properties[:max_properties]
        return properties
    
    def scrape(self, max_properties: int = None, max_pages: int = None) -> List[Dict]:
        """Wrapper síncrono."""
        return asyncio.run(self.scrape_async(max_properties, max_pages))

