#!/usr/bin/env python3
"""
SCRAPER PARA MEGA LEILÕES
Herda de PlaywrightBaseScraper com paginação automática.
SPA React - requer aguardar carregamento.
"""

import logging
from typing import Dict, Optional
from .playwright_base import PlaywrightBaseScraper

logger = logging.getLogger(__name__)

# Filtro de imóveis
IMOVEIS_KEYWORDS = ['apartamento', 'casa', 'terreno', 'sala', 'galpão', 'fazenda', 'sítio', 'chácara', 'imóvel', 'cobertura']
REJEITAR_KEYWORDS = ['veículo', 'carro', 'moto', 'caminhão', 'máquina', 'trator', 'ônibus']

class MegaLeiloesPlaywrightScraper(PlaywrightBaseScraper):
    """Scraper para Mega Leilões."""
    
    BASE_URL = "https://www.megaleiloes.com.br"
    LISTING_URL = "https://www.megaleiloes.com.br/imoveis"
    AUCTIONEER_ID = "megaleiloes"
    AUCTIONEER_NAME = "Mega Leilões"
    
    # SPA React precisa mais tempo
    WAIT_TIME = 10
    MAX_PAGES = 50
    
    # Seletores específicos do Mega Leilões
    SELECTORS = {
        "property_cards": [
            ".card", "[class*='card']", "[class*='imovel']",
            "[class*='property']", "article"
        ],
        "property_link": [
            "a[href*='/imovel/']", "a[href*='/lote/']", "a"
        ],
        "title": [
            ".card-title", "h3", "h4", "[class*='title']", "[class*='titulo']"
        ],
        "price": [
            "[class*='price']", "[class*='valor']", "[class*='lance']", "[class*='preco']"
        ],
        "location": [
            "[class*='location']", "[class*='cidade']", "[class*='local']", "[class*='endereco']"
        ],
        "image": ["img"],
        "pagination": [
            ".pagination a", "[class*='pagination'] a", "a[href*='pagina=']"
        ],
        "next_page": [
            "a[rel='next']", "a.next", "[class*='next']"
        ],
    }
    
    def _is_imovel(self, text: str) -> bool:
        """Verifica se é imóvel (não veículo)."""
        if not text:
            return True  # Se não tem texto, assume que é imóvel
        text_lower = text.lower()
        for kw in REJEITAR_KEYWORDS:
            if kw in text_lower:
                return False
        for kw in IMOVEIS_KEYWORDS:
            if kw in text_lower:
                return True
        return True  # Default: assume imóvel
    
    async def _extract_property(self, card) -> Optional[Dict]:
        """Extrai dados de um card com filtro de imóveis."""
        try:
            # Verificar se é imóvel antes de extrair
            card_text = await card.inner_text()
            if not self._is_imovel(card_text):
                return None
            
            # Usar método da base class
            prop = await super()._extract_property(card)
            
            if prop:
                prop["auction_type"] = "Extrajudicial"
            
            return prop
        except Exception as e:
            logger.debug(f"Erro ao extrair card: {e}")
            return None
