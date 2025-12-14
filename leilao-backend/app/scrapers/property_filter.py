"""
Property filter module to ensure only real estate items are collected.
Excludes vehicles, machinery, electronics, and other non-property items.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Categories that ARE real estate (imóveis)
CATEGORIAS_IMOVEIS = [
    'apartamento', 'casa', 'terreno', 'comercial',
    'rural', 'garagem', 'vaga', 'lote', 'sobrado',
    'cobertura', 'kitnet', 'studio', 'chácara',
    'fazenda', 'sítio', 'galpão', 'sala', 'loja',
    'prédio', 'edifício', 'flat', 'duplex', 'triplex',
    'penthouse', 'bangalô', 'chalé', 'rancho',
    'armazém', 'depósito', 'escritório', 'consultório',
    'ponto comercial', 'imóvel', 'imovel', 'residencial',
    'residência', 'moradia', 'habitação', 'propriedade',
    'área', 'gleba', 'fração', 'unidade'
]

# Words that indicate NON-property items (to exclude)
PALAVRAS_EXCLUIR = [
    # Vehicles
    'carro', 'moto', 'motocicleta', 'caminhão', 'caminhao',
    'veículo', 'veiculo', 'automóvel', 'automovel', 'auto',
    'ônibus', 'onibus', 'van', 'pickup', 'picape',
    'trator', 'reboque', 'carreta', 'cavalo mecânico',
    'empilhadeira', 'retroescavadeira', 'escavadeira',
    'motoniveladora', 'pá carregadeira', 'rolo compactador',
    # Machinery/Equipment
    'máquina', 'maquina', 'equipamento', 'ferramenta',
    'gerador', 'compressor', 'motor', 'bomba',
    # Electronics
    'eletrônico', 'eletronico', 'computador', 'notebook',
    'celular', 'smartphone', 'tablet', 'televisão', 'televisao',
    'tv', 'monitor', 'impressora', 'servidor',
    # Jewelry/Art
    'joia', 'jóia', 'relógio', 'relogio', 'anel', 'colar',
    'pulseira', 'brinco', 'obra de arte', 'quadro', 'escultura',
    # Other non-property
    'móvel', 'movel', 'mobília', 'mobilia', 'sofá', 'sofa',
    'mesa', 'cadeira', 'armário', 'armario', 'estante',
    'eletrodoméstico', 'eletrodomestico', 'geladeira', 'fogão',
    'crédito', 'credito', 'direito', 'ação', 'acao', 'quota',
    'participação', 'participacao', 'título', 'titulo',
    'semovente', 'gado', 'boi', 'vaca', 'cavalo', 'animal'
]

# URL patterns that indicate property listings
URL_PATTERNS_IMOVEIS = [
    '/imoveis/', '/imovel/', '/apartamento/', '/casa/',
    '/terreno/', '/comercial/', '/rural/', '/lote/',
    '/residencial/', '/property/', '/real-estate/'
]

# URL patterns that indicate NON-property listings
URL_PATTERNS_EXCLUIR = [
    '/veiculos/', '/veiculo/', '/automoveis/', '/automovel/',
    '/carros/', '/carro/', '/motos/', '/moto/',
    '/maquinas/', '/maquina/', '/equipamentos/', '/equipamento/',
    '/outros/', '/diversos/', '/bens-moveis/'
]


def is_property(item: Dict[str, Any], strict: bool = False) -> bool:
    """
    Check if an item is a real estate property.
    
    Args:
        item: Dictionary with property data (must have 'title' and optionally 'category', 'source_url')
        strict: If True, requires explicit property indicators. If False, excludes only clear non-properties.
    
    Returns:
        True if the item is a property, False otherwise
    """
    title = item.get('title', '').lower()
    category = item.get('category', '').lower()
    source_url = item.get('source_url', '').lower()
    description = item.get('description', '').lower() if item.get('description') else ''
    
    combined_text = f"{title} {category} {description}"
    
    # First check: URL patterns (most reliable)
    for pattern in URL_PATTERNS_EXCLUIR:
        if pattern in source_url:
            logger.debug(f"Excluded by URL pattern '{pattern}': {title[:50]}")
            return False
    
    for pattern in URL_PATTERNS_IMOVEIS:
        if pattern in source_url:
            # URL indicates property, but still check for exclusion words
            break
    
    # Second check: Exclusion words (high priority)
    for palavra in PALAVRAS_EXCLUIR:
        if palavra in combined_text:
            logger.debug(f"Excluded by word '{palavra}': {title[:50]}")
            return False
    
    # Third check: Property indicators
    for cat in CATEGORIAS_IMOVEIS:
        if cat in combined_text:
            logger.debug(f"Accepted by category '{cat}': {title[:50]}")
            return True
    
    # If strict mode, require explicit property indicator
    if strict:
        logger.debug(f"Excluded (strict mode, no property indicator): {title[:50]}")
        return False
    
    # In non-strict mode, accept if no exclusion words found
    # This handles cases where the category might not be explicitly stated
    logger.debug(f"Accepted (no exclusion words found): {title[:50]}")
    return True


def filter_properties(items: list, strict: bool = False) -> tuple:
    """
    Filter a list of items to keep only real estate properties.
    
    Args:
        items: List of dictionaries with property data
        strict: If True, requires explicit property indicators
    
    Returns:
        Tuple of (accepted_items, rejected_items)
    """
    accepted = []
    rejected = []
    
    for item in items:
        if is_property(item, strict=strict):
            accepted.append(item)
        else:
            rejected.append(item)
    
    logger.info(f"Property filter: {len(accepted)} accepted, {len(rejected)} rejected out of {len(items)} total")
    
    return accepted, rejected


def get_filter_stats(items: list) -> Dict[str, int]:
    """
    Get statistics about filtering results.
    
    Args:
        items: List of dictionaries with property data
    
    Returns:
        Dictionary with filter statistics
    """
    accepted, rejected = filter_properties(items)
    
    return {
        'total': len(items),
        'accepted': len(accepted),
        'rejected': len(rejected),
        'acceptance_rate': round(len(accepted) / len(items) * 100, 1) if items else 0
    }
