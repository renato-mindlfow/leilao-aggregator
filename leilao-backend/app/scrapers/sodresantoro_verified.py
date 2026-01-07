#!/usr/bin/env python3
"""
SCRAPER PARA SODRÉ SANTORO
Validado visualmente em 2026-01-07.
URL /imoveis já filtra apenas imóveis.
"""

import httpx
import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

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
    
    def _parse_price(self, price_str: str) -> Optional[float]:
        if not price_str:
            return None
        try:
            # Encontrar valor no texto
            match = re.search(r'R\$\s*([\d.,]+)', price_str)
            if match:
                clean = match.group(1).replace('.', '').replace(',', '.')
                return float(clean)
            # Tentar parse direto
            clean = re.sub(r'[R$\s.]', '', price_str)
            clean = clean.replace(',', '.')
            return float(clean)
        except:
            return None
    
    def _extract_state_city(self, location: str) -> tuple:
        if not location:
            return None, None
        
        location = location.strip()
        
        # Padrões comuns
        patterns = [
            r'^(.+?)\s*[-/,]\s*([A-Z]{2})$',  # Cidade - UF
            r'^([A-Z]{2})\s*[-/,]\s*(.+)$',   # UF - Cidade
            r'([A-Z]{2})$',                    # Só UF no final
        ]
        
        for pattern in patterns:
            match = re.search(pattern, location)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    if len(groups[0]) == 2:
                        return groups[0], groups[1].strip()
                    return groups[1], groups[0].strip()
                elif len(groups) == 1 and len(groups[0]) == 2:
                    return groups[0], location.replace(groups[0], '').strip(' -/')
        
        return None, location
    
    def _determine_category(self, text: str) -> str:
        if not text:
            return "Outro"
        
        text_lower = text.lower()
        
        if any(x in text_lower for x in ['apartamento', 'apto', 'cobertura', 'flat', 'kitnet']):
            return "Apartamento"
        if any(x in text_lower for x in ['casa', 'sobrado', 'residência', 'residencia']):
            return "Casa"
        if any(x in text_lower for x in ['terreno', 'lote', 'área', 'gleba']):
            return "Terreno"
        if any(x in text_lower for x in ['sala', 'loja', 'galpão', 'galpao', 'prédio', 'comercial', 'escritório']):
            return "Comercial"
        if any(x in text_lower for x in ['fazenda', 'sítio', 'sitio', 'chácara', 'chacara', 'rural', 'haras']):
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
                    
                    logger.info(f"  📄 Página {current_page}: {url}")
                    
                    response = client.get(url)
                    if response.status_code != 200:
                        logger.warning(f"  ⚠️ HTTP {response.status_code}")
                        break
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Tentar múltiplos seletores - priorizar links de lote
                    cards = []
                    selectors_to_try = [
                        "a[href*='/lote']",  # Prioridade: links de lote
                        "a[href*='/leilao']",
                        "a[href*='/imovel']",
                        "div.card",
                        "div.item",
                        "article",
                        "div[class*='lote']",
                        "div[class*='leilao']",
                    ]
                    
                    for selector in selectors_to_try:
                        cards = soup.select(selector)
                        if cards:
                            logger.info(f"  📦 Seletor '{selector}': {len(cards)} cards")
                            break
                    
                    if not cards:
                        # Última tentativa: encontrar todos os links de leilão/lote
                        links = soup.find_all('a', href=re.compile(r'/(leilao|lote|imovel)'))
                        if links:
                            logger.info(f"  📦 Links encontrados: {len(links)}")
                            cards = links
                    
                    if not cards:
                        logger.info(f"  ℹ️ Nenhum card na página {current_page}")
                        break
                    
                    page_count = 0
                    for card in cards:
                        # Como estamos em /imoveis, TODOS são imóveis
                        # Não precisa filtrar por palavra-chave
                        
                        prop = self._extract_property(card, soup)
                        if prop and prop.get("source_url"):
                            # Evitar duplicatas
                            if not any(p.get("source_url") == prop["source_url"] for p in properties):
                                properties.append(prop)
                                page_count += 1
                                
                                if page_count <= 3:
                                    logger.debug(f"    ✓ {prop.get('title', 'N/A')[:40]}")
                    
                    logger.info(f"  ✅ {page_count} imóveis extraídos")
                    
                    if max_properties and len(properties) >= max_properties:
                        break
                    
                    if page_count == 0:
                        break
                    
                    current_page += 1
        
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info(f"✅ Total: {len(properties)} imóveis de Sodré Santoro")
        return properties[:max_properties] if max_properties else properties
    
    def _extract_property(self, card, soup=None) -> Optional[Dict]:
        """Extrai dados de um card ou link."""
        try:
            prop = {
                "auctioneer_id": self.AUCTIONEER_ID,
                "auctioneer_name": self.AUCTIONEER_NAME,
                "auctioneer_url": self.BASE_URL,
                "scraped_at": datetime.now().isoformat(),
                "auction_type": "Extrajudicial",
            }
            
            # Se o card é um link <a>
            if card.name == 'a':
                href = card.get("href", "")
                prop["source_url"] = urljoin(self.BASE_URL, href)
                prop["url"] = prop["source_url"]
                prop["title"] = card.get_text(strip=True) or "Imóvel"
            else:
                # Encontrar link dentro do card
                link = card.select_one("a[href*='/leilao'], a[href*='/lote'], a[href*='/imovel'], a")
                if link:
                    href = link.get("href", "")
                    prop["source_url"] = urljoin(self.BASE_URL, href)
                    prop["url"] = prop["source_url"]
                
                # Título
                title_elem = card.select_one("h1, h2, h3, h4, h5, .title, .titulo, [class*='title'], [class*='nome']")
                if title_elem:
                    prop["title"] = title_elem.get_text(strip=True)
                elif link:
                    prop["title"] = link.get_text(strip=True)
                else:
                    prop["title"] = card.get_text(strip=True)[:100]
            
            if not prop.get("source_url"):
                return None
            
            # Limpar título
            if prop.get("title"):
                prop["title"] = ' '.join(prop["title"].split())[:200]
            
            # Preço - tentar encontrar no card ou em elementos próximos
            price_selectors = [
                "[class*='valor']",
                "[class*='price']",
                "[class*='preco']",
                "[class*='lance']",
                "span.valor",
                "div.valor",
            ]
            
            for selector in price_selectors:
                price_elem = card.select_one(selector) if hasattr(card, 'select_one') else None
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    prop["first_auction_value"] = self._parse_price(price_text)
                    if prop["first_auction_value"]:
                        break
            
            # Se não encontrou preço no card, procurar no texto
            if not prop.get("first_auction_value"):
                card_text = card.get_text() if hasattr(card, 'get_text') else str(card)
                match = re.search(r'R\$\s*([\d.,]+)', card_text)
                if match:
                    prop["first_auction_value"] = self._parse_price(match.group(0))
            
            # Localização
            loc_selectors = [
                "[class*='cidade']",
                "[class*='local']",
                "[class*='endereco']",
                "[class*='location']",
            ]
            
            for selector in loc_selectors:
                loc_elem = card.select_one(selector) if hasattr(card, 'select_one') else None
                if loc_elem:
                    loc_text = loc_elem.get_text(strip=True)
                    state, city = self._extract_state_city(loc_text)
                    prop["state"] = state
                    prop["city"] = city
                    break
            
            # Imagem
            img = card.select_one("img") if hasattr(card, 'select_one') else None
            if img:
                src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                if src and not any(x in src.lower() for x in ['logo', 'icon', 'placeholder', 'avatar']):
                    prop["image_url"] = urljoin(self.BASE_URL, src)
            
            # Categoria baseada no título
            prop["category"] = self._determine_category(prop.get("title", ""))
            
            return prop
            
        except Exception as e:
            logger.debug(f"Erro ao extrair: {e}")
            return None

