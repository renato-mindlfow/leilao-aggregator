"""
Utility para normalizar categorias de imóveis

Garante que categorias sejam sempre salvas no formato correto (Title Case)
e previne duplicatas como "Apartamento" vs "APARTAMENTO"
"""

from typing import Optional

# Mapeamento canônico de categorias
CATEGORY_MAP = {
    'apartamento': 'Apartamento',
    'casa': 'Casa',
    'terreno': 'Terreno',
    'comercial': 'Comercial',
    'rural': 'Rural',
    'galpão': 'Galpão',
    'galpao': 'Galpão',
    'loja': 'Loja',
    'sala comercial': 'Sala Comercial',
    'prédio': 'Prédio',
    'predio': 'Prédio',
    'chácara': 'Chácara',
    'chacara': 'Chácara',
    'sitio': 'Sítio',
    'sítio': 'Sítio',
    'fazenda': 'Fazenda',
    'cobertura': 'Cobertura',
    'kitnet': 'Kitnet',
    'flat': 'Flat',
    'box': 'Box',
    'garagem': 'Garagem',
    'vaga de garagem': 'Vaga de Garagem',
    'estacionamento': 'Estacionamento',
    'outro': 'Outro',
    'outros': 'Outro',
    'industrial': 'Industrial',
    'área': 'Área',
    'area': 'Área',
    'imóvel rural': 'Rural',
    'imovel rural': 'Rural',
    'imovel': 'Outro',
}


def normalize_category(category: Optional[str]) -> str:
    """
    Normaliza a categoria de um imóvel para o formato padrão.
    
    Args:
        category: Categoria original (pode estar em qualquer case)
    
    Returns:
        Categoria normalizada em Title Case
    
    Examples:
        >>> normalize_category("APARTAMENTO")
        'Apartamento'
        >>> normalize_category("casa")
        'Casa'
        >>> normalize_category("Imóvel Rural")
        'Rural'
        >>> normalize_category(None)
        'Outro'
        >>> normalize_category("")
        'Outro'
    """
    # Tratar valores vazios ou None
    if not category or category.strip() == '' or category.lower() == 'none':
        return 'Outro'
    
    # Normalizar para lowercase e remover espaços extras
    category_clean = category.strip().lower()
    
    # Buscar no mapeamento
    if category_clean in CATEGORY_MAP:
        return CATEGORY_MAP[category_clean]
    
    # Se não encontrar no mapa, usar Title Case
    return category.strip().title()


def normalize_city(city: Optional[str]) -> Optional[str]:
    """
    Normaliza o nome de uma cidade para Title Case.
    
    Args:
        city: Nome da cidade
    
    Returns:
        Nome da cidade em Title Case ou None
    
    Examples:
        >>> normalize_city("RIO DE JANEIRO")
        'Rio De Janeiro'
        >>> normalize_city("são paulo")
        'São Paulo'
        >>> normalize_city(None)
        None
    """
    if not city or city.strip() == '':
        return None
    
    return city.strip().title()


def normalize_neighborhood(neighborhood: Optional[str]) -> Optional[str]:
    """
    Normaliza o nome de um bairro para Title Case.
    
    Args:
        neighborhood: Nome do bairro
    
    Returns:
        Nome do bairro em Title Case ou None
    
    Examples:
        >>> normalize_neighborhood("CENTRO")
        'Centro'
        >>> normalize_neighborhood("jardim catarina")
        'Jardim Catarina'
        >>> normalize_neighborhood(None)
        None
        >>> normalize_neighborhood("")
        None
    """
    if not neighborhood or neighborhood.strip() == '':
        return None
    
    return neighborhood.strip().title()


def get_valid_categories() -> list[str]:
    """
    Retorna a lista de categorias válidas/canônicas.
    
    Returns:
        Lista ordenada de categorias válidas
    """
    # Pegar valores únicos do mapeamento
    unique_categories = sorted(set(CATEGORY_MAP.values()))
    return unique_categories


def is_valid_category(category: str) -> bool:
    """
    Verifica se uma categoria está no formato canônico.
    
    Args:
        category: Categoria a verificar
    
    Returns:
        True se está no formato correto, False caso contrário
    
    Examples:
        >>> is_valid_category("Apartamento")
        True
        >>> is_valid_category("APARTAMENTO")
        False
        >>> is_valid_category("casa")
        False
    """
    if not category:
        return False
    
    return category in get_valid_categories()

