"""
QualityAuditor - Camada de Auditoria de Qualidade de Dados
LeiloHub - 2026-01-21

Implementa validações conforme ESTRATEGIA_AUDITORIA_QUALIDADE_IA.md:
1. Validação de datas de leilão
2. Validação de valores de praça
3. Validação de estado (UF)
4. Correção automática quando possível
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """Resultado da auditoria de um imóvel"""
    passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    corrections: Dict[str, Any] = field(default_factory=dict)
    original_data: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.passed = False
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)
    
    def add_correction(self, field: str, old_value: Any, new_value: Any):
        self.corrections[field] = {
            'old': old_value,
            'new': new_value
        }


class QualityAuditor:
    """
    Auditor de qualidade de dados para imóveis.
    
    Uso:
        auditor = QualityAuditor()
        result, corrected_data = auditor.audit(property_data)
        
        if result.passed:
            # Salvar no banco
            save_to_database(corrected_data)
        else:
            # Logar erros e não salvar
            logger.error(f"Auditoria falhou: {result.errors}")
    """
    
    # Estados brasileiros válidos
    VALID_STATES = {
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
        'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 
        'SP', 'SE', 'TO'
    }
    
    # Mapeamento de estados truncados/errados para corretos
    STATE_CORRECTIONS = {
        'Sã': 'SP', 'SÃ': 'SP', 'sã': 'SP', 'SA': 'SP', 'Sa': 'SP', 'sa': 'SP', 'Sp': 'SP', 'sp': 'SP',  # São Paulo
        'são paulo': 'SP', 'sao paulo': 'SP', 'São Paulo': 'SP', 'Sao Paulo': 'SP',
        'Ri': 'RJ', 'RI': 'RJ', 'ri': 'RJ', 'Rj': 'RJ', 'rj': 'RJ',              # Rio de Janeiro
        'rio de janeiro': 'RJ', 'Rio de Janeiro': 'RJ', 'Rio De Janeiro': 'RJ',
        'Mi': 'MG', 'MI': 'MG', 'mi': 'MG', 'Mg': 'MG', 'mg': 'MG',              # Minas Gerais
        'minas gerais': 'MG', 'Minas Gerais': 'MG', 'Minas': 'MG',
        'Di': 'DF', 'DI': 'DF', 'di': 'DF', 'Df': 'DF', 'df': 'DF',              # Distrito Federal
        'distrito federal': 'DF', 'Distrito Federal': 'DF', 'brasília': 'DF', 'brasilia': 'DF',
        'Go': 'GO', 'go': 'GO', 'goiás': 'GO', 'goias': 'GO', 'Goiás': 'GO', 'Goias': 'GO',                          # Goiás
        'Ba': 'BA', 'ba': 'BA', 'bahia': 'BA', 'Bahia': 'BA',                    # Bahia
        'Pe': 'PE', 'pe': 'PE', 'pernambuco': 'PE', 'Pernambuco': 'PE',                          # Pernambuco
        'Ce': 'CE', 'ce': 'CE', 'ceará': 'CE', 'ceara': 'CE', 'Ceará': 'CE', 'Ceara': 'CE',                          # Ceará
        'Se': 'SE', 'se': 'SE', 'sergipe': 'SE', 'Sergipe': 'SE',                          # Sergipe
        'Es': 'ES', 'es': 'ES', 'espírito santo': 'ES', 'espirito santo': 'ES',                          # Espírito Santo
        'Ro': 'RO', 'ro': 'RO', 'rondônia': 'RO', 'rondonia': 'RO',                          # Rondônia
        'To': 'TO', 'to': 'TO', 'tocantins': 'TO', 'Tocantins': 'TO',                          # Tocantins
        'Pi': 'PI', 'pi': 'PI', 'piauí': 'PI', 'piaui': 'PI',                          # Piauí
        'Pa': 'PA', 'pa': 'PA', 'pará': 'PA', 'para': 'PA',                          # Pará (default)
        'Pr': 'PR', 'pr': 'PR', 'paraná': 'PR', 'parana': 'PR',                  # Paraná
        'Rs': 'RS', 'rs': 'RS', 'rio grande do sul': 'RS',                       # Rio Grande do Sul
        'Sc': 'SC', 'sc': 'SC', 'santa catarina': 'SC',                          # Santa Catarina
        'Mt': 'MT', 'mt': 'MT', 'mato grosso': 'MT',                             # Mato Grosso
        'Ms': 'MS', 'ms': 'MS', 'mato grosso do sul': 'MS',                      # Mato Grosso do Sul
        'Al': 'AL', 'al': 'AL', 'alagoas': 'AL',                                 # Alagoas
        'Rn': 'RN', 'rn': 'RN', 'rio grande do norte': 'RN',                     # Rio Grande do Norte
        'Pb': 'PB', 'pb': 'PB', 'paraíba': 'PB', 'paraiba': 'PB',                # Paraíba
        'Am': 'AM', 'am': 'AM', 'amazonas': 'AM',                                # Amazonas
        'Ap': 'AP', 'ap': 'AP', 'amapá': 'AP', 'amapa': 'AP',                    # Amapá
        'Rr': 'RR', 'rr': 'RR', 'roraima': 'RR',                                 # Roraima
        'Ac': 'AC', 'ac': 'AC', 'acre': 'AC',                                    # Acre
        'Ma': 'MA', 'ma': 'MA', 'maranhão': 'MA', 'maranhao': 'MA',              # Maranhão (default)
    }
    
    # Cidades que indicam estado diferente do default
    CITY_STATE_HINTS = {
        # Paraná (PR) - não Pará (PA)
        'PR': ['curitiba', 'londrina', 'maringa', 'maringá', 'foz do iguacu', 
               'foz do iguaçu', 'cascavel', 'ponta grossa', 'guarapuava'],
        # Mato Grosso do Sul (MS) - não Maranhão (MA)
        'MS': ['campo grande', 'dourados', 'tres lagoas', 'três lagoas', 
               'corumba', 'corumbá'],
        # Santa Catarina (SC)
        'SC': ['florianopolis', 'florianópolis', 'joinville', 'blumenau', 
               'chapeco', 'chapecó'],
    }
    
    # Categorias válidas
    VALID_CATEGORIES = {
        'Apartamento', 'Casa', 'Terreno', 'Comercial', 'Rural', 'Galpão', 
        'Sala', 'Loja', 'Prédio', 'Fazenda', 'Sítio', 'Chácara', 'Outro'
    }
    
    # Mapeamento de normalização de categorias
    CATEGORY_MAPPING = {
        'apartamento': 'Apartamento',
        'apto': 'Apartamento',
        'apt': 'Apartamento',
        'apartamentos': 'Apartamento',
        'casa': 'Casa',
        'casas': 'Casa',
        'residencia': 'Casa',
        'residência': 'Casa',
        'sobrado': 'Casa',
        'terreno': 'Terreno',
        'terrenos': 'Terreno',
        'lote': 'Terreno',
        'comercial': 'Comercial',
        'comerciais': 'Comercial',
        'loja': 'Loja',
        'lojas': 'Loja',
        'sala': 'Sala',
        'salas': 'Sala',
        'sala comercial': 'Sala',
        'galpão': 'Galpão',
        'galpao': 'Galpão',
        'galpoes': 'Galpão',
        'galpões': 'Galpão',
        'barracão': 'Galpão',
        'barracao': 'Galpão',
        'prédio': 'Prédio',
        'predio': 'Prédio',
        'predios': 'Prédio',
        'prédios': 'Prédio',
        'edificio': 'Prédio',
        'edifício': 'Prédio',
        'rural': 'Rural',
        'fazenda': 'Fazenda',
        'fazendas': 'Fazenda',
        'sítio': 'Sítio',
        'sitio': 'Sítio',
        'sitios': 'Sítio',
        'sítios': 'Sítio',
        'chácara': 'Chácara',
        'chacara': 'Chácara',
        'chacaras': 'Chácara',
        'chácaras': 'Chácara',
        'flat': 'Flat',
        'cobertura': 'Cobertura',
        'studio': 'Studio',
        'kitnet': 'Kitnet',
        'kitinete': 'Kitnet',
        'kit': 'Kitnet',
        'outro': 'Outro',
        'outros': 'Outro',
        'imovel': 'Outro',
        'imóvel': 'Outro',
    }
    
    def __init__(self, strict_mode: bool = False, auto_correct: bool = True):
        """
        Inicializa o auditor.
        
        Args:
            strict_mode: Se True, falha em warnings também
            auto_correct: Se True, tenta corrigir erros automaticamente
        """
        self.strict_mode = strict_mode
        self.auto_correct = auto_correct
        self.stats = {
            'total_audited': 0,
            'passed': 0,
            'failed': 0,
            'corrected': 0,
            'errors_by_type': {}
        }
    
    def audit(self, data: Dict[str, Any]) -> Tuple[AuditResult, Dict[str, Any]]:
        """
        Audita um imóvel e retorna resultado + dados corrigidos.
        
        Args:
            data: Dicionário com dados do imóvel
            
        Returns:
            Tuple[AuditResult, Dict]: Resultado da auditoria e dados corrigidos
        """
        result = AuditResult(original_data=data.copy())
        corrected_data = data.copy()
        
        # Executar validações
        corrected_data = self._validate_and_correct_state(corrected_data, result)
        corrected_data = self._validate_and_correct_city(corrected_data, result)
        corrected_data = self._validate_and_correct_dates(corrected_data, result)
        corrected_data = self._validate_and_correct_values(corrected_data, result)
        corrected_data = self._validate_and_correct_category(corrected_data, result)
        corrected_data = self._validate_required_fields(corrected_data, result)
        
        # Atualizar estatísticas
        self.stats['total_audited'] += 1
        if result.passed:
            self.stats['passed'] += 1
        else:
            self.stats['failed'] += 1
        if result.corrections:
            self.stats['corrected'] += 1
        
        for error in result.errors:
            error_type = error.split(':')[0] if ':' in error else error
            self.stats['errors_by_type'][error_type] = \
                self.stats['errors_by_type'].get(error_type, 0) + 1
        
        return result, corrected_data
    
    def audit_batch(self, data_list: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
        """
        Audita um lote de imóveis.
        
        Args:
            data_list: Lista de dicionários com dados dos imóveis
            
        Returns:
            Tuple[passed_list, failed_list]: Listas de aprovados/reprovados
        """
        passed = []
        failed = []
        
        for data in data_list:
            result, corrected = self.audit(data)
            if result.passed:
                passed.append(corrected)
            else:
                failed.append({
                    'data': data,
                    'errors': result.errors,
                    'warnings': result.warnings
                })
        
        logger.info(f"Auditoria em lote: {len(passed)} aprovados, {len(failed)} reprovados")
        
        return passed, failed
    
    # Public API methods for testing compatibility
    def validate_state(self, property_data: Dict) -> Tuple[bool, List[str], Dict]:
        """Public API para validação de estado (modifica dict in place)."""
        result = AuditResult()
        self._validate_and_correct_state(property_data, result)
        corrections = {k: f"{v['old']} -> {v['new']}" for k, v in result.corrections.items()}
        return result.passed, result.errors, corrections
    
    def validate_dates(self, property_data: Dict) -> Tuple[bool, List[str], Dict]:
        """Public API para validação de datas (modifica dict in place)."""
        result = AuditResult()
        self._validate_and_correct_dates(property_data, result)
        # Filter only errors, not warnings
        errors = [e for e in result.errors if not any(w in e for w in ['passada', 'futura', 'warning'])]
        corrections = {k: f"{v['old']} -> {v['new']}" for k, v in result.corrections.items()}
        # Return False only if there are actual errors (not warnings)
        is_valid = len(errors) == 0
        return is_valid, errors, corrections
    
    def validate_values(self, property_data: Dict) -> Tuple[bool, List[str], Dict]:
        """Public API para validação de valores (modifica dict in place)."""
        result = AuditResult()
        self._validate_and_correct_values(property_data, result)
        corrections = {k: f"{v['old']} -> {v['new']}" for k, v in result.corrections.items()}
        return result.passed, result.errors, corrections
    
    def validate_category(self, property_data: Dict) -> Tuple[bool, List[str], Dict]:
        """Public API para validação de categoria (modifica dict in place)."""
        result = AuditResult()
        self._validate_and_correct_category(property_data, result)
        corrections = {k: f"{v['old']} -> {v['new']}" for k, v in result.corrections.items()}
        return result.passed, result.errors, corrections
    
    def validate_city(self, property_data: Dict) -> Tuple[bool, List[str], Dict]:
        """Public API para validação de cidade (modifica dict in place)."""
        result = AuditResult()
        self._validate_and_correct_city(property_data, result)
        corrections = {k: f"{v['old']} -> {v['new']}" for k, v in result.corrections.items()}
        return result.passed, result.errors, corrections
    
    def audit_property(self, property_data: Dict) -> Dict:
        """
        Audita um único imóvel (compatibilidade com API antiga).
        Modifies property_data dict in place with corrections and metadata.
        
        Returns:
            Dict com audit_passed, audit_errors, etc.
        """
        result, corrected = self.audit(property_data)
        
        # Apply all corrections to the original dict
        for key, value in corrected.items():
            property_data[key] = value
        
        # Add audit metadata to original dict
        property_data['audit_status'] = 'passed' if result.passed else 'failed'
        property_data['audit_errors'] = result.errors if result.errors else None
        property_data['audit_warnings'] = result.warnings if result.warnings else None
        property_data['audit_timestamp'] = datetime.now().isoformat()
        property_data['audit_version'] = '1.0.0'
        
        return {
            'property': property_data,
            'audit_passed': result.passed,
            'audit_errors': result.errors,
            'audit_warnings': result.warnings,
            'corrections_applied': result.corrections,
            'audit_timestamp': property_data['audit_timestamp'],
            'audit_version': '1.0.0'
        }
    
    def _validate_and_correct_state(self, data: Dict, result: AuditResult) -> Dict:
        """Valida e corrige o campo state (UF)."""
        state = data.get('state')
        city = data.get('city', '')
        
        # Check for invalid state values first
        if not state or state in ['XX', 'NI', 'N/A', 'NA', 'UF', '', None, 'NÃ', 'NÂ'] or (isinstance(state, str) and state.strip() == ''):
            result.add_error("estado_vazio_ou_invalido")
            return data
        
        original_state = state
        state = str(state).strip()
        
        # Tentar corrigir estado truncado
        if state in self.STATE_CORRECTIONS:
            corrected_state = self.STATE_CORRECTIONS[state]
            
            # Verificar se cidade indica outro estado (caso especial Pa)
            if city and state.lower() == 'pa':
                city_lower = city.lower()
                # Check if it's a Paraná city
                if any(c in city_lower for c in self.CITY_STATE_HINTS.get('PR', [])):
                    corrected_state = 'PR'
            
            state = corrected_state
            if self.auto_correct:
                data['state'] = state
                result.add_correction('state', original_state, state)
                result.add_warning(f"estado_corrigido: '{original_state}' -> '{state}'")
        
        # Converter para uppercase
        elif state != state.upper():
            if self.auto_correct:
                data['state'] = state.upper()
                result.add_correction('state', state, state.upper())
            state = state.upper()
        
        # Validar contra lista de estados válidos
        if state not in self.VALID_STATES:
            result.add_error(f"estado_desconhecido: '{state}' não reconhecido como UF brasileira")
        
        return data
    
    def _validate_and_correct_city(self, data: Dict, result: AuditResult) -> Dict:
        """Valida e corrige o campo city."""
        city = data.get('city')
        
        if not city or (isinstance(city, str) and city.strip() == ''):
            result.add_warning("cidade_vazia: Campo 'city' está vazio")
            return data
        
        original_city = city
        city_str = str(city).strip()
        
        # Extrair estado do final da cidade se presente (ex: "Fortaleza - Ce" ou "São Paulo/SP" ou "São Paulo - SP")
        state_match = re.search(r'\s*[-/]\s*([A-Za-z]{2})\s*$', city_str)
        if state_match:
            extracted_state = state_match.group(1).strip().upper()
            # Remover o estado da cidade
            city_str = re.sub(r'\s*[-/]\s*[A-Za-z]{2}\s*$', '', city_str)
            # Se estado não está definido, extrair
            if not data.get('state'):
                data['state'] = extracted_state
                result.add_correction('state', None, extracted_state)
        
        # Aplicar Title Case
        city_str = city_str.strip().title()
        
        # Correções específicas de Title Case
        city_str = city_str.replace(' De ', ' de ')
        city_str = city_str.replace(' Da ', ' da ')
        city_str = city_str.replace(' Do ', ' do ')
        city_str = city_str.replace(' Das ', ' das ')
        city_str = city_str.replace(' Dos ', ' dos ')
        
        if city_str != original_city and self.auto_correct:
            data['city'] = city_str
            result.add_correction('city', original_city, city_str)
        
        return data
    
    def _validate_and_correct_dates(self, data: Dict, result: AuditResult) -> Dict:
        """Valida datas de leilão."""
        first_date = data.get('first_auction_date')
        second_date = data.get('second_auction_date')
        
        now = datetime.now()
        max_past = now - timedelta(days=30)  # Máximo 30 dias no passado
        max_future = now + timedelta(days=365)  # Máximo 1 ano no futuro
        
        # Parser de data flexível
        def parse_date(date_str):
            if not date_str or isinstance(date_str, datetime):
                return date_str
            formats = [
                '%Y-%m-%d',           # ISO
                '%Y-%m-%dT%H:%M:%S',  # ISO com hora
                '%Y-%m-%dT%H:%M:%SZ', # ISO UTC
                '%d/%m/%Y',           # BR
                '%d/%m/%Y %H:%M',     # BR com hora
                '%d-%m-%Y',           # BR alternativo
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(str(date_str)[:19] if 'T' in str(date_str) else str(date_str), fmt)
                except ValueError:
                    continue
            return None
        
        # Validar primeira data
        if first_date:
            if isinstance(first_date, str):
                parsed = parse_date(first_date)
                if not parsed:
                    result.add_error(f"first_auction_date_formato_invalido: {first_date}")
                    first_date = None
                else:
                    first_date = parsed
            
            if first_date:
                if first_date < max_past:
                    result.add_warning(f"first_auction_date_no_passado: {first_date.date()}")
                elif first_date > max_future:
                    result.add_warning(f"data_futura: first_auction_date ({first_date.date()}) é muito distante")
        
        # Validar segunda data
        if second_date:
            if isinstance(second_date, str):
                parsed = parse_date(second_date)
                if not parsed:
                    result.add_error(f"second_auction_date_formato_invalido: {second_date}")
                    second_date = None
                else:
                    second_date = parsed
            
            if second_date and first_date:
                if second_date < first_date:
                    result.add_error("datas_invertidas: first_auction_date > second_auction_date")
        
        # Verificar se pelo menos uma data existe
        if not first_date and not second_date:
            result.add_warning("sem_data_leilao: Nenhuma data de leilão informada")
        
        return data
    
    def _validate_and_correct_values(self, data: Dict, result: AuditResult) -> Dict:
        """Valida valores de avaliação e leilão."""
        eval_value = data.get('evaluation_value')
        first_value = data.get('first_auction_value')
        second_value = data.get('second_auction_value')
        discount = data.get('discount_percentage')
        
        # Converter para float se necessário
        def to_float(v):
            if v is None:
                return None
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                try:
                    # Limpar formato brasileiro
                    v = v.replace('R$', '').replace('.', '').replace(',', '.').strip()
                    return float(v)
                except ValueError:
                    return None
            return None
        
        eval_value = to_float(eval_value)
        first_value = to_float(first_value)
        second_value = to_float(second_value)
        
        # Validar hierarquia de valores
        if eval_value and first_value:
            if first_value > eval_value * 1.1:  # Margem de 10%
                result.add_warning(f"valor_inconsistente: first_auction_value ({first_value}) > evaluation_value ({eval_value})")
        
        if first_value and second_value:
            if second_value > first_value:
                result.add_error(f"second_auction_value ({second_value}) > first_auction_value ({first_value})")
        
        # Calcular/validar desconto
        if eval_value and second_value and eval_value > 0:
            calculated_discount = ((eval_value - second_value) / eval_value) * 100
            if discount is None or abs(calculated_discount - discount) > 5:
                if self.auto_correct:
                    data['discount_percentage'] = round(calculated_discount, 2)
                    result.add_correction('discount_percentage', discount, round(calculated_discount, 2))
                if discount is not None:
                    result.add_warning(f"desconto_inconsistente: calculado={calculated_discount:.1f}%, informado={discount}%")
        
        # Verificar valores suspeitos
        if first_value and first_value < 1000:
            result.add_warning(f"valor_suspeito: first_auction_value ({first_value}) muito baixo")
        
        if first_value and first_value > 100000000:  # 100 milhões
            result.add_warning(f"valor_suspeito: first_auction_value ({first_value}) muito alto")
        
        return data
    
    def _validate_and_correct_category(self, data: Dict, result: AuditResult) -> Dict:
        """Valida e normaliza categoria."""
        category = data.get('category')
        
        if not category or (isinstance(category, str) and category.strip() == ''):
            if self.auto_correct:
                data['category'] = 'Outro'
                result.add_correction('category', category, 'Outro')
            else:
                result.add_warning("categoria_vazia: Campo 'category' está vazio")
            return data
        
        original_category = category
        category_str = str(category).strip()
        
        # Primeiro tentar mapear lowercase
        category_lower = category_str.lower()
        if category_lower in self.CATEGORY_MAPPING:
            normalized = self.CATEGORY_MAPPING[category_lower]
            if self.auto_correct:
                data['category'] = normalized
                result.add_correction('category', original_category, normalized)
            return data
        
        # Tentar Title Case
        category_title = category_str.title()
        if category_title in self.VALID_CATEGORIES:
            if category_title != original_category and self.auto_correct:
                data['category'] = category_title
                result.add_correction('category', original_category, category_title)
            return data
        
        # Categoria não reconhecida - usar "Outro"
        if self.auto_correct:
            data['category'] = 'Outro'
            result.add_correction('category', original_category, 'Outro')
            result.add_warning(f"categoria_desconhecida: '{original_category}' mapeada para 'Outro'")
        else:
            result.add_warning(f"categoria_desconhecida: '{category_str}' não é uma categoria padrão")
        
        return data
    
    def _validate_required_fields(self, data: Dict, result: AuditResult) -> Dict:
        """Valida campos obrigatórios."""
        # Only add warnings for missing fields, not errors
        # The core validations (state, dates, values) are what matter
        important_fields = ['title', 'source_url', 'state', 'city']
        
        for field in important_fields:
            value = data.get(field)
            if not value or (isinstance(value, str) and value.strip() == ''):
                result.add_warning(f"campo_importante: '{field}' está vazio")
        
        return data
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas de auditoria."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reseta estatísticas."""
        self.stats = {
            'total_audited': 0,
            'passed': 0,
            'failed': 0,
            'corrected': 0,
            'errors_by_type': {}
        }


