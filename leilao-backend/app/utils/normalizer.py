"""
NORMALIZAÇÃO DE DADOS - EXECUTAR NA ENTRADA
Este módulo DEVE ser usado por TODOS os scrapers antes de salvar no banco.
"""

import re
from typing import Optional

# Mapeamento de estados (todas as variações)
STATE_MAP = {
    'AC': 'AC', 'Ac': 'AC', 'ac': 'AC',
    'AL': 'AL', 'Al': 'AL', 'al': 'AL',
    'AP': 'AP', 'Ap': 'AP', 'ap': 'AP',
    'AM': 'AM', 'Am': 'AM', 'am': 'AM',
    'BA': 'BA', 'Ba': 'BA', 'ba': 'BA',
    'CE': 'CE', 'Ce': 'CE', 'ce': 'CE',
    'DF': 'DF', 'Df': 'DF', 'df': 'DF',
    'ES': 'ES', 'Es': 'ES', 'es': 'ES',
    'GO': 'GO', 'Go': 'GO', 'go': 'GO',
    'MA': 'MA', 'Ma': 'MA', 'ma': 'MA',
    'MT': 'MT', 'Mt': 'MT', 'mt': 'MT',
    'MS': 'MS', 'Ms': 'MS', 'ms': 'MS',
    'MG': 'MG', 'Mg': 'MG', 'mg': 'MG',
    'PA': 'PA', 'Pa': 'PA', 'pa': 'PA',
    'PB': 'PB', 'Pb': 'PB', 'pb': 'PB',
    'PR': 'PR', 'Pr': 'PR', 'pr': 'PR',
    'PE': 'PE', 'Pe': 'PE', 'pe': 'PE',
    'PI': 'PI', 'Pi': 'PI', 'pi': 'PI',
    'RJ': 'RJ', 'Rj': 'RJ', 'rj': 'RJ',
    'RN': 'RN', 'Rn': 'RN', 'rn': 'RN',
    'RS': 'RS', 'Rs': 'RS', 'rs': 'RS',
    'RO': 'RO', 'Ro': 'RO', 'ro': 'RO',
    'RR': 'RR', 'Rr': 'RR', 'rr': 'RR',
    'SC': 'SC', 'Sc': 'SC', 'sc': 'SC',
    'SP': 'SP', 'Sp': 'SP', 'sp': 'SP',
    'SE': 'SE', 'Se': 'SE', 'se': 'SE',
    'TO': 'TO', 'To': 'TO', 'to': 'TO',
}

# Mapeamento de categorias (todas as variações)
CATEGORY_MAP = {
    # Apartamento
    'apartamento': 'Apartamento',
    'APARTAMENTO': 'Apartamento',
    'Apartamento': 'Apartamento',
    'apto': 'Apartamento',
    'apt': 'Apartamento',
    
    # Casa
    'casa': 'Casa',
    'CASA': 'Casa',
    'Casa': 'Casa',
    'residencia': 'Casa',
    'residência': 'Casa',
    'sobrado': 'Casa',
    
    # Terreno
    'terreno': 'Terreno',
    'TERRENO': 'Terreno',
    'Terreno': 'Terreno',
    'lote': 'Terreno',
    'gleba': 'Terreno',
    
    # Comercial
    'comercial': 'Comercial',
    'COMERCIAL': 'Comercial',
    'Comercial': 'Comercial',
    'prédio comercial': 'Comercial',
    'predio comercial': 'Comercial',
    'galpão': 'Comercial',
    'galpao': 'Comercial',
    
    # Rural
    'rural': 'Rural',
    'RURAL': 'Rural',
    'Rural': 'Rural',
    'fazenda': 'Rural',
    'sítio': 'Rural',
    'sitio': 'Rural',
    'chácara': 'Rural',
    'chacara': 'Rural',
    
    # Garagem
    'garagem': 'Garagem',
    'GARAGEM': 'Garagem',
    'Garagem': 'Garagem',
    'vaga': 'Garagem',
    'box': 'Garagem',
    
    # Loja
    'loja': 'Loja',
    'LOJA': 'Loja',
    'Loja': 'Loja',
    
    # Sala Comercial
    'sala comercial': 'Sala Comercial',
    'SALA COMERCIAL': 'Sala Comercial',
    'Sala Comercial': 'Sala Comercial',
    'sala': 'Sala Comercial',
    'conjunto': 'Sala Comercial',
    
    # Área
    'área': 'Área',
    'ÁREA': 'Área',
    'area': 'Área',
    'AREA': 'Área',
    'Área': 'Área',
    'Area': 'Área',
    
    # Outros
    'outro': 'Outro',
    'OUTRO': 'Outro',
    'Outro': 'Outro',
    'outros': 'Outro',
    'OUTROS': 'Outro',
    'Outros': 'Outro',
    'não informado': 'Outro',
    'nao informado': 'Outro',
    '': 'Outro',
}


