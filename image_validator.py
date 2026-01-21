"""
Validador de Imagens para LeiloHub
==================================
Filtra URLs de imagens inválidas (logos, placeholders, banners, etc.)

Uso:
    from image_validator import ImageValidator
    
    validator = ImageValidator()
    
    # Validar uma URL
    is_valid, reason = validator.validate_url("https://example.com/image.jpg")
    
    # Limpar URL (retorna None se inválida)
    clean_url = validator.clean_url("https://example.com/logo.png")
    
    # Processar lista de imóveis
    properties = validator.process_properties(properties_list)

Autor: Claude - Engenheiro Chefe LeiloHub
Data: 20/01/2026
"""

import json
import re
import os
from typing import Optional, Tuple, List, Dict
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class ImageValidator:
    """Validador de URLs de imagens para filtrar logos, placeholders e imagens inválidas."""
    
    def __init__(self, blacklist_path: Optional[str] = None):
        """
        Inicializa o validador com a blacklist.
        
        Args:
            blacklist_path: Caminho para o arquivo JSON de blacklist.
                           Se None, usa o padrão no mesmo diretório.
        """
        if blacklist_path is None:
            blacklist_path = os.path.join(os.path.dirname(__file__), 'image_blacklist.json')
        
        self.blacklist = self._load_blacklist(blacklist_path)
        self._compile_patterns()
    
    def _load_blacklist(self, path: str) -> dict:
        """Carrega a blacklist do arquivo JSON."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Blacklist não encontrada em {path}, usando padrões padrão")
            return self._get_default_blacklist()
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear blacklist: {e}")
            return self._get_default_blacklist()
    
    def _get_default_blacklist(self) -> dict:
        """Retorna blacklist padrão caso o arquivo não exista."""
        return {
            "url_patterns": {
                "logos": ["logo", "logotipo", "brand"],
                "placeholders": ["placeholder", "no-image", "sem-foto", "default"],
                "banners": ["banner", "header", "footer"],
                "icons": ["icon", "favicon"]
            },
            "domain_blacklist": ["facebook.com", "twitter.com", "instagram.com"],
            "file_patterns": {
                "extensions_to_ignore": [".svg", ".gif", ".ico"],
                "min_dimensions": {"width": 200, "height": 200}
            }
        }
    
    def _compile_patterns(self):
        """Compila os padrões regex para melhor performance."""
        all_patterns = []
        
        # Adicionar padrões de URL
        url_patterns = self.blacklist.get("url_patterns", {})
        for category, patterns in url_patterns.items():
            all_patterns.extend(patterns)
        
        # Adicionar padrões de logos de bancos
        bank_logos = self.blacklist.get("bank_logos", {}).get("patterns", [])
        all_patterns.extend(bank_logos)
        
        # Adicionar padrões de logos de leiloeiros
        auctioneer_logos = self.blacklist.get("auctioneer_logos", {}).get("patterns", [])
        all_patterns.extend(auctioneer_logos)
        
        # Compilar regex único para todos os padrões (case insensitive)
        if all_patterns:
            pattern_str = '|'.join(re.escape(p) for p in all_patterns)
            self._blacklist_regex = re.compile(pattern_str, re.IGNORECASE)
        else:
            self._blacklist_regex = None
        
        # Compilar padrões de whitelist
        whitelist_patterns = self.blacklist.get("whitelist_patterns", {}).get("patterns", [])
        if whitelist_patterns:
            whitelist_str = '|'.join(re.escape(p) for p in whitelist_patterns)
            self._whitelist_regex = re.compile(whitelist_str, re.IGNORECASE)
        else:
            self._whitelist_regex = None
    
    def validate_url(self, url: Optional[str]) -> Tuple[bool, str]:
        """
        Valida uma URL de imagem.
        
        Args:
            url: URL da imagem a ser validada
            
        Returns:
            Tupla (is_valid, reason) onde:
            - is_valid: True se a URL é válida
            - reason: Motivo da invalidação ou "OK"
        """
        # Verificar se URL existe
        if not url or not isinstance(url, str):
            return False, "URL vazia ou inválida"
        
        url = url.strip()
        if len(url) < 10:
            return False, "URL muito curta"
        
        # Verificar se é uma URL válida
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "URL mal formada"
        except Exception:
            return False, "Erro ao parsear URL"
        
        url_lower = url.lower()
        
        # Verificar extensões inválidas
        extensions_to_ignore = self.blacklist.get("file_patterns", {}).get("extensions_to_ignore", [])
        for ext in extensions_to_ignore:
            if url_lower.endswith(ext):
                return False, f"Extensão inválida: {ext}"
        
        # Verificar domínios na blacklist
        domain_blacklist = self.blacklist.get("domain_blacklist", [])
        for domain in domain_blacklist:
            if domain in url_lower:
                return False, f"Domínio na blacklist: {domain}"
        
        # Verificar se está na whitelist (válido automaticamente)
        if self._whitelist_regex and self._whitelist_regex.search(url_lower):
            # Mesmo na whitelist, verificar se tem padrões muito ruins
            critical_patterns = ['logo', 'placeholder', 'no-image', 'sem-foto']
            for pattern in critical_patterns:
                if pattern in url_lower:
                    return False, f"Padrão crítico encontrado: {pattern}"
            return True, "OK (whitelist)"
        
        # Verificar padrões da blacklist
        if self._blacklist_regex and self._blacklist_regex.search(url_lower):
            match = self._blacklist_regex.search(url_lower)
            return False, f"Padrão inválido: {match.group()}"
        
        # Verificar domínios conhecidos como válidos
        known_valid = self.blacklist.get("known_valid_domains", {}).get("domains", [])
        for domain in known_valid:
            if domain in url_lower:
                return True, "OK (domínio confiável)"
        
        return True, "OK"
    
    def clean_url(self, url: Optional[str]) -> Optional[str]:
        """
        Limpa e valida uma URL de imagem.
        
        Args:
            url: URL a ser validada
            
        Returns:
            URL original se válida, None se inválida
        """
        is_valid, reason = self.validate_url(url)
        if is_valid:
            return url.strip() if url else None
        else:
            logger.debug(f"URL rejeitada: {url[:100]}... Motivo: {reason}")
            return None
    
    def process_properties(self, properties: List[Dict]) -> List[Dict]:
        """
        Processa uma lista de imóveis, limpando URLs de imagem inválidas.
        
        Args:
            properties: Lista de dicionários com dados de imóveis
            
        Returns:
            Lista processada com image_url = None para imagens inválidas
        """
        stats = {
            "total": len(properties),
            "valid": 0,
            "invalid": 0,
            "no_image": 0,
            "reasons": {}
        }
        
        for prop in properties:
            original_url = prop.get("image_url")
            
            if not original_url:
                stats["no_image"] += 1
                continue
            
            is_valid, reason = self.validate_url(original_url)
            
            if is_valid:
                stats["valid"] += 1
            else:
                stats["invalid"] += 1
                prop["image_url"] = None
                prop["image_validation_reason"] = reason
                
                # Contabilizar razões
                if reason not in stats["reasons"]:
                    stats["reasons"][reason] = 0
                stats["reasons"][reason] += 1
        
        # Log resumo
        logger.info(f"Validação de imagens: {stats['valid']} válidas, "
                   f"{stats['invalid']} inválidas, {stats['no_image']} sem imagem")
        
        if stats["reasons"]:
            logger.info(f"Motivos de rejeição: {stats['reasons']}")
        
        return properties
    
    def get_stats(self, properties: List[Dict]) -> Dict:
        """
        Gera estatísticas de validação de imagens para uma lista de imóveis.
        
        Args:
            properties: Lista de imóveis
            
        Returns:
            Dicionário com estatísticas
        """
        stats = {
            "total": len(properties),
            "with_image": 0,
            "without_image": 0,
            "valid_images": 0,
            "invalid_images": 0,
            "validation_details": {}
        }
        
        for prop in properties:
            url = prop.get("image_url")
            
            if not url:
                stats["without_image"] += 1
                continue
            
            stats["with_image"] += 1
            is_valid, reason = self.validate_url(url)
            
            if is_valid:
                stats["valid_images"] += 1
            else:
                stats["invalid_images"] += 1
                if reason not in stats["validation_details"]:
                    stats["validation_details"][reason] = 0
                stats["validation_details"][reason] += 1
        
        # Calcular percentuais
        if stats["total"] > 0:
            stats["pct_with_image"] = round(100 * stats["with_image"] / stats["total"], 1)
            stats["pct_valid"] = round(100 * stats["valid_images"] / max(stats["with_image"], 1), 1)
        
        return stats


# Instância global para uso conveniente
_validator = None

def get_validator() -> ImageValidator:
    """Retorna instância singleton do validador."""
    global _validator
    if _validator is None:
        _validator = ImageValidator()
    return _validator


def validate_image_url(url: str) -> Tuple[bool, str]:
    """Função de conveniência para validar uma URL."""
    return get_validator().validate_url(url)


def clean_image_url(url: str) -> Optional[str]:
    """Função de conveniência para limpar uma URL."""
    return get_validator().clean_url(url)


# =============================================================================
# TESTES
# =============================================================================

if __name__ == "__main__":
    # Configurar logging para testes
    logging.basicConfig(level=logging.DEBUG)
    
    validator = ImageValidator()
    
    # Testes de URLs
    test_urls = [
        # Válidas
        ("https://cdn.megaleiloes.com.br/imoveis/12345.jpg", True),
        ("https://images.superbid.com/property/abc.jpg", True),
        ("https://example.com/fotos/apartamento.jpg", True),
        
        # Inválidas - logos
        ("https://site.com/logo.png", False),
        ("https://site.com/images/logotipo.jpg", False),
        
        # Inválidas - placeholders
        ("https://site.com/placeholder.jpg", False),
        ("https://site.com/no-image.png", False),
        ("https://site.com/sem-foto.jpg", False),
        
        # Inválidas - extensões
        ("https://site.com/icon.svg", False),
        ("https://site.com/loading.gif", False),
        
        # Inválidas - domínios
        ("https://facebook.com/image.jpg", False),
        ("https://gravatar.com/avatar/123", False),
        
        # Edge cases
        ("", False),
        (None, False),
        ("not-a-url", False),
    ]
    
    print("=" * 60)
    print("TESTES DE VALIDAÇÃO DE IMAGENS")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for url, expected in test_urls:
        is_valid, reason = validator.validate_url(url)
        status = "✅ PASS" if is_valid == expected else "❌ FAIL"
        
        if is_valid == expected:
            passed += 1
        else:
            failed += 1
        
        url_display = url[:50] + "..." if url and len(url) > 50 else url
        print(f"{status} | {url_display}")
        print(f"       Esperado: {expected} | Resultado: {is_valid} | Motivo: {reason}")
        print()
    
    print("=" * 60)
    print(f"RESULTADO: {passed} passou, {failed} falhou")
    print("=" * 60)
