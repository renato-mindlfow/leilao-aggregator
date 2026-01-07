#!/usr/bin/env python3
"""
SCRAPER PLAYWRIGHT PARA SOLD LEILÕES
Site com proteção Cloudflare.
"""

import logging
import re
from typing import Dict, List, Optional
from .playwright_base import PlaywrightBaseScraper

logger = logging.getLogger(__name__)

class SoldPlaywrightScraper(PlaywrightBaseScraper):
    """
    Scraper para Sold Leilões usando Playwright.
    
    NOTA: O site Sold é uma Single Page Application (SPA) React que carrega
    dados dinamicamente via API. Os seletores atuais não conseguem capturar
    os dados porque eles são renderizados após o carregamento inicial.
    
    PRÓXIMOS PASSOS:
    1. Identificar a API REST usada pelo site
    2. Fazer requests diretos à API em vez de scraping HTML
    3. Ou aguardar seletores específicos aparecerem na página
    
    Por enquanto, este scraper retorna lista vazia mas está pronto para
    ser expandido quando a API for identificada.
    """
    
    BASE_URL = "https://www.sold.com.br"
    AUCTIONEER_ID = "sold"
    AUCTIONEER_NAME = "Sold Leilões"
    LISTING_URL = "https://www.sold.com.br/leiloes"
    
    SELECTORS = {
        "property_cards": "div.MuiCard-root, div[class*='Card'], article",
        "property_link": "a[href*='/evento/'], a[href*='/leilao/']",
        "title": "h3, h2, p[class*='Title'], p[class*='title']",
        "price": "p[class*='price'], p[class*='Price'], span[class*='valor']",
        "location": "p[class*='location'], p[class*='Location'], span[class*='cidade']",
        "image": "img[alt*='event'], img[alt*='leilao'], img.MuiCardMedia-img",
        "date": "p[class*='date'], p[class*='Date'], span[class*='data']",
    }
    
    async def _extract_property_data(self, card) -> Optional[Dict]:
        """Extrai dados de um card de propriedade da Sold."""
        try:
            prop = {}
            
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
                prop["evaluation_value"] = prop["first_auction_value"]
            
            # Localização
            location_elem = await card.query_selector(self.SELECTORS["location"])
            if location_elem:
                location_text = await location_elem.inner_text()
                state, city = self._extract_state_city(location_text)
                prop["state"] = state
                prop["city"] = city
            
            # Imagem
            img_elem = await card.query_selector(self.SELECTORS["image"])
            if img_elem:
                src = await img_elem.get_attribute("src") or await img_elem.get_attribute("data-src")
                if src and not any(x in src.lower() for x in ['logo', 'icon', 'placeholder']):
                    prop["image_url"] = src if src.startswith("http") else self.BASE_URL + src
            
            # Categoria
            prop["category"] = self._determine_category(prop.get("title", ""))
            prop["auction_type"] = "Extrajudicial"
            
            return prop if prop.get("title") else None
            
        except Exception as e:
            logger.debug(f"Erro ao extrair card: {e}")
            return None

