"""
DataNormalizer - Normalização de dados para consistência.

Problemas resolvidos:
1. Categorias inconsistentes (APARTAMENTO vs apartamento vs Apartamento)
2. Cidades com erros de digitação
3. Estados em formatos diferentes
4. Valores monetários com formatos variados
"""

import re
from typing import Optional, Dict
import unicodedata
import logging

logger = logging.getLogger(__name__)

class DataNormalizer:
    """
    Normalizador de dados para garantir consistência.
    """
    
    # Mapeamento de categorias para padronização
    CATEGORIAS_MAPA = {
        # Apartamento
        'apartamento': 'Apartamento',
        'apto': 'Apartamento',
        'apt': 'Apartamento',
        'ap': 'Apartamento',
        'flat': 'Apartamento',
        'studio': 'Apartamento',
        'kitnet': 'Apartamento',
        'kitchenette': 'Apartamento',
        'loft': 'Apartamento',
        'cobertura': 'Apartamento',
        
        # Casa
        'casa': 'Casa',
        'residencia': 'Casa',
        'residência': 'Casa',
        'sobrado': 'Casa',
        'chalé': 'Casa',
        'chale': 'Casa',
        'bangalô': 'Casa',
        'bangalo': 'Casa',
        'edícula': 'Casa',
        'edicula': 'Casa',
        
        # Terreno
        'terreno': 'Terreno',
        'lote': 'Terreno',
        'gleba': 'Terreno',
        'área': 'Terreno',
        'area': 'Terreno',
        'chácara': 'Terreno',
        'chacara': 'Terreno',
        'sítio': 'Terreno',
        'sitio': 'Terreno',
        'fazenda': 'Terreno',
        
        # Comercial
        'comercial': 'Comercial',
        'sala comercial': 'Comercial',
        'loja': 'Comercial',
        'ponto comercial': 'Comercial',
        'galpão': 'Comercial',
        'galpao': 'Comercial',
        'armazém': 'Comercial',
        'armazem': 'Comercial',
        'barracão': 'Comercial',
        'barracao': 'Comercial',
        'escritório': 'Comercial',
        'escritorio': 'Comercial',
        'prédio comercial': 'Comercial',
        'predio comercial': 'Comercial',
        
        # Outros
        'outros': 'Outros',
        'outro': 'Outros',
        'imóvel': 'Outros',
        'imovel': 'Outros',
        'bem imóvel': 'Outros',
        'bem imovel': 'Outros',
        'vaga': 'Outros',
        'garagem': 'Outros',
        'box': 'Outros',
    }
    
    # Estados brasileiros
    ESTADOS = {
        'acre': 'AC', 'ac': 'AC',
        'alagoas': 'AL', 'al': 'AL',
        'amapá': 'AP', 'amapa': 'AP', 'ap': 'AP',
        'amazonas': 'AM', 'am': 'AM',
        'bahia': 'BA', 'ba': 'BA',
        'ceará': 'CE', 'ceara': 'CE', 'ce': 'CE',
        'distrito federal': 'DF', 'df': 'DF',
        'espírito santo': 'ES', 'espirito santo': 'ES', 'es': 'ES',
        'goiás': 'GO', 'goias': 'GO', 'go': 'GO',
        'maranhão': 'MA', 'maranhao': 'MA', 'ma': 'MA',
        'mato grosso': 'MT', 'mt': 'MT',
        'mato grosso do sul': 'MS', 'ms': 'MS',
        'minas gerais': 'MG', 'mg': 'MG',
        'pará': 'PA', 'para': 'PA', 'pa': 'PA',
        'paraíba': 'PB', 'paraiba': 'PB', 'pb': 'PB',
        'paraná': 'PR', 'parana': 'PR', 'pr': 'PR',
        'pernambuco': 'PE', 'pe': 'PE',
        'piauí': 'PI', 'piaui': 'PI', 'pi': 'PI',
        'rio de janeiro': 'RJ', 'rj': 'RJ',
        'rio grande do norte': 'RN', 'rn': 'RN',
        'rio grande do sul': 'RS', 'rs': 'RS',
        'rondônia': 'RO', 'rondonia': 'RO', 'ro': 'RO',
        'roraima': 'RR', 'rr': 'RR',
        'santa catarina': 'SC', 'sc': 'SC',
        'são paulo': 'SP', 'sao paulo': 'SP', 'sp': 'SP',
        'sergipe': 'SE', 'se': 'SE',
        'tocantins': 'TO', 'to': 'TO',
    }
    
    def normalize_category(self, category: str) -> str:
        """
        Normaliza categoria para uma das 5 categorias padrão.
        
        Returns:
            Uma de: Apartamento, Casa, Terreno, Comercial, Outros
        """
        if not category:
            return "Outros"
        
        # Limpa e normaliza
        clean = self._clean_text(category.lower())
        
        # Procura correspondência
        for key, value in self.CATEGORIAS_MAPA.items():
            if key in clean:
                return value
        
        # Tenta match parcial
        for key, value in self.CATEGORIAS_MAPA.items():
            if any(word in clean for word in key.split()):
                return value
        
        return "Outros"
    
    def normalize_state(self, state: str) -> str:
        """
        Normaliza estado para sigla de 2 letras.
        
        Returns:
            Sigla do estado (ex: "SP", "RJ") ou string vazia
        """
        if not state:
            return ""
        
        clean = self._clean_text(state.lower())
        
        # Procura correspondência
        for key, value in self.ESTADOS.items():
            if key == clean or clean == value.lower():
                return value
        
        # Se já é uma sigla válida, retorna em maiúsculo
        if len(state) == 2 and state.upper() in self.ESTADOS.values():
            return state.upper()
        
        return ""
    
    def normalize_city(self, city: str) -> str:
        """
        Normaliza nome de cidade para Title Case.
        
        Trata casos especiais como "SAO PAULO" → "São Paulo"
        """
        if not city:
            return ""
        
        # Remove espaços extras
        city = ' '.join(city.split())
        
        # Title Case inteligente
        words = city.lower().split()
        result = []
        
        # Palavras que não devem ser capitalizadas (exceto no início)
        lowercase_words = {'de', 'da', 'do', 'das', 'dos', 'e'}
        
        for i, word in enumerate(words):
            if i == 0 or word not in lowercase_words:
                result.append(word.capitalize())
            else:
                result.append(word)
        
        normalized = ' '.join(result)
        
        # Correções especiais
        corrections = {
            'Sao Paulo': 'São Paulo',
            'Brasilia': 'Brasília',
            'Goiania': 'Goiânia',
            'Curitiba': 'Curitiba',
            'Belem': 'Belém',
            'Sao Luis': 'São Luís',
            'Sao Jose': 'São José',
            'Sao Bernardo': 'São Bernardo',
            'Sao Caetano': 'São Caetano',
            'Sao Vicente': 'São Vicente',
            'Ribeirao Preto': 'Ribeirão Preto',
            'Uberlandia': 'Uberlândia',
            'Londrina': 'Londrina',
            'Niteroi': 'Niterói',
            'Florianopolis': 'Florianópolis',
        }
        
        for wrong, correct in corrections.items():
            if wrong in normalized:
                normalized = normalized.replace(wrong, correct)
        
        return normalized
    
    def normalize_money(self, value: str) -> Optional[float]:
        """
        Normaliza valor monetário para float.
        
        Formatos suportados:
        - "R$ 100.000,00"
        - "100000.00"
        - "100.000"
        - "R&#36; 100.000,00" (HTML entity)
        """
        if not value:
            return None
        
        # Converte HTML entities
        import html
        value = html.unescape(str(value))
        
        # Remove símbolos de moeda
        value = re.sub(r'[R$\s]', '', value)
        
        # Remove pontos de milhar e converte vírgula para ponto
        # Detecta formato brasileiro (1.000,00) vs americano (1,000.00)
        if ',' in value and '.' in value:
            # Formato brasileiro: 1.000.000,00
            value = value.replace('.', '').replace(',', '.')
        elif ',' in value:
            # Apenas vírgula: assume formato brasileiro
            value = value.replace(',', '.')
        
        try:
            return float(value)
        except ValueError:
            return None
    
    def normalize_area(self, area: str) -> Optional[float]:
        """
        Normaliza área para float em m².
        
        Formatos suportados:
        - "100 m²"
        - "100m2"
        - "100 metros quadrados"
        - "100,50 m²"
        """
        if not area:
            return None
        
        # Remove texto e mantém números
        clean = re.sub(r'[^\d,.]', '', str(area))
        
        # Converte vírgula para ponto
        clean = clean.replace(',', '.')
        
        try:
            return float(clean)
        except ValueError:
            return None
    
    def normalize_title(self, title: str) -> str:
        """
        Normaliza título para Title Case e remove lixo.
        """
        if not title:
            return ""
        
        # Remove padrões de lixo comuns
        junk_patterns = [
            r'navegue pelos lotes',
            r'clique para ver',
            r'ver detalhes',
            r'saiba mais',
            r'<[^>]+>',  # Tags HTML
        ]
        
        for pattern in junk_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Remove espaços extras
        title = ' '.join(title.split())
        
        # Title Case
        return title.title() if title else ""
    
    def _clean_text(self, text: str) -> str:
        """Remove acentos e caracteres especiais."""
        # Remove acentos
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        
        # Remove caracteres especiais
        text = re.sub(r'[^\w\s]', '', text)
        
        return text.strip()


# Instância global para uso conveniente
_normalizer = DataNormalizer()

def normalize_category(category: str) -> str:
    """Função de conveniência."""
    return _normalizer.normalize_category(category)

def normalize_state(state: str) -> str:
    """Função de conveniência."""
    return _normalizer.normalize_state(state)

def normalize_city(city: str) -> str:
    """Função de conveniência."""
    return _normalizer.normalize_city(city)

def normalize_money(value: str) -> Optional[float]:
    """Função de conveniência."""
    return _normalizer.normalize_money(value)

def normalize_area(area: str) -> Optional[float]:
    """Função de conveniência."""
    return _normalizer.normalize_area(area)

def normalize_title(title: str) -> str:
    """Função de conveniência."""
    return _normalizer.normalize_title(title)

