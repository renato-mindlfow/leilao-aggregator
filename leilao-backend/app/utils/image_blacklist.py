"""
Blacklist de URLs de imagens.

Contém padrões de URLs que devem ser ignorados durante a extração de imagens,
como logos de bancos, ícones, placeholders, etc.
"""

import re
from typing import List, Set
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

# URLs específicas de logos de bancos e instituições
BANK_LOGO_DOMAINS = {
    # Caixa Econômica Federal
    "caixa.gov.br",
    "caixaeconomica.com.br",
    
    # Outros bancos
    "bb.com.br",
    "bancodobrasil.com.br",
    "bradesco.com.br",
    "itau.com.br",
    "santander.com.br",
    "safra.com.br",
    "banrisul.com.br",
    "sicredi.com.br",
    "sicoob.com.br",
}

# Padrões de URL que indicam logos/ícones (regex)
LOGO_URL_PATTERNS = [
    r'/logo[s]?/',
    r'/logo[s]?\.',
    r'[-_]logo[-_.]',
    r'/icon[s]?/',
    r'/icon[s]?\.',
    r'[-_]icon[-_.]',
    r'/favicon',
    r'/brand/',
    r'/branding/',
    r'/marca/',
    r'/banner[s]?/',
    r'/header[-_]?img',
    r'/footer[-_]?img',
    r'/sprite[s]?/',
    r'/svg/',
    r'\.svg$',
    r'\.ico$',
]

# Padrões de nome de arquivo que indicam logos/placeholders
LOGO_FILENAME_PATTERNS = [
    r'logo',
    r'icon',
    r'favicon',
    r'brand',
    r'marca',
    r'banner',
    r'placeholder',
    r'default[-_]image',
    r'no[-_]?image',
    r'sem[-_]?foto',
    r'sem[-_]?imagem',
    r'loading',
    r'spinner',
    r'avatar',
    r'profile[-_]?pic',
    r'user[-_]?pic',
    r'thumb[-_]?default',
    r'empty',
    r'blank',
    r'spacer',
    r'pixel',
    r'tracking',
    r'analytics',
    r'1x1',
    r'transparent',
]

# Padrões de redes sociais e terceiros
SOCIAL_PATTERNS = [
    r'facebook\.com',
    r'fb\.com',
    r'twitter\.com',
    r'instagram\.com',
    r'linkedin\.com',
    r'youtube\.com',
    r'whatsapp\.com',
    r'google\.com/.*logo',
    r'googleusercontent\.com/.*icon',
    r'gstatic\.com',
    r'googleapis\.com/.*icon',
]

# Dimensões mínimas (imagens menores são provavelmente ícones)
MIN_WIDTH = 200
MIN_HEIGHT = 200


