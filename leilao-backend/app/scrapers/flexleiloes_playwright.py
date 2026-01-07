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
    
    WAIT_TIME = 8
    MAX_PAGES = 50
    
    SELECTORS = {
        "property_cards": [
            "ul.chamadas li", "li", "[class*='item']", "[class*='lote']"
        ],
        "property_link": [
            "a[href*='lotes/']", "a[href*='/lote']", "a"
        ],
        "title": [
            "h2.item-titulo", ".item-titulo", "h2", "h3"
        ],
        "price": [
            ".item-descricao", "[class*='price']", "[class*='valor']"
        ],
        "location": [
            ".item-local", "[class*='local']", "[class*='cidade']"
        ],
        "image": [
            ".item-imagem img", "img"
        ],
        "pagination": [
            ".pagination a", "[class*='pagination'] a", "a[href*='page=']"
        ],
        "next_page": [
            "a[rel='next']", "a.next", "[class*='next']"
        ],
    }
    
    async def _extract_property(self, card) -> Optional[Dict]:
        """Extrai dados de um card de propriedade da Flex."""
        try:
            # Usar método da base class primeiro
            prop = await super()._extract_property(card)
            
            if not prop:
                return None
            
            # Customização específica: extrair preço do texto de descrição
            if not prop.get("first_auction_value"):
                card_text = await card.inner_text()
                import re
                price_match = re.search(r'Lance\s+M[ií]nimo:\s*R\$\s*([\d.,]+)', card_text)
                if price_match:
                    prop["first_auction_value"] = self._parse_price(price_match.group(1))
            
            prop["auction_type"] = "Judicial"
            
            return prop if prop.get("title") else None
            
        except Exception as e:
            logger.debug(f"Erro ao extrair card: {e}")
            return None

