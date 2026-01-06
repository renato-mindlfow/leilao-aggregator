"""
Função de normalização reutilizável para dados de propriedades.
Aplicar em TODOS os lugares onde salvamos dados.
"""


def normalize_property_data(prop: dict) -> dict:
    """
    Normaliza dados de propriedade antes de salvar no banco.
    
    Aplica:
    - Title Case para categoria
    - Title Case para cidade
    - Uppercase para estado (máximo 2 caracteres)
    
    Args:
        prop: Dicionário com dados da propriedade
        
    Returns:
        Dicionário normalizado (modifica o original)
    """
    # Title Case para categoria
    if prop.get("category"):
        prop["category"] = prop["category"].strip().title()
    
    # Title Case para cidade
    if prop.get("city"):
        prop["city"] = prop["city"].strip().title()
    
    # Uppercase para estado (máximo 2 caracteres)
    if prop.get("state"):
        prop["state"] = prop["state"].strip().upper()[:2]
    
    return prop

