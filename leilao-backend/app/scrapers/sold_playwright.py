#!/usr/bin/env python3
"""
SCRAPER PARA SOLD LEILÕES
Usa API Superbid diretamente conforme configurado em auctioneer_selectors.json
"""

import logging
import json
import os
import asyncio
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class SoldPlaywrightScraper:
    """
    Scraper para Sold Leilões usando API Superbid diretamente.
    Configuração carregada de auctioneer_selectors.json.
    """
    
    BASE_URL = "https://www.sold.com.br"
    AUCTIONEER_ID = "sold"
    AUCTIONEER_NAME = "Sold Leilões"
    LISTING_URL = "https://www.sold.com.br/h/imoveis"
    
    def __init__(self):
        self.selector_config = self._load_selector_config()
        self.api_config = self._get_api_config()
    
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
    
    def _get_api_config(self) -> Optional[Dict]:
        """Extrai configuração da API."""
        if not self.selector_config:
            return None
        
        return self.selector_config.get('api')
    
    async def scrape_properties(self, max_properties: int = 150) -> List[Dict[str, Any]]:
        """
        Faz scraping de propriedades do Sold via API.
        
        Args:
            max_properties: Número máximo de propriedades a extrair
            
        Returns:
            Lista de propriedades extraídas
        """
        if not self.api_config:
            logger.error("Configuração de API não encontrada")
            return []
        
        properties = []
        api_url = self.api_config.get('base_url')
        api_params = self.api_config.get('params', {}).copy()
        pagination = self.api_config.get('pagination', {})
        response_mapping = self.api_config.get('response_mapping', {})
        
        max_pages = pagination.get('max_pages', 10)
        items_per_page = pagination.get('items_per_page', 50)
        current_page = pagination.get('start', 1)
        max_items = pagination.get('max_items', max_properties)
        
        logger.info(f"Iniciando scraping de {self.AUCTIONEER_NAME} via API (max: {max_items} imóveis)")
        
        while len(properties) < max_items and current_page <= max_pages:
            api_params[pagination.get('param', 'pageNumber')] = current_page
            api_params['pageSize'] = items_per_page
            
            logger.info(f"Buscando página {current_page}...")
            
            try:
                response = requests.get(api_url, params=api_params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                offers = data.get(response_mapping.get('items_field', 'offers'), [])
                total = data.get(response_mapping.get('total_field', 'total'), 0)
                
                if current_page == 1:
                    logger.info(f"Total disponível na API: {total}")
                
                logger.info(f"Recebidos {len(offers)} itens na página {current_page}")
                
                if len(offers) == 0:
                    logger.info("Nenhum item recebido, parando...")
                    break
                
                # Processar cada oferta
                for offer in offers:
                    if len(properties) >= max_items:
                        break
                    
                    prop = self._map_api_response_to_property(offer, response_mapping)
                    if prop:
                        properties.append(prop)
                
                # Se recebeu menos itens que o pageSize, é a última página
                if len(offers) < items_per_page:
                    logger.info("Última página atingida")
                    break
                
                current_page += 1
                await asyncio.sleep(1.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Erro ao buscar página {current_page}: {e}")
                break
        
        logger.info(f"Scraping concluído: {len(properties)} imóveis extraídos")
        return properties[:max_items]
    
    def _map_api_response_to_property(self, offer: Dict, mapping: Dict) -> Optional[Dict]:
        """Mapeia resposta da API para formato de propriedade."""
        try:
            prop = {
                'auctioneer_id': self.AUCTIONEER_ID,
                'auctioneer_name': self.AUCTIONEER_NAME,
                'extracted_at': datetime.now().isoformat()
            }
            
            # URL
            link_url = offer.get(mapping.get('url_field', 'linkURL'), '')
            if not link_url:
                offer_id = offer.get(mapping.get('id_field', 'id'))
                if offer_id:
                    link_url = f"/produto/{offer_id}"
            
            if link_url:
                prop['url'] = urljoin(self.BASE_URL, link_url) if not link_url.startswith('http') else link_url
            
            # Título
            title_path = mapping.get('title_field', 'product.shortDesc').split('.')
            title = offer
            for key in title_path:
                title = title.get(key, {}) if isinstance(title, dict) else None
                if title is None:
                    break
            prop['title'] = str(title)[:200] if title else ""
            
            # Preço
            price = offer.get(mapping.get('price_field', 'priceFormatted'), '')
            prop['price'] = price
            
            # Imagem
            image_path = mapping.get('image_field', 'product.thumbnailUrl').split('.')
            image = offer
            for key in image_path:
                image = image.get(key, {}) if isinstance(image, dict) else None
                if image is None:
                    break
            prop['image_url'] = str(image) if image else ""
            
            # Categoria
            category_path = mapping.get('category_field', 'product.productType.description').split('.')
            category = offer
            for key in category_path:
                category = category.get(key, {}) if isinstance(category, dict) else None
                if category is None:
                    break
            prop['category'] = str(category) if category else ""
            
            return prop if prop.get('url') else None
        
        except Exception as e:
            logger.debug(f"Erro ao mapear resposta da API: {e}")
            return None
    
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

