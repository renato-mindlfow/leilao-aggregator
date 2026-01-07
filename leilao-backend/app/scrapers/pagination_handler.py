#!/usr/bin/env python3
"""
MÓDULO DE PAGINAÇÃO INTELIGENTE
Detecta e navega automaticamente por diferentes tipos de paginação.
"""

import re
import logging
from typing import Optional, List, Dict, Callable, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class PaginationHandler:
    """
    Handler inteligente de paginação.
    Detecta automaticamente o tipo de paginação e gera URLs.
    """
    
    # Padrões comuns de parâmetros de paginação
    PAGE_PARAMS = ['page', 'pagina', 'p', 'pg', 'pag', 'offset', 'start']
    
    # Padrões de URL de paginação
    URL_PATTERNS = [
        r'\?.*page=(\d+)',
        r'\?.*pagina=(\d+)',
        r'\?.*p=(\d+)',
        r'/page/(\d+)',
        r'/pagina/(\d+)',
        r'/p/(\d+)',
    ]
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.detected_pattern = None
        self.detected_param = None
        self.total_pages = None
        self.items_per_page = None
    
    def detect_pagination_from_html(self, html: str) -> Dict:
        """
        Detecta o tipo de paginação analisando o HTML.
        Retorna informações sobre a paginação encontrada.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            "has_pagination": False,
            "type": None,
            "total_pages": None,
            "next_url": None,
            "page_urls": [],
            "param": None,
        }
        
        # 1. Procurar links de paginação
        pagination_selectors = [
            'nav.pagination a',
            '.pagination a',
            '[class*="pagination"] a',
            '[class*="paging"] a',
            'ul.pagination a',
            '.page-numbers a',
            '[class*="page-link"]',
            'a[href*="page="]',
            'a[href*="pagina="]',
            'a[href*="/page/"]',
        ]
        
        page_links = []
        for selector in pagination_selectors:
            links = soup.select(selector)
            if links:
                page_links.extend(links)
                break
        
        if page_links:
            result["has_pagination"] = True
            
            # Extrair URLs e detectar padrão
            for link in page_links:
                href = link.get('href', '')
                if href:
                    result["page_urls"].append(href)
                    
                    # Detectar padrão
                    for pattern in self.URL_PATTERNS:
                        match = re.search(pattern, href)
                        if match:
                            result["type"] = "query_param" if "?" in pattern else "path"
                            
                            # Extrair parâmetro
                            for param in self.PAGE_PARAMS:
                                if param in href.lower():
                                    result["param"] = param
                                    self.detected_param = param
                                    break
                            break
            
            # Tentar encontrar total de páginas
            # Procurar último número em links de paginação
            page_numbers = []
            for link in page_links:
                text = link.get_text(strip=True)
                if text.isdigit():
                    page_numbers.append(int(text))
                
                # Também verificar href
                href = link.get('href', '')
                for pattern in self.URL_PATTERNS:
                    match = re.search(pattern, href)
                    if match:
                        page_numbers.append(int(match.group(1)))
            
            if page_numbers:
                result["total_pages"] = max(page_numbers)
                self.total_pages = result["total_pages"]
        
        # 2. Procurar botão "próxima página" ou "carregar mais"
        next_selectors = [
            'a[rel="next"]',
            'a.next',
            'a[class*="next"]',
            'button[class*="next"]',
            'a:contains("Próxima")',
            'a:contains("Próximo")',
            'a:contains(">")',
            '[class*="load-more"]',
            '[class*="loadmore"]',
        ]
        
        for selector in next_selectors:
            try:
                next_elem = soup.select_one(selector)
                if next_elem:
                    result["has_pagination"] = True
                    if next_elem.name == 'a':
                        result["next_url"] = next_elem.get('href')
                    result["type"] = result["type"] or "next_button"
                    break
            except:
                continue
        
        # 3. Procurar indicador de total (ex: "Mostrando 1-20 de 756")
        total_patterns = [
            r'de\s+(\d+)\s+(?:resultado|imóve|imo|item|lote)',
            r'total[:\s]+(\d+)',
            r'(\d+)\s+(?:resultado|imóve|imo|item|lote)s?\s+encontrad',
            r'mostrando.*?de\s+(\d+)',
        ]
        
        page_text = soup.get_text().lower()
        for pattern in total_patterns:
            match = re.search(pattern, page_text)
            if match:
                total_items = int(match.group(1))
                # Estimar páginas (assumindo ~20-50 items por página)
                if not result["total_pages"] and total_items > 50:
                    result["total_pages"] = (total_items // 48) + 1
                break
        
        # 4. Detectar infinite scroll
        if not result["has_pagination"]:
            infinite_indicators = [
                'data-infinite',
                'infinite-scroll',
                'data-page',
                'load-more',
            ]
            
            html_lower = html.lower()
            for indicator in infinite_indicators:
                if indicator in html_lower:
                    result["has_pagination"] = True
                    result["type"] = "infinite_scroll"
                    break
        
        self.detected_pattern = result["type"]
        return result
    
    def get_page_url(self, page_num: int, base_url: str = None) -> str:
        """
        Gera URL para uma página específica.
        """
        url = base_url or self.base_url
        
        if page_num == 1:
            # Remover parâmetros de paginação da URL base
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            # Remover parâmetros de página
            for param in self.PAGE_PARAMS:
                query_params.pop(param, None)
            
            new_query = urlencode(query_params, doseq=True)
            return urlunparse(parsed._replace(query=new_query))
        
        # Determinar qual parâmetro usar
        param = self.detected_param or 'pagina'
        
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Remover parâmetros de página existentes
        for p in self.PAGE_PARAMS:
            query_params.pop(p, None)
        
        # Adicionar novo parâmetro
        query_params[param] = [str(page_num)]
        
        new_query = urlencode(query_params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
    
    def estimate_total_pages(self, items_on_first_page: int, total_items: int = None) -> int:
        """
        Estima o número total de páginas.
        """
        if self.total_pages:
            return self.total_pages
        
        if total_items and items_on_first_page > 0:
            return (total_items // items_on_first_page) + 1
        
        # Default conservador
        return 50


class PaginatedScraper:
    """
    Mixin para adicionar paginação a qualquer scraper.
    """
    
    def __init__(self):
        self.pagination = None
        self.max_pages = 100  # Limite de segurança
        self.items_per_page = 0
    
    def setup_pagination(self, base_url: str, html: str = None):
        """
        Configura o handler de paginação.
        """
        self.pagination = PaginationHandler(base_url)
        
        if html:
            info = self.pagination.detect_pagination_from_html(html)
            logger.info(f"📄 Paginação detectada: {info}")
            
            if info.get("total_pages"):
                self.max_pages = min(info["total_pages"], self.max_pages)
                logger.info(f"   Total de páginas: {self.max_pages}")
    
    def get_page_url(self, page_num: int) -> str:
        """
        Retorna URL para página específica.
        """
        if self.pagination:
            return self.pagination.get_page_url(page_num)
        return self.base_url
    
    def should_continue_pagination(self, page_num: int, items_found: int, consecutive_empty: int = 0) -> bool:
        """
        Determina se deve continuar paginando.
        """
        # Parar se atingiu máximo de páginas
        if page_num >= self.max_pages:
            logger.info(f"🛑 Atingiu máximo de páginas ({self.max_pages})")
            return False
        
        # Parar se muitas páginas vazias consecutivas
        if consecutive_empty >= 2:
            logger.info(f"🛑 {consecutive_empty} páginas vazias consecutivas")
            return False
        
        return True