def normalize_state(state: Optional[str]) -> str:
    """
    Normaliza sigla de estado para UPPERCASE.
    Retorna 'XX' se inválido.
    """
    if not state:
        return 'XX'
    
    state = state.strip()
    
    # Verificar mapeamento direto
    if state in STATE_MAP:
        return STATE_MAP[state]
    
    # Tentar uppercase
    upper = state.upper()[:2]
    if upper in STATE_MAP:
        return STATE_MAP[upper]
    
    return 'XX'


def normalize_category(category: Optional[str]) -> str:
    """
    Normaliza categoria para Title Case padrão.
    Retorna 'Outro' se não reconhecida.
    """
    if not category:
        return 'Outro'
    
    category = category.strip()
    
    # Verificar mapeamento direto
    if category in CATEGORY_MAP:
        return CATEGORY_MAP[category]
    
    # Tentar lowercase
    lower = category.lower()
    if lower in CATEGORY_MAP:
        return CATEGORY_MAP[lower]
    
    # Verificar se contém palavras-chave
    lower = category.lower()
    if 'apartamento' in lower or 'apto' in lower:
        return 'Apartamento'
    if 'casa' in lower or 'sobrado' in lower or 'residencia' in lower:
        return 'Casa'
    if 'terreno' in lower or 'lote' in lower:
        return 'Terreno'
    if 'comercial' in lower or 'galpão' in lower or 'galpao' in lower:
        return 'Comercial'
    if 'rural' in lower or 'fazenda' in lower or 'sítio' in lower or 'chácara' in lower:
        return 'Rural'
    if 'garagem' in lower or 'vaga' in lower:
        return 'Garagem'
    if 'loja' in lower:
        return 'Loja'
    if 'sala' in lower:
        return 'Sala Comercial'
    
    return 'Outro'


def normalize_city(city: Optional[str]) -> str:
    """
    Normaliza nome de cidade:
    - Remove sufixo de estado (ex: "Arapiraca - Al" -> "Arapiraca")
    - Aplica Title Case
    """
    if not city:
        return 'Não informada'
    
    city = city.strip()
    
    # Remover sufixo de estado (ex: " - Al", " - SP", "/SP", " -SP")
    city = re.sub(r'\s*[-/]\s*[A-Za-z]{2}\s*$', '', city)
    
    # Remover estado entre parênteses (ex: "Cidade (SP)")
    city = re.sub(r'\s*\([A-Za-z]{2}\)\s*$', '', city)
    
    # Title Case com exceções
    def title_case(s):
        words = s.split()
        result = []
        lowercase_words = ['de', 'da', 'do', 'das', 'dos', 'e', 'em', 'na', 'no', 'nas', 'nos']
        
        for i, word in enumerate(words):
            if i == 0:
                # Primeira palavra sempre capitalizada
                result.append(word.capitalize())
            elif word.lower() in lowercase_words:
                result.append(word.lower())
            else:
                result.append(word.capitalize())
        
        return ' '.join(result)
    
    return title_case(city)


def normalize_property(prop: dict) -> dict:
    """
    Normaliza todos os campos de uma propriedade.
    USE ESTA FUNÇÃO EM TODOS OS SCRAPERS ANTES DE SALVAR.
    """
    normalized = prop.copy()
    
    # Normalizar estado
    if 'state' in normalized:
        normalized['state'] = normalize_state(normalized['state'])
    
    # Normalizar categoria
    if 'category' in normalized:
        normalized['category'] = normalize_category(normalized['category'])
    
    # Normalizar cidade
    if 'city' in normalized:
        normalized['city'] = normalize_city(normalized['city'])
    
    return normalized


# Teste rápido
if __name__ == "__main__":
    # Testar estados
    test_states = ['Al', 'al', 'AL', 'Sp', 'sp', 'SP', 'Ba', 'XX', None, '']
    print("=== ESTADOS ===")
    for s in test_states:
        print(f"  {repr(s)} -> {normalize_state(s)}")
    
    # Testar categorias
    test_categories = ['APARTAMENTO', 'apartamento', 'Casa', 'TERRENO', 'RURAL', 'OUTRO', '', None]
    print("\n=== CATEGORIAS ===")
    for c in test_categories:
        print(f"  {repr(c)} -> {normalize_category(c)}")
    
    # Testar cidades
    test_cities = ['Arapiraca - Al', 'São Paulo - SP', 'Rio de Janeiro/RJ', 'Belo Horizonte (MG)', 'Salvador']
    print("\n=== CIDADES ===")
    for c in test_cities:
        print(f"  {repr(c)} -> {normalize_city(c)}")
