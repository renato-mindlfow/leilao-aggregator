"""
GenericPaginator - Sistema de paginação inteligente.

Padrões de paginação detectados:
1. Query string: ?page=2, ?p=2, ?pagina=2
2. Path segment: /page/2, /pagina/2
3. Infinite scroll: botão "Carregar mais"
4. API JSON: offset/limit

Funciona com:
- Sites tradicionais (HTML server-rendered)
- SPAs com paginação client-side
- APIs REST com paginação
"""

import re
import asyncio
from typing import List, Optional, Set, Callable, Awaitable, Dict, Any
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class PaginationConfig:
    """Configuração de paginação para um site específico."""
    pattern: str  # "query", "path", "api"
    param_name: str  # "page", "p", "pagina", "offset"
    start_page: int = 1
    max_pages: int = 50  # Limite de segurança
    items_per_page: int = 20  # Estimativa
    delay_between_pages: float = 1.0  # Delay em segundos

class GenericPaginator:
    """
    Paginador genérico que detecta automaticamente o padrão de paginação.
    """
    
    # Padrões de query string para paginação
    QUERY_PATTERNS = [
        r'[?&]page=(\d+)',
        r'[?&]p=(\d+)',
        r'[?&]pagina=(\d+)',
        r'[?&]pg=(\d+)',
        r'[?&]offset=(\d+)',
        r'[?&]start=(\d+)',
    ]
    
    # Padrões de path para paginação
    PATH_PATTERNS = [
        r'/page/(\d+)',
        r'/pagina/(\d+)',
        r'/p/(\d+)',
        r'/(\d+)/?$',  # URL terminando em número
    ]
    
    # Seletores CSS para links de "próxima página"
    NEXT_PAGE_SELECTORS = [
        'a.next',
        'a.proximo',
        'a.proxima',
        'a[rel="next"]',
        'a[aria-label="Next"]',
        'a[aria-label="Próximo"]',
        'a[aria-label="Próxima página"]',
        '.pagination a.next',
        '.pagination .next a',
        '.pager .next a',
        'nav.pagination a:last-child',
        'ul.pagination li:last-child a',
        'a:contains("Próxima")',
        'a:contains("Próximo")',
        'a:contains("Next")',
        'a:contains("»")',
        'a:contains(">")',
        'button.load-more',
        'button.carregar-mais',
        'a.load-more',
        'a.ver-mais',
    ]
    
    def __init__(
        self,
        fetch_func: Callable[[str], Awaitable[str]],
        extract_func: Callable[[str, str], List[Dict[str, Any]]],
        max_pages: int = 50,
        delay: float = 1.0,
        max_empty_pages: int = 2
    ):
        """
        Args:
            fetch_func: Função assíncrona que busca HTML de uma URL
            extract_func: Função que extrai itens do HTML (html, url) -> list
            max_pages: Número máximo de páginas a processar
            delay: Delay entre requisições em segundos
            max_empty_pages: Número de páginas vazias antes de parar
        """
        self.fetch_func = fetch_func
        self.extract_func = extract_func
        self.max_pages = max_pages
        self.delay = delay
        self.max_empty_pages = max_empty_pages
    
    async def paginate(self, start_url: str) -> List[Dict[str, Any]]:
        """
        Executa paginação começando da URL inicial.
        
        Returns:
            Lista de todos os itens extraídos de todas as páginas.
        """
        all_items: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()
        empty_pages_count = 0
        
        # Detecta padrão de paginação
        config = await self._detect_pagination_pattern(start_url)
        logger.info(f"Pagination pattern detected: {config.pattern} with param '{config.param_name}'")
        
        current_url = start_url
        page_num = config.start_page
        
        while page_num <= self.max_pages:
            # Evita URLs duplicadas
            normalized_url = self._normalize_url(current_url)
            if normalized_url in seen_urls:
                logger.info(f"URL already visited: {current_url}")
                break
            seen_urls.add(normalized_url)
            
            logger.info(f"Fetching page {page_num}: {current_url}")
            
            try:
                # Busca a página
                html = await self.fetch_func(current_url)
                
                if not html or len(html) < 500:
                    logger.warning(f"Empty or too short response for page {page_num}")
                    empty_pages_count += 1
                    if empty_pages_count >= self.max_empty_pages:
                        logger.info(f"Stopping: {empty_pages_count} empty pages in a row")
                        break
                    page_num += 1
                    current_url = self._build_next_page_url(start_url, page_num, config)
                    continue
                
                # Extrai itens
                items = self.extract_func(html, current_url)
                
                if not items:
                    empty_pages_count += 1
                    logger.info(f"No items found on page {page_num} (empty count: {empty_pages_count})")
                    if empty_pages_count >= self.max_empty_pages:
                        logger.info(f"Stopping: {empty_pages_count} empty pages in a row")
                        break
                else:
                    empty_pages_count = 0  # Reset counter
                    
                    # Filtra duplicatas
                    new_items = self._filter_duplicates(items, all_items)
                    all_items.extend(new_items)
                    
                    logger.info(f"Page {page_num}: {len(items)} items found, {len(new_items)} new (total: {len(all_items)})")
                
                # Encontra próxima página
                next_url = self._find_next_page_url(html, current_url, config)
                
                if next_url:
                    current_url = next_url
                else:
                    # Constrói URL da próxima página baseado no padrão
                    page_num += 1
                    current_url = self._build_next_page_url(start_url, page_num, config)
                
                # Delay entre páginas
                if self.delay > 0:
                    await asyncio.sleep(self.delay)
                    
            except Exception as e:
                logger.error(f"Error on page {page_num}: {e}")
                empty_pages_count += 1
                if empty_pages_count >= self.max_empty_pages:
                    break
                page_num += 1
                current_url = self._build_next_page_url(start_url, page_num, config)
        
        logger.info(f"Pagination complete: {len(all_items)} total items from {len(seen_urls)} pages")
        return all_items
    
    async def _detect_pagination_pattern(self, url: str) -> PaginationConfig:
        """
        Detecta o padrão de paginação analisando a URL e o HTML.
        """
        # Primeiro, tenta detectar pela URL
        for pattern in self.QUERY_PATTERNS:
            if re.search(pattern, url):
                param = pattern.split('=')[0].split('[?&]')[1]
                return PaginationConfig(
                    pattern="query",
                    param_name=param,
                    start_page=1
                )
        
        for pattern in self.PATH_PATTERNS:
            if re.search(pattern, url):
                return PaginationConfig(
                    pattern="path",
                    param_name="page",
                    start_page=1
                )
        
        # Busca a página inicial para analisar o HTML
        try:
            html = await self.fetch_func(url)
            
            # Procura links de paginação no HTML
            pagination_patterns = [
                (r'href=["\'][^"\']*[?&]page=\d+', 'query', 'page'),
                (r'href=["\'][^"\']*[?&]p=\d+', 'query', 'p'),
                (r'href=["\'][^"\']*[?&]pagina=\d+', 'query', 'pagina'),
                (r'href=["\'][^"\']*[?&]offset=\d+', 'query', 'offset'),
                (r'href=["\'][^"\']*[?&]start=\d+', 'query', 'start'),
                (r'href=["\'][^"\']*/page/\d+', 'path', 'page'),
                (r'href=["\'][^"\']*/pagina/\d+', 'path', 'pagina'),
            ]
            
            for pattern, ptype, param in pagination_patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    return PaginationConfig(
                        pattern=ptype,
                        param_name=param,
                        start_page=1
                    )
            
            # Procura por botões "Carregar mais" (infinite scroll)
            infinite_scroll_patterns = [
                r'load-more',
                r'carregar-mais',
                r'ver-mais',
                r'show-more',
                r'loadMore',
            ]
            
            for pattern in infinite_scroll_patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    return PaginationConfig(
                        pattern="infinite",
                        param_name="page",
                        start_page=1
                    )
                    
        except Exception as e:
            logger.warning(f"Error detecting pagination pattern: {e}")
        
        # Padrão default: query string com 'page'
        return PaginationConfig(
            pattern="query",
            param_name="page",
            start_page=1
        )
    
    def _build_next_page_url(self, base_url: str, page_num: int, config: PaginationConfig) -> str:
        """
        Constrói a URL da próxima página baseado no padrão detectado.
        """
        parsed = urlparse(base_url)
        
        if config.pattern == "query":
            # Adiciona/atualiza query parameter
            query_params = parse_qs(parsed.query)
            
            # Define o valor baseado no tipo de parâmetro
            if config.param_name in ['offset', 'start']:
                # Para offset, calcula baseado no número de itens por página
                query_params[config.param_name] = [str((page_num - 1) * config.items_per_page)]
            else:
                query_params[config.param_name] = [str(page_num)]
            
            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
            return new_url
            
        elif config.pattern == "path":
            # Adiciona/atualiza path segment
            path = parsed.path.rstrip('/')
            
            # Remove número de página existente
            path = re.sub(r'/page/\d+', '', path)
            path = re.sub(r'/pagina/\d+', '', path)
            path = re.sub(r'/\d+$', '', path)
            
            # Adiciona novo número
            new_path = f"{path}/page/{page_num}"
            
            new_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                new_path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            return new_url
        
        else:
            # Fallback: adiciona ?page=X
            if '?' in base_url:
                return f"{base_url}&page={page_num}"
            else:
                return f"{base_url}?page={page_num}"
    
    def _find_next_page_url(self, html: str, current_url: str, config: PaginationConfig) -> Optional[str]:
        """
        Procura link para a próxima página no HTML.
        """
        # Procura por padrões de link "próxima página"
        patterns = [
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*next[^"\']*["\']',
            r'<a[^>]*class=["\'][^"\']*next[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
            r'<a[^>]*rel=["\']next["\'][^>]*href=["\']([^"\']+)["\']',
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']next["\']',
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*aria-label=["\'][^"\']*[Nn]ext[^"\']*["\']',
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*aria-label=["\'][^"\']*[Pp]róxim[oa][^"\']*["\']',
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>[^<]*(?:Próxim[oa]|Next|»|>)[^<]*</a>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                href = match.group(1)
                # Resolve URL relativa
                full_url = urljoin(current_url, href)
                
                # Verifica se a URL é válida e diferente da atual
                if full_url != current_url and self._is_valid_pagination_url(full_url):
                    return full_url
        
        return None
    
    def _is_valid_pagination_url(self, url: str) -> bool:
        """
        Verifica se a URL parece ser uma página válida de paginação.
        """
        try:
            parsed = urlparse(url)
            
            # Deve ter scheme e netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Não deve ser um arquivo (pdf, jpg, etc)
            invalid_extensions = ['.pdf', '.jpg', '.png', '.gif', '.doc', '.xls']
            for ext in invalid_extensions:
                if parsed.path.lower().endswith(ext):
                    return False
            
            # Não deve ser javascript
            if url.lower().startswith('javascript:'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _filter_duplicates(
        self,
        new_items: List[Dict[str, Any]],
        existing_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filtra itens duplicados baseado em ID ou URL.
        """
        existing_ids = set()
        existing_urls = set()
        
        for item in existing_items:
            if item.get('id'):
                existing_ids.add(str(item['id']))
            if item.get('source_url'):
                existing_urls.add(item['source_url'])
            if item.get('url'):
                existing_urls.add(item['url'])
        
        unique_items = []
        for item in new_items:
            item_id = str(item.get('id', ''))
            item_url = item.get('source_url') or item.get('url', '')
            
            # Verifica se já existe
            if item_id and item_id in existing_ids:
                continue
            if item_url and item_url in existing_urls:
                continue
            
            unique_items.append(item)
            
            # Adiciona aos sets de controle
            if item_id:
                existing_ids.add(item_id)
            if item_url:
                existing_urls.add(item_url)
        
        return unique_items
    
    def _normalize_url(self, url: str) -> str:
        """
        Normaliza URL para comparação.
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


async def paginate_and_extract(
    start_url: str,
    fetch_func: Callable[[str], Awaitable[str]],
    extract_func: Callable[[str, str], List[Dict[str, Any]]],
    max_pages: int = 50,
    delay: float = 1.0
) -> List[Dict[str, Any]]:
    """
    Função de conveniência para paginação.
    
    Args:
        start_url: URL inicial para começar a paginação
        fetch_func: Função assíncrona (url) -> html
        extract_func: Função (html, url) -> list de items
        max_pages: Máximo de páginas a processar
        delay: Delay entre páginas em segundos
        
    Returns:
        Lista de todos os itens extraídos
    """
    paginator = GenericPaginator(
        fetch_func=fetch_func,
        extract_func=extract_func,
        max_pages=max_pages,
        delay=delay
    )
    return await paginator.paginate(start_url)

