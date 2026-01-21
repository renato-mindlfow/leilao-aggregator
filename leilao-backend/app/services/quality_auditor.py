"""
Quality Auditor - Validação de qualidade dos dados extraídos
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class QualityAuditor:
    """Auditor de qualidade para validação de dados de imóveis."""
    
    VALID_STATES = {
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
        'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 
        'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    }
    
    AUDIT_VERSION = '1.0'
    
    def __init__(self):
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
        logger.info("QualityAuditor inicializado")
    
    def audit_property(self, property_data: Dict) -> Dict:
        """Audita uma propriedade e retorna resultado."""
        self.validation_errors = []
        self.validation_warnings = []
        
        try:
            self._validate_state(property_data)
            self._validate_dates(property_data)
            self._validate_values(property_data)
            self._validate_required_fields(property_data)
            self._validate_address(property_data)
        except Exception as e:
            logger.warning(f"Erro durante auditoria: {e}")
            self.validation_warnings.append(f'erro_auditoria:{str(e)[:50]}')
        
        return {
            'audit_passed': len(self.validation_errors) == 0,
            'audit_failed': len(self.validation_errors) > 0,
            'audit_errors': self.validation_errors.copy(),
            'audit_warnings': self.validation_warnings.copy(),
            'audit_timestamp': datetime.utcnow().isoformat(),
            'audit_version': self.AUDIT_VERSION
        }
    
    def _validate_state(self, data: Dict) -> None:
        state = data.get('state', '')
        if not state:
            self.validation_warnings.append('estado_ausente')
            return
        state = str(state).upper().strip()
        invalid_values = {'XX', 'N/A', 'NA', '', 'NULL', 'NONE'}
        if state in invalid_values:
            self.validation_errors.append(f'estado_invalido:{state}')
        elif len(state) != 2:
            self.validation_errors.append(f'estado_formato_invalido:{state}')
        elif state not in self.VALID_STATES:
            self.validation_errors.append(f'estado_nao_reconhecido:{state}')
    
    def _validate_dates(self, data: Dict) -> None:
        first_date = data.get('first_auction_date')
        second_date = data.get('second_auction_date')
        
        def parse_date(date_val):
            if not date_val:
                return None
            try:
                if isinstance(date_val, datetime):
                    return date_val
                return datetime.fromisoformat(str(date_val).replace('Z', '+00:00'))
            except:
                return None
        
        d1 = parse_date(first_date)
        d2 = parse_date(second_date)
        if d1 and d2 and d1 > d2:
            self.validation_errors.append('data_primeira_praca_maior_que_segunda')
    
    def _validate_values(self, data: Dict) -> None:
        first_value = data.get('first_auction_value')
        second_value = data.get('second_auction_value')
        
        def to_float(val):
            if val is None:
                return None
            try:
                return float(val)
            except:
                return None
        
        fv = to_float(first_value)
        sv = to_float(second_value)
        
        if fv is not None and fv < 0:
            self.validation_errors.append('first_auction_value_negativo')
        if sv is not None and sv < 0:
            self.validation_errors.append('second_auction_value_negativo')
        if fv is not None and sv is not None and sv > fv:
            self.validation_warnings.append('segunda_praca_maior_que_primeira')
    
    def _validate_required_fields(self, data: Dict) -> None:
        for field in ['title', 'source_url']:
            if not data.get(field):
                self.validation_errors.append(f'campo_obrigatorio_ausente:{field}')
    
    def _validate_address(self, data: Dict) -> None:
        address = data.get('address', '')
        if not address:
            return
        address_upper = str(address).upper()
        blacklist = ['ENTRE EM CONTATO', 'WHATSAPP', 'WWW.', '.COM.BR']
        for pattern in blacklist:
            if pattern in address_upper:
                self.validation_warnings.append('endereco_texto_promocional')
                break
    
    def audit_batch(self, properties: List[Dict]) -> List[Dict]:
        results = []
        for prop in properties:
            audit_result = self.audit_property(prop)
            results.append({**prop, **audit_result})
        return results
    
    def get_statistics(self, audited_properties: List[Dict]) -> Dict:
        total = len(audited_properties)
        if total == 0:
            return {'total': 0, 'passed': 0, 'failed': 0, 'pass_rate': 0}
        passed = sum(1 for p in audited_properties if p.get('audit_passed', False))
        return {
            'total': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': round(passed / total * 100, 2)
        }


_quality_auditor_instance: Optional[QualityAuditor] = None


def get_quality_auditor() -> QualityAuditor:
    """Retorna instância singleton do QualityAuditor."""
    global _quality_auditor_instance
    if _quality_auditor_instance is None:
        _quality_auditor_instance = QualityAuditor()
    return _quality_auditor_instance


__all__ = ['QualityAuditor', 'get_quality_auditor']
