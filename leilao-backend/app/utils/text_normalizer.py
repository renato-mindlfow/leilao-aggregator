"""
Funções para normalização de texto (cidades, estados, etc.)
"""

import re
import unicodedata

# Exceções que devem manter formatação específica
CITY_EXCEPTIONS = {
    "SAO PAULO": "São Paulo",
    "RIO DE JANEIRO": "Rio de Janeiro",
    "BELO HORIZONTE": "Belo Horizonte",
    "PORTO ALEGRE": "Porto Alegre",
    "SAO JOSE DOS CAMPOS": "São José dos Campos",
    "SAO BERNARDO DO CAMPO": "São Bernardo do Campo",
    "SANTO ANDRE": "Santo André",
    "SAO CAETANO DO SUL": "São Caetano do Sul",
    "RIBEIRAO PRETO": "Ribeirão Preto",
    "UBERLANDIA": "Uberlândia",
    "CONTAGEM": "Contagem",
    "JUIZ DE FORA": "Juiz de Fora",
    "JOINVILLE": "Joinville",
    "FLORIANOPOLIS": "Florianópolis",
    "CURITIBA": "Curitiba",
    "GOIANIA": "Goiânia",
    "BRASILIA": "Brasília",
    "SALVADOR": "Salvador",
    "FORTALEZA": "Fortaleza",
    "RECIFE": "Recife",
    "MANAUS": "Manaus",
    "BELEM": "Belém",
    "GUARULHOS": "Guarulhos",
    "CAMPINAS": "Campinas",
    "OSASCO": "Osasco",
    "NITEROI": "Niterói",
    "MACEIO": "Maceió",
    "NATAL": "Natal",
    "TERESINA": "Teresina",
    "CAMPO GRANDE": "Campo Grande",
    "JOAO PESSOA": "João Pessoa",
    "CUIABA": "Cuiabá",
    "ARACAJU": "Aracaju",
    "VITORIA": "Vitória",
    "SAO LUIS": "São Luís",
    "PORTO VELHO": "Porto Velho",
    "MACAPA": "Macapá",
    "BOA VISTA": "Boa Vista",
    "RIO BRANCO": "Rio Branco",
    "PALMAS": "Palmas",
}

# Palavras que devem ficar em minúscula (exceto no início)
LOWERCASE_WORDS = ["de", "da", "do", "das", "dos", "e", "em", "na", "no", "nas", "nos"]


def normalize_city_name(city: str | None) -> str | None:
    """
    Normaliza o nome de uma cidade para Title Case consistente.
    
    Args:
        city: Nome da cidade (pode estar em MAIÚSCULAS ou minúsculas)
        
    Returns:
        Nome normalizado ou None se vazio
    """
    if not city:
        return None
    
    # Remover espaços extras
    city = " ".join(city.strip().split())
    
    # Verificar exceções primeiro (comparação case-insensitive)
    city_upper = city.upper()
    if city_upper in CITY_EXCEPTIONS:
        return CITY_EXCEPTIONS[city_upper]
    
    # Aplicar Title Case inteligente
    words = city.split()
    result = []
    
    for i, word in enumerate(words):
        word_lower = word.lower()
        
        # Primeira palavra sempre capitalizada
        if i == 0:
            result.append(word.capitalize())
        # Palavras de ligação em minúscula
        elif word_lower in LOWERCASE_WORDS:
            result.append(word_lower)
        # Demais palavras capitalizadas
        else:
            result.append(word.capitalize())
    
    return " ".join(result)


def normalize_neighborhood(neighborhood: str | None) -> str | None:
    """
    Normaliza o nome de um bairro.
    
    Args:
        neighborhood: Nome do bairro
        
    Returns:
        Nome normalizado ou None se vazio
    """
    if not neighborhood:
        return None
    
    # Remover espaços extras
    neighborhood = " ".join(neighborhood.strip().split())
    
    # Aplicar Title Case
    words = neighborhood.split()
    result = []
    
    for i, word in enumerate(words):
        word_lower = word.lower()
        
        if i == 0:
            result.append(word.capitalize())
        elif word_lower in LOWERCASE_WORDS:
            result.append(word_lower)
        else:
            result.append(word.capitalize())
    
    return " ".join(result)


def normalize_address(address: str | None) -> str | None:
    """
    Normaliza um endereço.
    
    Args:
        address: Endereço completo
        
    Returns:
        Endereço normalizado ou None se vazio
    """
    if not address:
        return None
    
    # Remover espaços extras
    address = " ".join(address.strip().split())
    
    # Title Case básico
    return address.title()

