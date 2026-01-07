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

from app.scrapers.playwright_base import PlaywrightBaseScraper

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
                        logger.info(f"Página {current_page}: {len(new_properties)} novos imóveis (total: {len(properties)})")
                        
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
        
        except Exception as e:
            logger.error(f"Erro fatal no scraping: {e}")
        
        logger.info(f"Scraping concluído: {len(properties)} imóveis extraídos")
        return properties[:max_properties]
    
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
                'extracted_at': datetime.now().isoformat()
            }
            
            # Link
            link_elem = await card.query_selector(self.selectors['property_link'])
            if link_elem:
                href = await link_elem.get_attribute('href')
                if href:
                    prop['url'] = urljoin(self.BASE_URL, href)
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
                prop['price'] = (await price_elem.inner_text()).strip()
            
            # Localização
            location_elem = await card.query_selector(self.selectors['location'])
            if location_elem:
                prop['location'] = (await location_elem.inner_text()).strip()
            
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

