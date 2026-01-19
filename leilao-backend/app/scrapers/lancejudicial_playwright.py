#!/usr/bin/env python3
"""
SCRAPER PLAYWRIGHT PARA LANCE JUDICIAL
Site com proteção Cloudflare e PJAX/AJAX.
Usa seletores do auctioneer_selectors.json
"""

import logging
import json
import os
import asyncio
import re
from typing import Dict, Optional, List
from .playwright_base import PlaywrightBaseScraper
from bs4 import BeautifulSoup
from app.utils.fetcher import MultiLayerFetcher

logger = logging.getLogger(__name__)

class LanceJudicialPlaywrightScraper(PlaywrightBaseScraper):
    """
    Scraper para Lance Judicial (Grupo Lance) usando Playwright.
    Usa seletores configurados em auctioneer_selectors.json.
    """
    
    BASE_URL = "https://www.grupolance.com.br"
    AUCTIONEER_ID = "lancejudicial"
    AUCTIONEER_NAME = "Lance Judicial"
    LISTING_URL = "https://www.grupolance.com.br/imoveis"
    
    def __init__(self):
        super().__init__()
        self.selector_config = self._load_selector_config()
        self.SELECTORS = self._get_selectors()
    
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
                "property_cards": ".card, [class*='card'], [class*='item']",
                "property_link": ".card a, [class*='card'] a, a[href*='/imoveis/']",
                "title": "h2, h3, [class*='title']",
                "price": "[class*='price'], [class*='valor']",
                "location": "[class*='location'], [class*='cidade']",
                "image": "img"
            }
        
        listing_page = self.selector_config.get('listing_page', {})
        selectors = listing_page.get('selectors', {})
        
        return {
            "property_cards": selectors.get('property_card', ".card, [class*='card']"),
            "property_link": selectors.get('property_link', ".card a"),
            "title": selectors.get('title', "h2, h3"),
            "price": selectors.get('price', "[class*='price'], [class*='valor']"),
            "location": selectors.get('location', "[class*='location'], [class*='cidade']"),
            "image": selectors.get('image', "img")
        }
    
    async def _extract_property_data(self, card) -> Optional[Dict]:
        """Extrai dados de um card de propriedade do Lance Judicial."""
        try:
            prop = {
                "auctioneer_id": self.AUCTIONEER_ID,
                "auctioneer_name": self.AUCTIONEER_NAME,
                "auctioneer_url": self.BASE_URL,
                "source": self.AUCTIONEER_ID,
            }
            
            # Link
            link_elem = await card.query_selector(self.SELECTORS["property_link"])
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    prop["source_url"] = href if href.startswith("http") else self.BASE_URL + href
                    prop["url"] = prop["source_url"]
            
            if not prop.get("source_url"):
                return None
            
            # Título
            title_elem = await card.query_selector(self.SELECTORS["title"])
            if title_elem:
                prop["title"] = await title_elem.inner_text()
            
            # Preço
            price_elem = await card.query_selector(self.SELECTORS["price"])
            if price_elem:
                price_text = await price_elem.inner_text()
                prop["first_auction_value"] = self._parse_price(price_text)
            
            # Localização
            location_elem = await card.query_selector(self.SELECTORS["location"])
            if location_elem:
                location_text = await location_elem.inner_text()
                state, city = self._extract_state_city(location_text)
                prop["state"] = state or "NI"
                prop["city"] = city or "Não informado"
            else:
                prop["state"] = "NI"
                prop["city"] = "Não informado"
            
            # Imagem
            img_elem = await card.query_selector(self.SELECTORS["image"])
            if img_elem:
                src = await img_elem.get_attribute("src") or await img_elem.get_attribute("data-src")
                if src and 'logo' not in src.lower():
                    prop["image_url"] = src if src.startswith("http") else self.BASE_URL + src
            
            # Categoria e tipo
            prop["category"] = self._determine_category(prop.get("title", ""))
            prop["auction_type"] = "Judicial"
            if prop.get("first_auction_value") and not prop.get("price"):
                prop["price"] = prop["first_auction_value"]
            
            return prop if prop.get("title") else None
            
        except Exception as e:
            logger.debug(f"Erro ao extrair card: {e}")
            return None

    def scrape_properties(self, max_properties: int = 5) -> list[Dict]:
        """Wrapper síncrono para scraping com normalização."""
        props = self._scrape_with_fetcher(max_properties=max_properties)
        if props:
            return props

        props = asyncio.run(self.scrape_async(max_properties=max_properties))
        for prop in props:
            prop.setdefault("auctioneer_id", self.AUCTIONEER_ID)
            prop.setdefault("auctioneer_name", self.AUCTIONEER_NAME)
            prop.setdefault("source", self.AUCTIONEER_ID)
            prop.setdefault("city", "Não informado")
            prop.setdefault("state", "NI")
            if prop.get("first_auction_value") and not prop.get("price"):
                prop["price"] = prop["first_auction_value"]
        return props

    def _scrape_with_fetcher(self, max_properties: int = 5) -> List[Dict]:
        """Fallback rápido via MultiLayerFetcher + BeautifulSoup."""
        fetcher = MultiLayerFetcher(timeout=60.0, min_content_length=1200)
        listing_html = asyncio.run(fetcher.fetch(self.LISTING_URL))
        if not listing_html.success:
            return []

        soup = BeautifulSoup(listing_html.content, "html.parser")
        category_urls = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("/imoveis/") and href.count("/") <= 3:
                category_urls.append(self.BASE_URL + href)
        category_urls = list(dict.fromkeys(category_urls))[:10]

        properties: List[Dict] = []
        for category_url in category_urls:
            if len(properties) >= max_properties:
                break
            page_html = asyncio.run(fetcher.fetch(category_url))
            if not page_html.success:
                continue
            page_soup = BeautifulSoup(page_html.content, "html.parser")
            detail_links = []
            for a_tag in page_soup.find_all("a", href=True):
                href = a_tag["href"]
                if "/imoveis/" in href and href.count("/") >= 5:
                    detail_links.append(href if href.startswith("http") else self.BASE_URL + href)
            detail_links = list(dict.fromkeys(detail_links))

            for link in detail_links:
                if len(properties) >= max_properties:
                    break
                prop = self._extract_detail_from_html(fetcher, link)
                if prop:
                    properties.append(prop)

        return properties

    def _extract_detail_from_html(self, fetcher: MultiLayerFetcher, url: str) -> Optional[Dict]:
        result = asyncio.run(fetcher.fetch(url))
        if not result.success:
            return None

        soup = BeautifulSoup(result.content, "html.parser")
        title = None
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title.get("content").strip()
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)
        if not title:
            return None

        text = soup.get_text(" ", strip=True)
        price_match = re.search(r"R\$\s*([\d\.,]+)", text)
        price = self._parse_price(price_match.group(1)) if price_match else None
        city = None
        state = None
        text_match = re.findall(r"([A-Za-zÀ-ÿ\s]+)\s*/\s*([A-Z]{2})", text)
        if text_match:
            city, state = text_match[-1]
            city = city.strip().title()
            state = state.upper()
        else:
            state, city = self._extract_state_city(title)
            if city:
                if "," in city:
                    city = city.split(",")[-1].strip()
                city = re.sub(r"\([^)]*\)", "", city).strip()

        return {
            "title": title,
            "city": city or "Não informado",
            "state": state or "NI",
            "price": price,
            "source": self.AUCTIONEER_ID,
            "auctioneer_id": self.AUCTIONEER_ID,
            "auctioneer_name": self.AUCTIONEER_NAME,
            "auctioneer_url": self.BASE_URL,
            "source_url": url,
            "url": url,
        }

