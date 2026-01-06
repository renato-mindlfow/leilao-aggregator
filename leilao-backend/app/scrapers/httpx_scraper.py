"""
HTTPX Scraper - Scraper base usando httpx para requisições HTTP assíncronas.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HttpxScraper:
    """Scraper base usando httpx para requisições HTTP assíncronas."""
    
    def __init__(self, timeout: float = 30.0, headers: Optional[Dict[str, str]] = None):
        """
        Inicializa o scraper httpx.
        
        Args:
            timeout: Timeout em segundos para requisições
            headers: Headers customizados (opcional)
        """
        self.timeout = timeout
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        if headers:
            self.default_headers.update(headers)
    
    async def fetch(self, url: str, headers: Optional[Dict[str, str]] = None, 
                    follow_redirects: bool = True) -> Optional[httpx.Response]:
        """
        Faz uma requisição HTTP GET.
        
        Args:
            url: URL para fazer a requisição
            headers: Headers adicionais (opcional)
            follow_redirects: Se deve seguir redirects
        
        Returns:
            Response object ou None em caso de erro
        """
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=follow_redirects,
                verify=False  # Para desenvolvimento, em produção usar True
            ) as client:
                response = await client.get(url, headers=request_headers)
                return response
        except Exception as e:
            logger.error(f"Erro ao fazer requisição para {url}: {e}")
            return None
    
    async def fetch_html(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Faz uma requisição HTTP GET e retorna o HTML.
        
        Args:
            url: URL para fazer a requisição
            headers: Headers adicionais (opcional)
        
        Returns:
            HTML como string ou None em caso de erro
        """
        response = await self.fetch(url, headers)
        
        if response and response.status_code == 200:
            return response.text
        else:
            if response:
                logger.warning(f"Status code {response.status_code} para {url}")
            return None
    
    async def fetch_soup(self, url: str, headers: Optional[Dict[str, str]] = None, 
                        parser: str = 'html.parser') -> Optional[BeautifulSoup]:
        """
        Faz uma requisição HTTP GET e retorna BeautifulSoup object.
        
        Args:
            url: URL para fazer a requisição
            headers: Headers adicionais (opcional)
            parser: Parser do BeautifulSoup (default: 'html.parser')
        
        Returns:
            BeautifulSoup object ou None em caso de erro
        """
        html = await self.fetch_html(url, headers)
        
        if html:
            return BeautifulSoup(html, parser)
        return None
    
    async def post(self, url: str, data: Optional[Dict] = None, 
                  json_data: Optional[Dict] = None,
                  headers: Optional[Dict[str, str]] = None) -> Optional[httpx.Response]:
        """
        Faz uma requisição HTTP POST.
        
        Args:
            url: URL para fazer a requisição
            data: Dados para enviar como form data
            json_data: Dados para enviar como JSON
            headers: Headers adicionais (opcional)
        
        Returns:
            Response object ou None em caso de erro
        """
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                verify=False
            ) as client:
                if json_data:
                    response = await client.post(url, json=json_data, headers=request_headers)
                elif data:
                    response = await client.post(url, data=data, headers=request_headers)
                else:
                    response = await client.post(url, headers=request_headers)
                return response
        except Exception as e:
            logger.error(f"Erro ao fazer POST para {url}: {e}")
            return None
