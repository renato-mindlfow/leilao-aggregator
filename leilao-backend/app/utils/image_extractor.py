"""
ImageExtractor - Extração robusta de URLs de imagens.

Problemas resolvidos:
1. Regex restritivo (só CDN) → Regex universal
2. Lazy-loaded images ignoradas → data-src, data-lazy capturados
3. URLs relativas não resolvidas → Conversão para absolutas
"""

import re
from typing import List, Set
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)

class ImageExtractor:
    """
    Extrator robusto de URLs de imagens de HTML.
    """
    
    # Extensões de imagem válidas
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.avif'}
    
    # Atributos que podem conter URLs de imagens
    IMAGE_ATTRIBUTES = [
        'src',
        'data-src',
        'data-lazy',
        'data-lazy-src',
        'data-original',
        'data-srcset',
        'srcset',
        'data-bg',
        'data-background',
        'data-image',
        'data-img',
        'data-url',
        'data-full',
        'data-zoom',
        'data-large',
        'data-high-res',
        'content',  # Para meta tags og:image
    ]
    
    # Padrões a EXCLUIR (logos, ícones, placeholders)
    EXCLUDE_PATTERNS = [
        r'logo',
        r'icon',
        r'favicon',
        r'placeholder',
        r'loading',
        r'spinner',
        r'avatar',
        r'profile',
        r'banner',
        r'ad[s]?[_-]',
        r'tracking',
        r'pixel',
        r'spacer',
        r'transparent',
        r'blank',
        r'1x1',
        r'facebook',
        r'twitter',
        r'instagram',
        r'whatsapp',
        r'linkedin',
        r'youtube',
        r'google',
        r'analytics',
        r'cdn\..*\.(svg|ico)',
    ]
    
    def __init__(self, base_url: str):
        """
        Args:
            base_url: URL base para resolver URLs relativas.
        """
        self.base_url = base_url
        parsed = urlparse(base_url)
        self.domain = f"{parsed.scheme}://{parsed.netloc}"
        self._exclude_regex = re.compile('|'.join(self.EXCLUDE_PATTERNS), re.IGNORECASE)
    
    def extract_all(self, html: str) -> List[str]:
        """
        Extrai todas as URLs de imagens do HTML.
        
        Returns:
            Lista de URLs absolutas de imagens, sem duplicatas.
        """
        found_urls: Set[str] = set()
        
        # Método 1: Regex para tags <img>
        found_urls.update(self._extract_from_img_tags(html))
        
        # Método 2: Regex para atributos data-*
        found_urls.update(self._extract_from_data_attributes(html))
        
        # Método 3: Regex para URLs diretas no texto
        found_urls.update(self._extract_direct_urls(html))
        
        # Método 4: Background images em CSS inline
        found_urls.update(self._extract_from_css(html))
        
        # Método 5: Meta tags og:image e twitter:image
        found_urls.update(self._extract_from_meta_tags(html))
        
        # Filtrar e limpar
        clean_urls = []
        for url in found_urls:
            clean_url = self._clean_and_validate(url)
            if clean_url and not self._should_exclude(clean_url):
                clean_urls.append(clean_url)
        
        # Remover duplicatas mantendo ordem
        seen = set()
        unique_urls = []
        for url in clean_urls:
            normalized = self._normalize_url(url)
            if normalized not in seen:
                seen.add(normalized)
                unique_urls.append(url)
        
        # Aplica blacklist para remover logos e placeholders
        from app.utils.image_blacklist import filter_images
        filtered_urls = filter_images(unique_urls)
        
        logger.info(f"Extracted {len(unique_urls)} unique images from {self.base_url}, {len(filtered_urls)} after blacklist")
        return filtered_urls
    
    def _extract_from_img_tags(self, html: str) -> Set[str]:
        """Extrai de tags <img>."""
        urls = set()
        
        # Regex para capturar toda a tag <img>
        img_pattern = r'<img\s+[^>]*?(?:src|data-src|data-lazy|data-original)\s*=\s*["\']([^"\']+)["\'][^>]*?>'
        
        for match in re.finditer(img_pattern, html, re.IGNORECASE | re.DOTALL):
            url = match.group(1)
            urls.add(url)
        
        # Padrão alternativo para atributos em qualquer ordem
        for attr in self.IMAGE_ATTRIBUTES:
            pattern = rf'{attr}\s*=\s*["\']([^"\']+)["\']'
            for match in re.finditer(pattern, html, re.IGNORECASE):
                url = match.group(1)
                if self._looks_like_image_url(url):
                    urls.add(url)
        
        return urls
    
    def _extract_from_data_attributes(self, html: str) -> Set[str]:
        """Extrai de atributos data-* que contêm URLs de imagens."""
        urls = set()
        
        for attr in self.IMAGE_ATTRIBUTES:
            if attr.startswith('data-'):
                pattern = rf'{attr}\s*=\s*["\']([^"\']+)["\']'
                for match in re.finditer(pattern, html, re.IGNORECASE):
                    url = match.group(1)
                    if self._looks_like_image_url(url):
                        urls.add(url)
        
        return urls
    
    def _extract_direct_urls(self, html: str) -> Set[str]:
        """Extrai URLs de imagem que aparecem diretamente no texto."""
        urls = set()
        
        # Padrão universal para URLs de imagens
        pattern = r'https?://[^\s"\'<>\)\]]+\.(?:jpg|jpeg|png|webp|gif|avif)(?:\?[^\s"\'<>\)\]]*)?'
        
        for match in re.finditer(pattern, html, re.IGNORECASE):
            urls.add(match.group(0))
        
        return urls
    
    def _extract_from_css(self, html: str) -> Set[str]:
        """Extrai de background-image em CSS inline."""
        urls = set()
        
        # Padrão para background-image: url(...)
        pattern = r'background(?:-image)?\s*:\s*url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)'
        
        for match in re.finditer(pattern, html, re.IGNORECASE):
            url = match.group(1)
            if self._looks_like_image_url(url):
                urls.add(url)
        
        return urls
    
    def _extract_from_meta_tags(self, html: str) -> Set[str]:
        """Extrai de meta tags og:image e twitter:image."""
        urls = set()
        
        # og:image
        pattern = r'<meta\s+[^>]*?property\s*=\s*["\']og:image["\'][^>]*?content\s*=\s*["\']([^"\']+)["\']'
        for match in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
            urls.add(match.group(1))
        
        # Ordem invertida dos atributos
        pattern = r'<meta\s+[^>]*?content\s*=\s*["\']([^"\']+)["\'][^>]*?property\s*=\s*["\']og:image["\']'
        for match in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
            urls.add(match.group(1))
        
        # twitter:image
        pattern = r'<meta\s+[^>]*?(?:name|property)\s*=\s*["\']twitter:image["\'][^>]*?content\s*=\s*["\']([^"\']+)["\']'
        for match in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
            urls.add(match.group(1))
        
        return urls
    
    def _looks_like_image_url(self, url: str) -> bool:
        """Verifica se a URL parece ser de uma imagem."""
        if not url:
            return False
        
        # Remove query string para verificar extensão
        clean_url = url.split('?')[0].lower()
        
        for ext in self.IMAGE_EXTENSIONS:
            if clean_url.endswith(ext):
                return True
        
        # Alguns CDNs não têm extensão mas são imagens
        image_cdn_patterns = [
            r'cloudinary\.com',
            r'imgix\.net',
            r'cdn\.',
            r'images\.',
            r'fotos?\.',
            r'photos?\.',
        ]
        
        for pattern in image_cdn_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    def _clean_and_validate(self, url: str) -> str:
        """Limpa e valida uma URL, convertendo para absoluta se necessário."""
        if not url or not isinstance(url, str):
            return ""
        
        url = url.strip()
        
        # Remove caracteres problemáticos
        url = url.replace('\n', '').replace('\r', '').replace('\t', '')
        
        # Converte para URL absoluta
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = urljoin(self.domain, url)
        elif not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)
        
        # Valida URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ""
        except Exception:
            return ""
        
        return url
    
    def _should_exclude(self, url: str) -> bool:
        """Verifica se a URL deve ser excluída (logo, ícone, etc)."""
        if self._exclude_regex.search(url):
            return True
        
        # Exclui imagens muito pequenas (indicam ícones)
        size_pattern = r'[_-](\d+)x(\d+)\.'
        match = re.search(size_pattern, url)
        if match:
            width, height = int(match.group(1)), int(match.group(2))
            if width < 100 or height < 100:
                return True
        
        return False
    
    def _normalize_url(self, url: str) -> str:
        """Normaliza URL para comparação (remove query params variáveis)."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def extract_images(html: str, base_url: str) -> List[str]:
    """
    Função de conveniência para extrair imagens.
    
    Args:
        html: Conteúdo HTML
        base_url: URL base para resolver URLs relativas
        
    Returns:
        Lista de URLs absolutas de imagens
    """
    extractor = ImageExtractor(base_url)
    return extractor.extract_all(html)

