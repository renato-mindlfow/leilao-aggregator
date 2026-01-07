#!/usr/bin/env python3
"""
SCRAPER PLAYWRIGHT PARA FLEX LEILÕES
Site com proteção Cloudflare.
"""

import logging
from typing import Dict, Optional
from .playwright_base import PlaywrightBaseScraper

logger = logging.getLogger(__name__)

class FlexLeiloesPlaywrightScraper(PlaywrightBaseScraper):
    """Scraper para Flex Leilões usando Playwright."""
    
    BASE_URL = "https://www.flexleiloes.com.br"
    AUCTIONEER_ID = "flexleiloes"
    AUCTIONEER_NAME = "Flex Leilões"
    LISTING_URL = "https://www.flexleiloes.com.br/imoveis"
    
    SELECTORS = {
        "property_cards": "ul.chamadas li",
        "property_link": "a[href*='lotes/']",
        "title": "h2.item-titulo, .item-titulo",
        "price": ".item-descricao",
        "location": ".item-local",
        "image": ".item-imagem img",
    }
    
    async def _extract_property_data(self, card) -> Optional[Dict]:
        """Extrai dados de um card de propriedade da Flex."""
        try:
            prop = {}
            
            # Link
            link_elem = await card.query_selector(self.SELECTORS["property_link"])
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    prop["source_url"] = href if href.startswith("http") else self.BASE_URL + "/" + href
                    prop["url"] = prop["source_url"]
            
            if not prop.get("source_url"):
                return None
            
            # Título
            title_elem = await card.query_selector(self.SELECTORS["title"])
            if title_elem:
                title_text = await title_elem.inner_text()
                prop["title"] = title_text.strip()
            
            # Preço (extrair do texto de descrição)
            price_elem = await card.query_selector(self.SELECTORS["price"])
            if price_elem:
                price_text = await price_elem.inner_text()
                # Buscar por "Lance Mínimo: R$ X"
                import re
                price_match = re.search(r'Lance\s+M[ií]nimo:\s*R\$\s*([\d.,]+)', price_text)
                if price_match:
                    prop["first_auction_value"] = self._parse_price(price_match.group(1))
            
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
                src = await img_elem.get_attribute("src")
                if src and not any(x in src.lower() for x in ['logo', 'icon', 'placeholder', 'avatar']):
                    prop["image_url"] = src if src.startswith("http") else self.BASE_URL + "/" + src
            
            prop["category"] = self._determine_category(prop.get("title", ""))
            prop["auction_type"] = "Judicial"
            
            return prop if prop.get("title") else None
            
        except Exception as e:
            logger.debug(f"Erro ao extrair card: {e}")
            return None

