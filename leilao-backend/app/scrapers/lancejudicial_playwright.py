#!/usr/bin/env python3
"""
SCRAPER PLAYWRIGHT PARA LANCE JUDICIAL
Site com proteção Cloudflare e PJAX/AJAX.
Usa seletores do auctioneer_selectors.json
"""

import logging
import json
import os
from typing import Dict, Optional
from .playwright_base import PlaywrightBaseScraper

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
                if src and 'logo' not in src.lower():
                    prop["image_url"] = src if src.startswith("http") else self.BASE_URL + src
            
            # Categoria e tipo
            prop["category"] = self._determine_category(prop.get("title", ""))
            prop["auction_type"] = "Judicial"
            
            return prop if prop.get("title") else None
            
        except Exception as e:
            logger.debug(f"Erro ao extrair card: {e}")
            return None

