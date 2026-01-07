#!/usr/bin/env python3
"""
SCRAPER PARA SODRÉ SANTORO
Validado visualmente em 2026-01-07.
Não requer Playwright - HTTP simples funciona.
"""

import httpx
import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

IMOVEIS_KEYWORDS = ['apartamento', 'casa', 'terreno', 'sala', 'galpão', 'fazenda', 'sítio', 'chácara', 'imóvel']
REJEITAR_KEYWORDS = ['veículo', 'carro', 'moto', 'caminhão', 'máquina', 'trator']

class SodreSantoroScraper:
    """Scraper para Sodré Santoro."""
    
    BASE_URL = "https://www.sodresantoro.com.br"
    IMOVEIS_URL = "https://www.sodresantoro.com.br/imoveis"
    AUCTIONEER_ID = "sodresantoro"
    AUCTIONEER_NAME = "Sodré Santoro"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'pt-BR,pt;q=0.9',
        }
    
    def _is_imovel(self, text: str) -> bool:
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
        if any(x in text_lower for x in ['apartamento', 'apto']):
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
    
    def scrape(self, max_properties: int = None, max_pages: int = 10) -> List[Dict]:
        """Executa scraping."""
        properties = []
        current_page = 1
        
        logger.info(f"🔍 Scraping Sodré Santoro: {self.IMOVEIS_URL}")
        
        try:
            with httpx.Client(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
                while current_page <= max_pages:
                    url = self.IMOVEIS_URL
                    if current_page > 1:
                        url = f"{self.IMOVEIS_URL}?page={current_page}"
                    
                    logger.info(f"  📄 Página {current_page}")
                    
                    response = client.get(url)
                    if response.status_code != 200:
                        break
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Seletores verificados visualmente
                    # Tentar múltiplos seletores
                    cards = soup.select(".item, [class*='item'], article, .card, [class*='card'], [class*='lote']")
                    
                    if not cards:
                        break
                    
                    logger.info(f"  📦 {len(cards)} cards encontrados")
                    
                    page_count = 0
                    for card in cards:
                        card_text = card.get_text()
                        
                        # Filtrar apenas imóveis
                        if not self._is_imovel(card_text):
                            continue
                        
                        prop = self._extract_property(card)
                        if prop and prop.get("source_url"):
                            if not any(p.get("source_url") == prop["source_url"] for p in properties):
                                properties.append(prop)
                                page_count += 1
                    
                    logger.info(f"  ✅ {page_count} imóveis extraídos")
                    
                    if max_properties and len(properties) >= max_properties:
                        break
                    
                    if page_count == 0:
                        break
                    
                    current_page += 1
        
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
        
        logger.info(f"✅ Total: {len(properties)} imóveis de Sodré Santoro")
        return properties[:max_properties] if max_properties else properties
    
    def _extract_property(self, card) -> Optional[Dict]:
        """Extrai dados de um card."""
        try:
            prop = {
                "auctioneer_id": self.AUCTIONEER_ID,
                "auctioneer_name": self.AUCTIONEER_NAME,
                "auctioneer_url": self.BASE_URL,
                "scraped_at": datetime.now().isoformat(),
            }
            
            # Link - tentar múltiplos padrões
            link = card.select_one("a[href*='/leilao'], a[href*='/lote'], a[href*='/imovel'], a")
            if link:
                href = link.get("href", "")
                if href:
                    # Se o link já contém o subdomínio leilao, usar diretamente
                    if 'leilao.sodresantoro.com.br' in href:
                        prop["source_url"] = href if href.startswith("http") else "https://" + href.lstrip("/")
                    else:
                        prop["source_url"] = urljoin(self.BASE_URL, href)
                    prop["url"] = prop["source_url"]
            
            if not prop.get("source_url"):
                return None
            
            # Título
            title = card.select_one(".title, h3, h4, [class*='title']")
            prop["title"] = title.get_text(strip=True) if title else "Imóvel"
            
            # Preço
            price = card.select_one("[class*='valor'], [class*='price']")
            if price:
                prop["first_auction_value"] = self._parse_price(price.get_text())
            
            # Localização
            loc = card.select_one("[class*='cidade'], [class*='local']")
            if loc:
                state, city = self._extract_state_city(loc.get_text())
                prop["state"] = state
                prop["city"] = city
            
            # Imagem
            img = card.select_one("img")
            if img:
                src = img.get("src") or img.get("data-src")
                if src and 'logo' not in src.lower():
                    prop["image_url"] = urljoin(self.BASE_URL, src)
            
            prop["category"] = self._determine_category(prop.get("title", ""))
            prop["auction_type"] = "Extrajudicial"
            
            return prop
        except:
            return None

