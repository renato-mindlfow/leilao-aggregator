"""
MultiLayerFetcher - Sistema de 4 camadas de fallback para extração robusta.

Camadas:
1. Fetch direto (httpx) - Grátis, rápido
2. Headers avançados (simula browser real) - Grátis
3. ScrapingBee (renderiza JS, bypassa proteções) - Pago
4. Jina.ai Reader (converte para markdown limpo) - Grátis até 1M/mês
"""

import httpx
import logging
import asyncio
import os
from typing import Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class FetchLayer(Enum):
    DIRECT = "direct"
    ADVANCED_HEADERS = "advanced_headers"
    SCRAPINGBEE = "scrapingbee"
    JINA_READER = "jina_reader"

@dataclass
class FetchResult:
    success: bool
    content: str
    layer_used: FetchLayer
    content_length: int
    error: Optional[str] = None

class MultiLayerFetcher:
    """
    Fetcher com 4 camadas de fallback para máxima taxa de sucesso.
    """
    
    def __init__(
        self,
        scrapingbee_api_key: Optional[str] = None,
        timeout: float = 30.0,
        min_content_length: int = 1000
    ):
        self.scrapingbee_api_key = scrapingbee_api_key or os.getenv("SCRAPINGBEE_API_KEY")
        self.timeout = timeout
        self.min_content_length = min_content_length
        
        # Headers que simulam um navegador real
        self.browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
    
    async def fetch(self, url: str) -> FetchResult:
        """
        Tenta buscar a URL usando as 4 camadas em sequência.
        Retorna assim que uma camada obtiver sucesso.
        """
        
        # CAMADA 1: Fetch direto
        result = await self._layer1_direct_fetch(url)
        if self._is_valid_result(result):
            logger.info(f"[Layer 1 SUCCESS] {url} - {result.content_length} chars")
            return result
        logger.warning(f"[Layer 1 FAILED] {url} - {result.error}")
        
        # CAMADA 2: Headers avançados
        result = await self._layer2_advanced_headers(url)
        if self._is_valid_result(result):
            logger.info(f"[Layer 2 SUCCESS] {url} - {result.content_length} chars")
            return result
        logger.warning(f"[Layer 2 FAILED] {url} - {result.error}")
        
        # CAMADA 3: ScrapingBee
        if self.scrapingbee_api_key:
            result = await self._layer3_scrapingbee(url)
            if self._is_valid_result(result):
                logger.info(f"[Layer 3 SUCCESS] {url} - {result.content_length} chars")
                return result
            logger.warning(f"[Layer 3 FAILED] {url} - {result.error}")
        else:
            logger.info(f"[Layer 3 SKIPPED] ScrapingBee API key not configured")
        
        # CAMADA 4: Jina.ai Reader
        result = await self._layer4_jina_reader(url)
        if self._is_valid_result(result):
            logger.info(f"[Layer 4 SUCCESS] {url} - {result.content_length} chars")
            return result
        logger.warning(f"[Layer 4 FAILED] {url} - {result.error}")
        
        # Todas as camadas falharam
        return FetchResult(
            success=False,
            content="",
            layer_used=FetchLayer.JINA_READER,
            content_length=0,
            error=f"All 4 layers failed for {url}"
        )
    
    def _is_valid_result(self, result: FetchResult) -> bool:
        """Verifica se o resultado é válido (sucesso + conteúdo suficiente + não é Cloudflare)."""
        if not result.success:
            return False
        if result.content_length < self.min_content_length:
            return False
        # Detecta páginas de challenge do Cloudflare
        cloudflare_indicators = [
            "Just a moment",
            "Checking your browser",
            "Enable JavaScript",
            "cf-browser-verification",
            "Cloudflare Ray ID"
        ]
        for indicator in cloudflare_indicators:
            if indicator in result.content:
                result.error = f"Cloudflare challenge detected: {indicator}"
                return False
        return True
    
    async def _layer1_direct_fetch(self, url: str) -> FetchResult:
        """Camada 1: Fetch HTTP direto com User-Agent básico."""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                headers = {"User-Agent": self.browser_headers["User-Agent"]}
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    content = response.text
                    return FetchResult(
                        success=True,
                        content=content,
                        layer_used=FetchLayer.DIRECT,
                        content_length=len(content)
                    )
                else:
                    return FetchResult(
                        success=False,
                        content="",
                        layer_used=FetchLayer.DIRECT,
                        content_length=0,
                        error=f"HTTP {response.status_code}"
                    )
        except Exception as e:
            return FetchResult(
                success=False,
                content="",
                layer_used=FetchLayer.DIRECT,
                content_length=0,
                error=str(e)
            )
    
    async def _layer2_advanced_headers(self, url: str) -> FetchResult:
        """Camada 2: Fetch com headers completos de browser real."""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                http2=True  # HTTP/2 para parecer mais com browser moderno
            ) as client:
                response = await client.get(url, headers=self.browser_headers)
                
                if response.status_code == 200:
                    content = response.text
                    return FetchResult(
                        success=True,
                        content=content,
                        layer_used=FetchLayer.ADVANCED_HEADERS,
                        content_length=len(content)
                    )
                else:
                    return FetchResult(
                        success=False,
                        content="",
                        layer_used=FetchLayer.ADVANCED_HEADERS,
                        content_length=0,
                        error=f"HTTP {response.status_code}"
                    )
        except Exception as e:
            return FetchResult(
                success=False,
                content="",
                layer_used=FetchLayer.ADVANCED_HEADERS,
                content_length=0,
                error=str(e)
            )
    
    async def _layer3_scrapingbee(self, url: str) -> FetchResult:
        """Camada 3: ScrapingBee com renderização JavaScript."""
        try:
            scrapingbee_url = "https://app.scrapingbee.com/api/v1/"
            params = {
                "api_key": self.scrapingbee_api_key,
                "url": url,
                "render_js": "true",
                "premium_proxy": "true",
                "country_code": "br",
                "wait": "3000",  # Espera 3s para JS carregar
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(scrapingbee_url, params=params)
                
                if response.status_code == 200:
                    content = response.text
                    return FetchResult(
                        success=True,
                        content=content,
                        layer_used=FetchLayer.SCRAPINGBEE,
                        content_length=len(content)
                    )
                else:
                    return FetchResult(
                        success=False,
                        content="",
                        layer_used=FetchLayer.SCRAPINGBEE,
                        content_length=0,
                        error=f"ScrapingBee HTTP {response.status_code}"
                    )
        except Exception as e:
            return FetchResult(
                success=False,
                content="",
                layer_used=FetchLayer.SCRAPINGBEE,
                content_length=0,
                error=str(e)
            )
    
    async def _layer4_jina_reader(self, url: str) -> FetchResult:
        """
        Camada 4: Jina.ai Reader API.
        
        GRÁTIS até 1M requisições/mês!
        Converte qualquer página em markdown/HTML limpo.
        Bypassa Cloudflare automaticamente.
        """
        try:
            jina_url = f"https://r.jina.ai/{url}"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {
                    "Accept": "text/html",
                    "X-Return-Format": "html"  # Pede HTML ao invés de markdown
                }
                
                response = await client.get(jina_url, headers=headers)
                
                if response.status_code == 200:
                    content = response.text
                    return FetchResult(
                        success=True,
                        content=content,
                        layer_used=FetchLayer.JINA_READER,
                        content_length=len(content)
                    )
                else:
                    return FetchResult(
                        success=False,
                        content="",
                        layer_used=FetchLayer.JINA_READER,
                        content_length=0,
                        error=f"Jina Reader HTTP {response.status_code}"
                    )
        except Exception as e:
            return FetchResult(
                success=False,
                content="",
                layer_used=FetchLayer.JINA_READER,
                content_length=0,
                error=str(e)
            )


# Função de conveniência para uso simples
async def fetch_with_fallbacks(url: str) -> Tuple[bool, str, str]:
    """
    Função de conveniência que retorna (success, content, layer_used).
    """
    fetcher = MultiLayerFetcher()
    result = await fetcher.fetch(url)
    return result.success, result.content, result.layer_used.value