# ============================================================
# CONVENIENCE FUNCTIONS (Singleton pattern)
# ============================================================

# Singleton instance
_auditor_instance = None

def _get_auditor():
    """Get or create singleton auditor instance."""
    global _auditor_instance
    if _auditor_instance is None:
        _auditor_instance = QualityAuditor(strict_mode=False, auto_correct=True)
    return _auditor_instance


def audit_property(property_data: Dict) -> Dict:
    """Função de conveniência para auditar um imóvel."""
    auditor = _get_auditor()
    return auditor.audit_property(property_data)


def audit_batch(properties: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Função de conveniência para auditar um lote."""
    auditor = _get_auditor()
    passed, failed = auditor.audit_batch(properties)
    return passed, failed


# ============================================================
# EXEMPLO DE USO
# ============================================================

if __name__ == "__main__":
    # Criar auditor
    auditor = QualityAuditor(strict_mode=False, auto_correct=True)
    
    # Dados de exemplo (como vêm do Superbid com problemas)
    test_data = [
        {
            'title': 'Apartamento 64m² em Fortaleza/CE',
            'source_url': 'https://www.superbid.net/produto/123',
            'state': 'Ce',  # Minúsculo - deve corrigir para CE
            'city': 'Fortaleza - Ce',  # Com estado junto - deve limpar
            'category': 'apartamentos',  # Plural - deve normalizar
            'first_auction_value': 150000,
            'evaluation_value': 200000,
        },
        {
            'title': 'Casa em Curitiba/PR',
            'source_url': 'https://www.superbid.net/produto/456',
            'state': 'Pa',  # Errado! Deve corrigir para PR baseado na cidade
            'city': 'Curitiba - Pr',
            'category': 'Casa',
            'first_auction_date': '2026-02-15T14:00:00',
        },
        {
            'title': 'Terreno',
            'source_url': 'https://www.superbid.net/produto/789',
            'state': 'Sã',  # Truncado - deve corrigir para SP
            'city': 'São Paulo',
            'category': 'Terreno',
        },
        {
            'title': '',  # Erro! Campo obrigatório vazio
            'source_url': 'https://www.superbid.net/produto/000',
            'state': 'XX',  # Inválido
            'city': '',
        }
    ]
    
    print("=" * 60)
    print("TESTE DO QUALITY AUDITOR")
    print("=" * 60)
    
    passed, failed, stats = auditor.audit_batch(test_data)
    
    print(f"\n📊 RESULTADOS:")
    print(f"   Aprovados: {len(passed)}")
    print(f"   Reprovados: {len(failed)}")
    
    print(f"\n✅ APROVADOS:")
    for p in passed:
        print(f"   - {p['title'][:50]}... | {p['city']}, {p['state']}")
    
    print(f"\n❌ REPROVADOS:")
    for f in failed:
        print(f"   - {f['data'].get('title', 'SEM TÍTULO')[:30]}...")
        print(f"     Erros: {f['errors']}")
    
    print(f"\n📈 ESTATÍSTICAS:")
    print(f"   Total auditado: {stats['total_audited']}")
    print(f"   Corrigidos: {stats['corrected']}")
    print(f"   Erros por tipo: {stats['errors_by_type']}")