class ImageBlacklist:
    """
    Verificador de blacklist de imagens.
    
    Uso:
        blacklist = ImageBlacklist()
        if blacklist.is_blacklisted(url):
            # Ignorar esta URL
    """
    
    def __init__(self, custom_patterns: List[str] = None):
        """
        Args:
            custom_patterns: Padrões adicionais para bloquear
        """
        # Compila patterns para performance
        all_patterns = LOGO_URL_PATTERNS + LOGO_FILENAME_PATTERNS + SOCIAL_PATTERNS
        if custom_patterns:
            all_patterns.extend(custom_patterns)
        
        self._logo_url_regex = re.compile(
            '|'.join(LOGO_URL_PATTERNS),
            re.IGNORECASE
        )
        self._logo_filename_regex = re.compile(
            '|'.join(LOGO_FILENAME_PATTERNS),
            re.IGNORECASE
        )
        self._social_regex = re.compile(
            '|'.join(SOCIAL_PATTERNS),
            re.IGNORECASE
        )
        
        # URLs específicas conhecidas
        self.specific_urls = {
            'venda-imoveis.caixa.gov.br/imagens/logo',
            'caixa.gov.br/PublishingImages/logo',
            'download-lista.asp',
        }
        
        self.stats = {
            "total_checked": 0,
            "blocked": 0,
            "allowed": 0
        }
    
    def is_blacklisted(self, url: str) -> bool:
        """
        Verifica se uma URL de imagem deve ser ignorada.
        
        Args:
            url: URL da imagem
            
        Returns:
            True se deve ser ignorada, False caso contrário
        """
        return self.is_blocked(url)
    
    def is_blocked(self, url: str) -> bool:
        """
        Verifica se uma URL de imagem deve ser bloqueada.
        
        Args:
            url: URL da imagem
            
        Returns:
            True se deve ser bloqueada, False se é válida
        """
        if not url:
            return True
        
        self.stats["total_checked"] += 1
        url_lower = url.lower()
        
        # Verificar URLs específicas conhecidas
        for blocked_url in self.specific_urls:
            if blocked_url in url_lower:
                self.stats["blocked"] += 1
                logger.debug(f"Imagem bloqueada (URL específica): {url[:100]}")
                return True
        
        # 1. Verifica domínios de bancos
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            for bank_domain in BANK_LOGO_DOMAINS:
                if bank_domain in domain:
                    # Se é domínio de banco, verifica se parece ser logo
                    if self._is_likely_logo(url):
                        self.stats["blocked"] += 1
                        logger.debug(f"Blacklisted (bank logo): {url}")
                        return True
        except:
            pass
        
        # 2. Verifica padrões de URL de logo
        if self._logo_url_regex.search(url_lower):
            self.stats["blocked"] += 1
            logger.debug(f"Blacklisted (logo URL pattern): {url}")
            return True
        
        # 3. Verifica padrões de nome de arquivo
        if self._logo_filename_regex.search(url_lower):
            self.stats["blocked"] += 1
            logger.debug(f"Blacklisted (logo filename): {url}")
            return True
        
        # 4. Verifica redes sociais
        if self._social_regex.search(url_lower):
            self.stats["blocked"] += 1
            logger.debug(f"Blacklisted (social media): {url}")
            return True
        
        # 5. Verifica dimensões na URL (ex: image_50x50.jpg)
        if self._has_small_dimensions(url_lower):
            self.stats["blocked"] += 1
            logger.debug(f"Blacklisted (small dimensions): {url}")
            return True
        
        # 6. Verificar extensão válida
        if not self._has_valid_extension(url_lower):
            self.stats["blocked"] += 1
            logger.debug(f"Imagem bloqueada (extensão inválida): {url[:100]}")
            return True
        
        self.stats["allowed"] += 1
        return False
    
    def _is_likely_logo(self, url: str) -> bool:
        """Verifica se URL parece ser de um logo."""
        url_lower = url.lower()
        
        logo_indicators = [
            'logo', 'icon', 'marca', 'brand',
            'header', 'footer', 'nav', 'menu'
        ]
        
        return any(indicator in url_lower for indicator in logo_indicators)
    
    def _has_small_dimensions(self, url: str) -> bool:
        """Verifica se a URL contém dimensões pequenas."""
        # Procura padrões como: _50x50, -100x100, /200x200/
        pattern = r'[/_-](\d+)x(\d+)[/_.-]'
        match = re.search(pattern, url)
        
        if match:
            try:
                width = int(match.group(1))
                height = int(match.group(2))
                
                if width < MIN_WIDTH or height < MIN_HEIGHT:
                    return True
            except:
                pass
        
        return False
    
    def _has_valid_extension(self, url: str) -> bool:
        """
        Verifica se a URL tem uma extensão de imagem válida.
        """
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
        
        # Extrair path da URL
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Verificar extensão no path
            for ext in valid_extensions:
                if path.endswith(ext):
                    return True
            
            # Alguns CDNs não têm extensão no path, mas têm formato no query
            # Ex: image.jpg?w=500 ou ?format=jpg
            query = parsed.query.lower()
            if 'format=' in query or 'type=' in query:
                for ext in valid_extensions:
                    ext_name = ext[1:]  # Remove o ponto
                    if f'format={ext_name}' in query or f'type={ext_name}' in query:
                        return True
            
            # Se não tem extensão clara mas parece ser de um CDN de imagens, permitir
            image_cdns = ['cloudinary', 'imgix', 'cloudfront', 'akamai', 'fastly', 'cdn']
            if any(cdn in url for cdn in image_cdns):
                return True
            
            return False
            
        except Exception:
            return False
    
    def filter_urls(self, urls: List[str]) -> List[str]:
        """
        Filtra uma lista de URLs, removendo as blacklistadas.
        
        Args:
            urls: Lista de URLs de imagens
            
        Returns:
            Lista filtrada
        """
        return self.filter_images(urls)
    
    def filter_images(self, urls: List[str]) -> List[str]:
        """
        Filtra uma lista de URLs, removendo as bloqueadas.
        
        Args:
            urls: Lista de URLs de imagens
            
        Returns:
            Lista de URLs válidas
        """
        filtered = [url for url in urls if url and not self.is_blocked(url)]
        
        removed = len(urls) - len(filtered)
        if removed > 0:
            logger.info(f"Blacklist: removidas {removed} de {len(urls)} imagens")
        
        return filtered
    
    def get_stats(self) -> dict:
        """Retorna estatísticas de filtragem."""
        total = self.stats.get("total_checked", 0)
        blocked = self.stats.get("blocked", 0)
        return {
            **self.stats,
            "block_rate": round(blocked / total * 100, 2) if total > 0 else 0
        }
    
    def add_to_blacklist(self, url_or_pattern: str, is_pattern: bool = False):
        """
        Adiciona uma URL ou padrão à blacklist.
        
        Args:
            url_or_pattern: URL específica ou padrão regex
            is_pattern: Se True, trata como regex
        """
        if is_pattern:
            # Adicionar ao regex de padrões
            compiled = re.compile(url_or_pattern, re.IGNORECASE)
            if not hasattr(self, '_custom_patterns'):
                self._custom_patterns = []
            self._custom_patterns.append(compiled)
        else:
            self.specific_urls.add(url_or_pattern.lower())


# Instância global para uso conveniente
_blacklist = ImageBlacklist()

def is_blacklisted_image(url: str) -> bool:
    """Função de conveniência para verificar blacklist."""
    return _blacklist.is_blacklisted(url)

def filter_images(urls: List[str]) -> List[str]:
    """Função de conveniência para filtrar lista de URLs."""
    return _blacklist.filter_images(urls)

def is_valid_property_image(url: str) -> bool:
    """
    Função de conveniência para verificar se uma imagem é válida.
    
    Args:
        url: URL da imagem
        
    Returns:
        True se é uma imagem válida de imóvel
    """
    return not _blacklist.is_blocked(url)

def filter_property_images(urls: List[str]) -> List[str]:
    """
    Função de conveniência para filtrar lista de imagens.
    
    Args:
        urls: Lista de URLs
        
    Returns:
        Lista de URLs válidas
    """
    return _blacklist.filter_images(urls)

def get_image_blacklist() -> ImageBlacklist:
    """Retorna a instância singleton da blacklist."""
    return _blacklist

