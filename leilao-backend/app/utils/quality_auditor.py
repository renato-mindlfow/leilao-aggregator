"""
Auditor de Qualidade de Dados
Valida e filtra dados de imóveis antes do salvamento no banco
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Estados brasileiros válidos
VALID_STATES = {
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
    'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
    'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
}

# Estados inválidos que devem ser rejeitados
INVALID_STATES = {'XX', 'NA', 'N/A', '', None, 'NI', 'ND'}


@dataclass
class AuditResult:
    """Resultado da auditoria de um imóvel."""
    passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    corrections: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.passed = False
        
    def add_warning(self, warning: str):
        self.warnings.append(warning)
        
    def add_correction(self, field: str, old_value: Any, new_value: Any):
        self.corrections[field] = {"old": old_value, "new": new_value}


class QualityAuditor:
    """
    Auditor de qualidade que valida dados de imóveis.
    
    Regras implementadas:
    1. Validação de datas (cronologia e formato)
    2. Validação de valores (regra de desconto)
    3. Validação de estado (UF válida)
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, strict_mode: bool = False):
        """
        Args:
            strict_mode: Se True, rejeita dados com warnings também.
        """
        self.strict_mode = strict_mode
        self.stats = {
            "total_audited": 0,
            "passed": 0,
            "failed": 0,
            "corrected": 0
        }
    
    def audit(self, property_data: Dict) -> Tuple[bool, Dict, AuditResult]:
        """
        Audita um imóvel e retorna dados corrigidos se possível.
        
        Args:
            property_data: Dicionário com dados do imóvel
            
        Returns:
            Tuple[passed, corrected_data, audit_result]
        """
        self.stats["total_audited"] += 1
        result = AuditResult()
        corrected_data = property_data.copy()
        
        # 1. Validar Estado
        corrected_data, state_result = self._validate_state(corrected_data)
        result.errors.extend(state_result.errors)
        result.warnings.extend(state_result.warnings)
        result.corrections.update(state_result.corrections)
        
        # 2. Validar Datas
        corrected_data, date_result = self._validate_dates(corrected_data)
        result.errors.extend(date_result.errors)
        result.warnings.extend(date_result.warnings)
        result.corrections.update(date_result.corrections)
        
        # 3. Validar Valores
        corrected_data, value_result = self._validate_values(corrected_data)
        result.errors.extend(value_result.errors)
        result.warnings.extend(value_result.warnings)
        result.corrections.update(value_result.corrections)
        
        # Determinar resultado final
        if result.errors:
            result.passed = False
            self.stats["failed"] += 1
        else:
            result.passed = True
            self.stats["passed"] += 1
            if result.corrections:
                self.stats["corrected"] += 1
        
        # Adicionar metadados de auditoria
        corrected_data["audit_status"] = "passed" if result.passed else "failed"
        corrected_data["audit_errors"] = result.errors
        corrected_data["audit_warnings"] = result.warnings
        corrected_data["audit_version"] = self.VERSION
        corrected_data["audit_timestamp"] = datetime.now().isoformat()
        
        return result.passed, corrected_data, result
    
    def _validate_state(self, data: Dict) -> Tuple[Dict, AuditResult]:
        """
        Valida o campo 'state' (UF).
        
        Regras:
        - Deve ser uma sigla válida de 2 caracteres
        - Não pode ser 'XX', 'N/A', vazio, etc.
        """
        result = AuditResult()
        state = data.get('state', '')
        
        # Normalizar para maiúsculas
        if state:
            state_upper = str(state).upper().strip()
            if state_upper != state:
                result.add_correction('state', state, state_upper)
                data['state'] = state_upper
                state = state_upper
        
        # Verificar se é inválido
        if state in INVALID_STATES or not state:
            result.add_error(f"Estado inválido: '{state}'")
            
            # Tentar inferir do endereço ou cidade
            inferred = self._infer_state_from_address(data)
            if inferred:
                result.add_correction('state', state, inferred)
                data['state'] = inferred
                result.errors.clear()  # Limpa o erro se conseguiu corrigir
                result.add_warning(f"Estado inferido do endereço: {inferred}")
            
        elif state not in VALID_STATES:
            result.add_error(f"Estado não reconhecido: '{state}'")
        
        return data, result
    
    def _infer_state_from_address(self, data: Dict) -> Optional[str]:
        """
        Tenta inferir o estado a partir do endereço ou cidade.
        """
        # Mapeamento de capitais para estados
        capital_to_state = {
            'SÃO PAULO': 'SP', 'SAO PAULO': 'SP',
            'RIO DE JANEIRO': 'RJ',
            'BELO HORIZONTE': 'MG',
            'SALVADOR': 'BA',
            'BRASÍLIA': 'DF', 'BRASILIA': 'DF',
            'FORTALEZA': 'CE',
            'CURITIBA': 'PR',
            'RECIFE': 'PE',
            'PORTO ALEGRE': 'RS',
            'MANAUS': 'AM',
            'BELÉM': 'PA', 'BELEM': 'PA',
            'GOIÂNIA': 'GO', 'GOIANIA': 'GO',
            'GUARULHOS': 'SP',
            'CAMPINAS': 'SP',
            'OSASCO': 'SP',
            'SANTO ANDRÉ': 'SP', 'SANTO ANDRE': 'SP',
            'NITERÓI': 'RJ', 'NITEROI': 'RJ',
            'DUQUE DE CAXIAS': 'RJ',
            'NOVA IGUAÇU': 'RJ', 'NOVA IGUACU': 'RJ',
            'CONTAGEM': 'MG',
            'UBERLÂNDIA': 'MG', 'UBERLANDIA': 'MG',
        }
        
        city = data.get('city', '').upper().strip()
        
        if city in capital_to_state:
            return capital_to_state[city]
        
        # Verificar se o endereço contém a sigla do estado
        address = data.get('address', '').upper()
        for state in VALID_STATES:
            # Procurar padrões como "- SP", ", SP", " SP "
            patterns = [f'- {state}', f', {state}', f' {state} ', f'/{state}']
            for pattern in patterns:
                if pattern in address:
                    return state
        
        return None
    
    def _validate_dates(self, data: Dict) -> Tuple[Dict, AuditResult]:
        """
        Valida as datas de leilão.
        
        Regras:
        - first_auction_date deve ser <= second_auction_date
        - Datas devem ser válidas
        - Datas muito antigas (> 30 dias no passado) geram warning
        """
        result = AuditResult()
        
        first_date = self._parse_date(data.get('first_auction_date'))
        second_date = self._parse_date(data.get('second_auction_date'))
        
        today = datetime.now()
        max_past = today - timedelta(days=30)
        max_future = today + timedelta(days=365)
        
        # Validar primeira praça
        if first_date:
            if first_date < max_past:
                result.add_warning(f"1ª praça muito antiga: {first_date.date()}")
            if first_date > max_future:
                result.add_error(f"1ª praça muito no futuro: {first_date.date()}")
        
        # Validar segunda praça
        if second_date:
            if second_date < max_past:
                result.add_warning(f"2ª praça muito antiga: {second_date.date()}")
            if second_date > max_future:
                result.add_error(f"2ª praça muito no futuro: {second_date.date()}")
        
        # Validar cronologia
        if first_date and second_date:
            if second_date < first_date:
                # Tentar corrigir invertendo as datas
                result.add_warning("Datas invertidas - corrigindo automaticamente")
                result.add_correction('first_auction_date', 
                                      data.get('first_auction_date'),
                                      data.get('second_auction_date'))
                result.add_correction('second_auction_date',
                                      data.get('second_auction_date'),
                                      data.get('first_auction_date'))
                
                # Inverter
                data['first_auction_date'], data['second_auction_date'] = \
                    data['second_auction_date'], data['first_auction_date']
                
                # Inverter valores também se existirem
                if data.get('first_auction_value') and data.get('second_auction_value'):
                    data['first_auction_value'], data['second_auction_value'] = \
                        data['second_auction_value'], data['first_auction_value']
        
        return data, result
    
    def _parse_date(self, date_value) -> Optional[datetime]:
        """
        Converte diversos formatos de data para datetime.
        """
        if not date_value:
            return None
            
        if isinstance(date_value, datetime):
            return date_value
            
        if isinstance(date_value, str):
            # Formatos comuns
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d/%m/%Y %H:%M:%S',
                '%d/%m/%Y %H:%M',
                '%d/%m/%Y',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
        
        return None
    
    def _validate_values(self, data: Dict) -> Tuple[Dict, AuditResult]:
        """
        Valida os valores de avaliação e praças.
        
        Regras:
        - evaluation_value >= first_auction_value >= second_auction_value
        - Valores devem ser positivos
        - Desconto deve estar entre 0% e 100%
        """
        result = AuditResult()
        
        eval_value = self._parse_value(data.get('evaluation_value'))
        first_value = self._parse_value(data.get('first_auction_value'))
        second_value = self._parse_value(data.get('second_auction_value'))
        
        # Validar valores positivos
        for name, value in [('evaluation_value', eval_value), 
                            ('first_auction_value', first_value),
                            ('second_auction_value', second_value)]:
            if value is not None and value < 0:
                result.add_error(f"Valor negativo em {name}: {value}")
        
        # Validar hierarquia de valores
        if eval_value and first_value:
            if first_value > eval_value:
                result.add_warning(f"1ª praça ({first_value}) maior que avaliação ({eval_value})")
        
        if first_value and second_value:
            if second_value > first_value:
                # Tentar corrigir invertendo
                result.add_warning("Valores de praça invertidos - corrigindo")
                result.add_correction('first_auction_value', first_value, second_value)
                result.add_correction('second_auction_value', second_value, first_value)
                
                data['first_auction_value'], data['second_auction_value'] = \
                    second_value, first_value
        
        # Calcular e validar desconto
        if eval_value and second_value and eval_value > 0:
            discount = ((eval_value - second_value) / eval_value) * 100
            
            if discount < 0 or discount > 100:
                result.add_error(f"Desconto inválido: {discount:.1f}%")
            else:
                # Atualizar ou adicionar desconto calculado
                current_discount = data.get('discount_percentage')
                if current_discount is None or abs(current_discount - discount) > 1:
                    result.add_correction('discount_percentage', current_discount, round(discount, 2))
                    data['discount_percentage'] = round(discount, 2)
        
        return data, result
    
    def _parse_value(self, value) -> Optional[float]:
        """
        Converte diversos formatos de valor monetário para float.
        """
        if value is None:
            return None
            
        if isinstance(value, (int, float)):
            return float(value)
            
        if isinstance(value, str):
            # Remove caracteres não numéricos, exceto vírgula e ponto
            import html
            value = html.unescape(value)  # Decodifica &#36; para $
            
            # Remove R$, espaços, etc.
            cleaned = re.sub(r'[R$\s]', '', value)
            
            # Trata formato brasileiro (1.234,56) vs americano (1,234.56)
            if ',' in cleaned and '.' in cleaned:
                # Verifica qual é o separador decimal
                if cleaned.rfind(',') > cleaned.rfind('.'):
                    # Formato brasileiro: 1.234,56
                    cleaned = cleaned.replace('.', '').replace(',', '.')
                else:
                    # Formato americano: 1,234.56
                    cleaned = cleaned.replace(',', '')
            elif ',' in cleaned:
                # Só tem vírgula: pode ser 1234,56 ou 1,234
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) == 2:
                    # Provavelmente decimal brasileiro
                    cleaned = cleaned.replace(',', '.')
                else:
                    # Provavelmente separador de milhar
                    cleaned = cleaned.replace(',', '')
            
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    def audit_batch(self, properties: List[Dict]) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Audita um lote de imóveis.
        
        Returns:
            Tuple[passed_list, failed_list, stats]
        """
        passed = []
        failed = []
        
        for prop in properties:
            is_valid, corrected, result = self.audit(prop)
            
            if is_valid:
                passed.append(corrected)
            else:
                failed.append({
                    "original": prop,
                    "errors": result.errors,
                    "warnings": result.warnings
                })
                logger.warning(f"Imóvel falhou auditoria: {prop.get('title', 'N/A')[:50]} - Erros: {result.errors}")
        
        return passed, failed, self.get_stats()
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas da auditoria."""
        total = self.stats["total_audited"]
        return {
            **self.stats,
            "pass_rate": round(self.stats["passed"] / total * 100, 2) if total > 0 else 0,
            "correction_rate": round(self.stats["corrected"] / total * 100, 2) if total > 0 else 0
        }
    
    def reset_stats(self):
        """Reseta as estatísticas."""
        self.stats = {
            "total_audited": 0,
            "passed": 0,
            "failed": 0,
            "corrected": 0
        }


# Instância singleton para uso global
_auditor_instance: Optional[QualityAuditor] = None

def get_quality_auditor() -> QualityAuditor:
    """Retorna a instância singleton do auditor."""
    global _auditor_instance
    if _auditor_instance is None:
        _auditor_instance = QualityAuditor()
    return _auditor_instance

