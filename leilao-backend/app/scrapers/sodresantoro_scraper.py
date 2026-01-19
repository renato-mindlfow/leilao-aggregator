"""
Scraper específico para Sodré Santoro usando seletores do auctioneer_selectors.json
"""
import logging
import json
import os
import re
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.scrapers.playwright_base import PlaywrightBaseScraper
from app.utils.fetcher import MultiLayerFetcher

logger = logging.getLogger(__name__)


class SodreSantoroScraper(PlaywrightBaseScraper):
    """
    Scraper específico para Sodré Santoro usando seletores configurados.
    """
    
    BASE_URL = "https://www.sodresantoro.com.br"
    AUCTIONEER_ID = "sodresantoro"
    AUCTIONEER_NAME = "Sodré Santoro"
    LISTING_URL = "https://www.sodresantoro.com.br/imoveis"
    
    def __init__(self):
        super().__init__()
        self.selector_config = self._load_selector_config()
        self.selectors = self._get_selectors()
    
    def _load_selector_config(self) -> Optional[Dict]:
        """Carrega configuração de seletores do JSON."""
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'config',
                'auctioneer_selectors.json'
            )
            
            if not os.path.exists(config_path):
                logger.warning(f"Arquivo de seletores não encontrado: {config_path}")
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return config.get('auctioneers', {}).get(self.AUCTIONEER_ID)
        except Exception as e:
            logger.error(f"Erro ao carregar seletores: {e}")
            return None
    
    def _get_selectors(self) -> Dict[str, str]:
        """Extrai seletores da configuração."""
        if not self.selector_config:
            # Fallback para seletores padrão
            return {
                "property_card": "[class*='card'], [class*='lote'], .card, .item",
                "property_link": "a[href*='/imovel/'], .card a, a[href*='/leilao/'], a[href*='/lote/']",
                "title": "h2, h3, [class*='title']",
                "price": "[class*='price'], [class*='valor'], [class*='lance']",
                "location": "[class*='location'], [class*='endereco'], [class*='cidade']",
                "image": "img",
                "category": "[class*='category'], [class*='tipo']"
            }
        
        listing_page = self.selector_config.get('listing_page', {})
        selectors = listing_page.get('selectors', {})
        
        return {
            "property_card": selectors.get('property_card', "[class*='card'], [class*='lote']"),
            "property_link": selectors.get('property_link', "a[href*='/imovel/']"),
            "title": selectors.get('title', "h2, h3"),
            "price": selectors.get('price', "[class*='price'], [class*='valor']"),
            "location": selectors.get('location', "[class*='location'], [class*='endereco']"),
            "image": selectors.get('image', "img"),
            "category": selectors.get('category', "[class*='category']")
        }
    
    def _get_pagination_config(self) -> Dict:
        """Retorna configuração de paginação."""
        if not self.selector_config:
            return {
                "type": "query",
                "param": "page",
                "start": 1,
                "max_pages": 30
            }
        
        pagination = self.selector_config.get('listing_page', {}).get('pagination', {})
        return {
            "type": pagination.get('type', 'query'),
            "param": pagination.get('param', 'page'),
            "start": pagination.get('start', 1),
            "max_pages": pagination.get('max_pages', 30),
            "items_per_page": pagination.get('items_per_page', 20)
        }

    @staticmethod
    def _parse_price(value: Optional[str]) -> Optional[float]:
        """Parse Brazilian price string to float."""
        if not value:
            return None
        cleaned = re.sub(r"[R$\s]", "", value)
        cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_location(value: Optional[str]) -> Dict[str, Optional[str]]:
        """Parse city/state from location string."""
        if not value:
            return {"city": None, "state": None}
        match = re.search(r"([A-Za-zÀ-ÿ\s]+)[-/]\s*([A-Z]{2})\b", value)
        if match:
            city = match.group(1).strip(" ,").title()
            state = match.group(2).upper()
            return {"city": city, "state": state}
        return {"city": None, "state": None}
    
    async def scrape_properties(self, max_properties: int = 500) -> List[Dict[str, Any]]:
        """
        Faz scraping de propriedades do Sodré Santoro.
        
        Args:
            max_properties: Número máximo de propriedades a extrair
            
        Returns:
            Lista de propriedades extraídas
        """
        properties = []
        pagination_config = self._get_pagination_config()
        max_pages = pagination_config.get('max_pages', 30)
        current_page = pagination_config.get('start', 1)
        
        logger.info(f"Iniciando scraping de {self.AUCTIONEER_NAME} (max: {max_properties} imóveis)")
        
        try:
            await self._setup_browser()
            
            while len(properties) < max_properties and current_page <= max_pages:
                # Construir URL da página
                if current_page == 1:
                    page_url = self.LISTING_URL
                else:
                    param = pagination_config.get('param', 'page')
                    separator = "&" if "?" in self.LISTING_URL else "?"
                    page_url = f"{self.LISTING_URL}{separator}{param}={current_page}"
                
                logger.info(f"Processando página {current_page}: {page_url}")
                
                try:
                    # Acessar página
                    await self.page.goto(page_url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(3)  # Aguardar carregamento
                    
                    # Scroll para carregar conteúdo lazy
                    await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)

                    # Extrair propriedades
                    page_properties = await self._extract_properties_from_page(self.page)

                    # Filtrar duplicados
                    new_properties = [
                        p for p in page_properties
                        if not any(prop.get('url') == p.get('url') for prop in properties)
                    ]

                    properties.extend(new_properties)
                    logger.info(
                        f"Página {current_page}: {len(new_properties)} novos imóveis (total: {len(properties)})"
                    )

                    # Se não encontrou novos imóveis, parar
                    if len(new_properties) == 0:
                        logger.info(f"Nenhum novo imóvel encontrado na página {current_page}, parando...")
                        break

                    current_page += 1
                    await asyncio.sleep(2)  # Rate limiting

                except Exception as e:
                    logger.error(f"Erro ao processar página {current_page}: {e}")
                    break
            
            await self._close_browser()

            if not properties:
                logger.info("Nenhum imóvel via Playwright. Tentando fallback com ScrapingBee/Fetch.")
                properties = await self._fallback_scrape_with_fetcher(max_properties=max_properties)

            if not properties:
                logger.info("Fallback vazio. Tentando links conhecidos do Sodré Santoro.")
                properties = await self._fallback_from_known_links(max_properties=max_properties)
        
        except Exception as e:
            logger.error(f"Erro fatal no scraping: {e}")
        
        logger.info(f"Scraping concluído: {len(properties)} imóveis extraídos")
        return properties[:max_properties]

    async def _fallback_scrape_with_fetcher(self, max_properties: int = 100) -> List[Dict[str, Any]]:
        """Fallback scraping using MultiLayerFetcher + BeautifulSoup."""
        properties: List[Dict[str, Any]] = []
        fetcher = MultiLayerFetcher(timeout=60.0, min_content_length=1200)
        pagination_config = self._get_pagination_config()
        max_pages = min(pagination_config.get('max_pages', 10), 10)
        current_page = pagination_config.get('start', 1)

        while len(properties) < max_properties and current_page <= max_pages:
            if current_page == 1:
                page_url = self.LISTING_URL
            else:
                param = pagination_config.get('param', 'page')
                separator = "&" if "?" in self.LISTING_URL else "?"
                page_url = f"{self.LISTING_URL}{separator}{param}={current_page}"

            result = await fetcher.fetch(page_url)
            if not result.success:
                logger.warning(f"Fallback fetch failed: {result.error}")
                break

            soup = BeautifulSoup(result.content, "html.parser")
            cards = soup.select(self.selectors['property_card'])

            if not cards:
                cards = soup.select("a[href*='/imovel/'], a[href*='/lote/'], a[href*='/leilao/']")

            if not cards and fetcher.scrapingbee_api_key:
                sb_result = await fetcher._layer3_scrapingbee(page_url)
                if fetcher._is_valid_result(sb_result):
                    soup = BeautifulSoup(sb_result.content, "html.parser")
                    cards = soup.select(self.selectors['property_card'])
                    if not cards:
                        cards = soup.select("a[href*='/imovel/'], a[href*='/lote/'], a[href*='/leilao/']")

            if not cards:
                logger.info(f"Nenhum card na página {current_page}")
                break

            for card in cards:
                prop = self._extract_property_from_bs4(card)
                if not prop:
                    continue
                if any(p.get("source_url") == prop.get("source_url") for p in properties):
                    continue
                properties.append(prop)
                if len(properties) >= max_properties:
                    break

            current_page += 1

        return properties[:max_properties]

    async def _fallback_from_known_links(self, max_properties: int = 50) -> List[Dict[str, Any]]:
        """Fallback usando links conhecidos salvos em validação visual."""
        properties: List[Dict[str, Any]] = []
        fetcher = MultiLayerFetcher(timeout=60.0, min_content_length=1200)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        links_path = os.path.join(base_dir, "validacao_visual_resultados.json")
        if not os.path.exists(links_path):
            return properties

        try:
            with open(links_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return properties

        known_links: List[str] = []
        for entry in data:
            if entry.get("site_id") != "sodresantoro":
                continue
            links = entry.get("links_imoveis") or []
            for link in links:
                if not isinstance(link, str):
                    continue
                if "leilao.sodresantoro.com.br" in link and "/leilao/" in link and "/lote/" in link:
                    known_links.append(link)

        seen = set()
        for link in known_links:
            if link in seen:
                continue
            seen.add(link)

            result = await fetcher._layer3_scrapingbee(link)
            if not fetcher._is_valid_result(result):
                continue

            prop = self._extract_detail_from_html(result.content, link)
            if prop:
                properties.append(prop)

            if len(properties) >= max_properties:
                break

        return properties

    def _extract_detail_from_html(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Extrai detalhes do imóvel a partir do HTML de detalhe."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            title = None
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title.get("content").strip()
            if not title:
                title_tag = soup.find("title")
                if title_tag:
                    title = title_tag.get_text(strip=True)

            page_text = soup.get_text(" ", strip=True)
            price_match = re.search(r"R\$\s*([\d\.,]+)", page_text)
            if not price_match:
                price_match = re.search(r"R\$\s*([\d\.,]+)", html)
            if not price_match:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                og_desc = soup.find("meta", property="og:description")
                meta_text = ""
                if meta_desc and meta_desc.get("content"):
                    meta_text += meta_desc.get("content")
                if og_desc and og_desc.get("content"):
                    meta_text += f" {og_desc.get('content')}"
                price_match = re.search(r"R\$\s*([\d\.,]+)", meta_text)
            price = self._parse_price(price_match.group(1)) if price_match else None

            city = "Não informado"
            state = "NI"
            if title:
                parts = [part.strip() for part in title.split("-") if part.strip()]
                for i in range(len(parts) - 1, 0, -1):
                    candidate_state = parts[i]
                    if len(candidate_state) == 2 and candidate_state.isupper():
                        state = candidate_state
                        city = parts[i - 1].title()
                        break

            return {
                "auctioneer_id": self.AUCTIONEER_ID,
                "auctioneer_name": self.AUCTIONEER_NAME,
                "auctioneer_url": self.BASE_URL,
                "source": self.AUCTIONEER_ID,
                "source_url": url,
                "url": url,
                "title": title or "Imóvel",
                "price": price,
                "city": city,
                "state": state,
            }
        except Exception:
            return None

    def _extract_property_from_bs4(self, card) -> Optional[Dict[str, Any]]:
        """Extract property data from BeautifulSoup card/link."""
        try:
            prop: Dict[str, Any] = {
                "auctioneer_id": self.AUCTIONEER_ID,
                "auctioneer_name": self.AUCTIONEER_NAME,
                "auctioneer_url": self.BASE_URL,
                "source": self.AUCTIONEER_ID,
                "extracted_at": datetime.now().isoformat(),
            }

            link_elem = card if card.name == "a" else card.select_one(self.selectors['property_link'])
            if not link_elem:
                return None
            href = link_elem.get("href")
            if not href:
                return None
            prop["url"] = urljoin(self.BASE_URL, href)
            prop["source_url"] = prop["url"]

            title_elem = card.select_one(self.selectors['title']) if card.name != "a" else None
            title_text = title_elem.get_text(strip=True) if title_elem else card.get_text(strip=True)
            prop["title"] = title_text[:200] if title_text else "Imóvel"

            price_elem = card.select_one(self.selectors['price'])
            price_text = price_elem.get_text(strip=True) if price_elem else card.get_text(strip=True)
            prop["price"] = self._parse_price(price_text)

            location_elem = card.select_one(self.selectors['location'])
            location_text = location_elem.get_text(strip=True) if location_elem else ""
            location_parts = self._parse_location(location_text)
            prop["city"] = location_parts.get("city") or "Não informado"
            prop["state"] = location_parts.get("state") or "NI"

            category_elem = card.select_one(self.selectors['category'])
            if category_elem:
                prop["category"] = category_elem.get_text(strip=True)

            return prop
        except Exception:
            return None
    
    async def _extract_properties_from_page(self, page) -> List[Dict[str, Any]]:
        """Extrai propriedades de uma página."""
        properties = []
        
        try:
            # Buscar cards de propriedades
            cards = await page.query_selector_all(self.selectors['property_card'])
            logger.debug(f"Encontrados {len(cards)} cards na página")
            
            for card in cards:
                try:
                    prop = await self._extract_property_data(card)
                    if prop:
                        properties.append(prop)
                except Exception as e:
                    logger.debug(f"Erro ao extrair dados do card: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Erro ao extrair propriedades: {e}")
        
        return properties
    
    async def _extract_property_data(self, card) -> Optional[Dict]:
        """Extrai dados de um card de propriedade."""
        try:
            prop = {
                'auctioneer_id': self.AUCTIONEER_ID,
                'auctioneer_name': self.AUCTIONEER_NAME,
                'source': self.AUCTIONEER_ID,
                'extracted_at': datetime.now().isoformat()
            }
            
            # Link
            link_elem = await card.query_selector(self.selectors['property_link'])
            if link_elem:
                href = await link_elem.get_attribute('href')
                if href:
                    prop['url'] = urljoin(self.BASE_URL, href)
                    prop['source_url'] = prop['url']
                else:
                    return None
            else:
                return None
            
            # Título
            title_elem = await card.query_selector(self.selectors['title'])
            if title_elem:
                prop['title'] = (await title_elem.inner_text()).strip()[:200]
            
            # Preço
            price_elem = await card.query_selector(self.selectors['price'])
            if price_elem:
                price_text = (await price_elem.inner_text()).strip()
                prop['price'] = self._parse_price(price_text)
            if not prop.get('price'):
                try:
                    card_text = (await card.inner_text()).strip()
                    price_match = re.search(r"R\$\s*([\d\.,]+)", card_text)
                    if price_match:
                        prop['price'] = self._parse_price(price_match.group(1))
                except Exception:
                    pass
            
            # Localização
            location_elem = await card.query_selector(self.selectors['location'])
            if location_elem:
                prop['location'] = (await location_elem.inner_text()).strip()
                location_parts = self._parse_location(prop['location'])
                prop['city'] = location_parts.get('city') or "Não informado"
                prop['state'] = location_parts.get('state') or "NI"
            else:
                prop['city'] = "Não informado"
                prop['state'] = "NI"
            
            # Imagem
            image_elem = await card.query_selector(self.selectors['image'])
            if image_elem:
                src = await image_elem.get_attribute('src') or await image_elem.get_attribute('data-src')
                if src:
                    prop['image_url'] = urljoin(self.BASE_URL, src)
            
            # Categoria
            category_elem = await card.query_selector(self.selectors['category'])
            if category_elem:
                prop['category'] = (await category_elem.inner_text()).strip()
            
            return prop if prop.get('url') else None
        
        except Exception as e:
            logger.debug(f"Erro ao extrair dados do card: {e}")
            return None

