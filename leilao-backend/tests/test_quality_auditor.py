"""
Testes Unitários - Quality Auditor

Execute com: pytest test_quality_auditor.py -v
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

# Adicionar diretório pai ao path para importar o módulo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.quality_auditor import QualityAuditor, audit_property, audit_batch


class TestValidateState:
    """Testes para validação de estado."""
    
    def setup_method(self):
        self.auditor = QualityAuditor()
    
    def test_valid_state_uppercase(self):
        """Estado válido em uppercase deve passar."""
        prop = {'state': 'SP'}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_valid_state_lowercase_corrected(self):
        """Estado válido em lowercase deve ser corrigido para uppercase."""
        prop = {'state': 'sp'}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is True
        assert prop['state'] == 'SP'
        assert 'state' in corrections
    
    def test_truncated_state_sa_to_sp(self):
        """Estado truncado 'Sã' deve ser corrigido para 'SP'."""
        prop = {'state': 'Sã'}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is True
        assert prop['state'] == 'SP'
    
    def test_truncated_state_ri_to_rj(self):
        """Estado truncado 'Ri' deve ser corrigido para 'RJ'."""
        prop = {'state': 'Ri'}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is True
        assert prop['state'] == 'RJ'
    
    def test_truncated_state_mi_to_mg(self):
        """Estado truncado 'Mi' deve ser corrigido para 'MG'."""
        prop = {'state': 'Mi'}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is True
        assert prop['state'] == 'MG'
    
    def test_pa_with_parana_city_becomes_pr(self):
        """Estado 'Pa' com cidade do Paraná deve ser corrigido para 'PR'."""
        prop = {'state': 'Pa', 'city': 'Curitiba'}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is True
        assert prop['state'] == 'PR'
    
    def test_pa_with_para_city_becomes_pa(self):
        """Estado 'Pa' com cidade do Pará deve ser corrigido para 'PA'."""
        prop = {'state': 'Pa', 'city': 'Belém'}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is True
        assert prop['state'] == 'PA'
    
    def test_invalid_state_xx(self):
        """Estado 'XX' deve ser rejeitado."""
        prop = {'state': 'XX'}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is False
        assert 'estado_vazio_ou_invalido' in errors
    
    def test_invalid_state_ni(self):
        """Estado 'NI' deve ser rejeitado."""
        prop = {'state': 'NI'}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is False
    
    def test_empty_state(self):
        """Estado vazio deve ser rejeitado."""
        prop = {'state': ''}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is False
    
    def test_none_state(self):
        """Estado None deve ser rejeitado."""
        prop = {'state': None}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is False
    
    def test_full_name_sao_paulo(self):
        """Nome completo 'são paulo' deve ser corrigido para 'SP'."""
        prop = {'state': 'são paulo'}
        is_valid, errors, corrections = self.auditor.validate_state(prop)
        assert is_valid is True
        assert prop['state'] == 'SP'


class TestValidateDates:
    """Testes para validação de datas."""
    
    def setup_method(self):
        self.auditor = QualityAuditor()
    
    def test_valid_dates_iso_format(self):
        """Datas válidas em formato ISO devem passar."""
        future = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        prop = {'first_auction_date': future, 'second_auction_date': future}
        is_valid, errors, corrections = self.auditor.validate_dates(prop)
        assert is_valid is True
    
    def test_valid_dates_br_format(self):
        """Datas válidas em formato BR devem passar."""
        future = (datetime.now() + timedelta(days=30)).strftime('%d/%m/%Y')
        prop = {'first_auction_date': future, 'second_auction_date': future}
        is_valid, errors, corrections = self.auditor.validate_dates(prop)
        assert is_valid is True
    
    def test_inverted_dates_fail(self):
        """Datas invertidas devem falhar (first > second)."""
        first = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
        second = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        prop = {'first_auction_date': first, 'second_auction_date': second}
        is_valid, errors, corrections = self.auditor.validate_dates(prop)
        assert is_valid is False
        assert any('invertidas' in e for e in errors)
    
    def test_no_dates_passes(self):
        """Sem datas deve passar (campos opcionais)."""
        prop = {}
        is_valid, errors, corrections = self.auditor.validate_dates(prop)
        assert is_valid is True
    
    def test_invalid_date_format(self):
        """Formato de data inválido deve falhar."""
        prop = {'first_auction_date': 'not-a-date'}
        is_valid, errors, corrections = self.auditor.validate_dates(prop)
        assert is_valid is False
        assert any('formato_invalido' in e for e in errors)


class TestValidateValues:
    """Testes para validação de valores."""
    
    def setup_method(self):
        self.auditor = QualityAuditor()
    
    def test_valid_value_hierarchy(self):
        """Hierarquia válida de valores deve passar."""
        prop = {
            'evaluation_value': 100000,
            'first_auction_value': 80000,
            'second_auction_value': 60000
        }
        is_valid, errors, corrections = self.auditor.validate_values(prop)
        assert is_valid is True
    
    def test_second_greater_than_first_fails(self):
        """second_auction_value > first_auction_value deve falhar."""
        prop = {
            'first_auction_value': 50000,
            'second_auction_value': 80000
        }
        is_valid, errors, corrections = self.auditor.validate_values(prop)
        assert is_valid is False
    
    def test_discount_recalculated(self):
        """Desconto deve ser recalculado se inconsistente."""
        prop = {
            'evaluation_value': 100000,
            'second_auction_value': 70000,
            'discount_percentage': 10  # Incorreto, deveria ser 30
        }
        is_valid, errors, corrections = self.auditor.validate_values(prop)
        assert is_valid is True
        assert prop['discount_percentage'] == 30.0
    
    def test_discount_set_when_missing(self):
        """Desconto deve ser calculado se ausente."""
        prop = {
            'evaluation_value': 100000,
            'second_auction_value': 60000
        }
        is_valid, errors, corrections = self.auditor.validate_values(prop)
        assert is_valid is True
        assert prop['discount_percentage'] == 40.0
    
    def test_no_values_passes(self):
        """Sem valores deve passar (campos opcionais)."""
        prop = {}
        is_valid, errors, corrections = self.auditor.validate_values(prop)
        assert is_valid is True


class TestValidateCategory:
    """Testes para validação de categoria."""
    
    def setup_method(self):
        self.auditor = QualityAuditor()
    
    def test_valid_category(self):
        """Categoria válida deve passar."""
        prop = {'category': 'Apartamento'}
        is_valid, errors, corrections = self.auditor.validate_category(prop)
        assert is_valid is True
    
    def test_lowercase_normalized(self):
        """Categoria em lowercase deve ser normalizada."""
        prop = {'category': 'apartamento'}
        is_valid, errors, corrections = self.auditor.validate_category(prop)
        assert is_valid is True
        assert prop['category'] == 'Apartamento'
    
    def test_abbreviation_mapped(self):
        """Abreviação deve ser mapeada."""
        prop = {'category': 'apto'}
        is_valid, errors, corrections = self.auditor.validate_category(prop)
        assert is_valid is True
        assert prop['category'] == 'Apartamento'
    
    def test_unknown_category_becomes_outro(self):
        """Categoria desconhecida deve ser 'Outro'."""
        prop = {'category': 'xyz123'}
        is_valid, errors, corrections = self.auditor.validate_category(prop)
        assert is_valid is True
        assert prop['category'] == 'Outro'
    
    def test_none_category_becomes_outro(self):
        """Categoria None deve ser 'Outro'."""
        prop = {'category': None}
        is_valid, errors, corrections = self.auditor.validate_category(prop)
        assert is_valid is True
        assert prop['category'] == 'Outro'


class TestValidateCity:
    """Testes para validação de cidade."""
    
    def setup_method(self):
        self.auditor = QualityAuditor()
    
    def test_title_case_applied(self):
        """Title Case deve ser aplicado."""
        prop = {'city': 'são paulo'}
        is_valid, errors, corrections = self.auditor.validate_city(prop)
        assert is_valid is True
        assert prop['city'] == 'São Paulo'
    
    def test_state_extracted_from_city(self):
        """Estado deve ser extraído da cidade se presente."""
        prop = {'city': 'São Paulo - SP', 'state': None}
        is_valid, errors, corrections = self.auditor.validate_city(prop)
        assert is_valid is True
        assert prop['city'] == 'São Paulo'
        assert prop['state'] == 'SP'
    
    def test_state_not_overwritten(self):
        """Estado existente não deve ser sobrescrito."""
        prop = {'city': 'Fortaleza - CE', 'state': 'BA'}  # Estado já definido
        is_valid, errors, corrections = self.auditor.validate_city(prop)
        assert is_valid is True
        assert prop['state'] == 'BA'  # Mantém o existente


class TestAuditProperty:
    """Testes para auditoria completa de imóvel."""
    
    def setup_method(self):
        self.auditor = QualityAuditor()
    
    def test_valid_property_passes(self):
        """Imóvel válido deve passar na auditoria."""
        prop = {
            'state': 'SP',
            'city': 'São Paulo',
            'category': 'Apartamento',
            'evaluation_value': 500000,
            'first_auction_value': 400000,
            'second_auction_value': 300000
        }
        result = self.auditor.audit_property(prop)
        assert result['audit_passed'] is True
        assert len(result['audit_errors']) == 0
    
    def test_invalid_state_fails_audit(self):
        """Imóvel com estado inválido deve falhar."""
        prop = {
            'state': 'XX',
            'city': 'São Paulo',
            'category': 'Apartamento'
        }
        result = self.auditor.audit_property(prop)
        assert result['audit_passed'] is False
    
    def test_corrections_applied(self):
        """Correções devem ser aplicadas."""
        prop = {
            'state': 'Sã',  # Será corrigido para SP
            'city': 'são paulo',  # Será corrigido para São Paulo
            'category': 'apto'  # Será corrigido para Apartamento
        }
        result = self.auditor.audit_property(prop)
        assert result['audit_passed'] is True
        assert prop['state'] == 'SP'
        assert prop['city'] == 'São Paulo'
        assert prop['category'] == 'Apartamento'
    
    def test_audit_metadata_added(self):
        """Metadados de auditoria devem ser adicionados."""
        prop = {'state': 'SP', 'city': 'São Paulo', 'category': 'Casa'}
        result = self.auditor.audit_property(prop)
        assert 'audit_status' in prop
        assert 'audit_timestamp' in prop
        assert 'audit_version' in prop


class TestAuditBatch:
    """Testes para auditoria em lote."""
    
    def setup_method(self):
        self.auditor = QualityAuditor()
    
    def test_batch_separates_passed_and_failed(self):
        """Lote deve separar aprovados e reprovados."""
        properties = [
            {'state': 'SP', 'city': 'São Paulo', 'category': 'Casa'},
            {'state': 'XX', 'city': 'Invalid', 'category': 'Unknown'},
            {'state': 'RJ', 'city': 'Rio', 'category': 'Apartamento'}
        ]
        passed, failed = self.auditor.audit_batch(properties)
        assert len(passed) == 2
        assert len(failed) == 1
    
    def test_stats_updated(self):
        """Estatísticas devem ser atualizadas."""
        self.auditor.reset_stats()
        properties = [
            {'state': 'SP', 'city': 'São Paulo', 'category': 'Casa'},
            {'state': 'XX', 'city': 'Invalid', 'category': 'Unknown'}
        ]
        self.auditor.audit_batch(properties)
        stats = self.auditor.get_stats()
        assert stats['total_audited'] == 2
        assert stats['passed'] == 1
        assert stats['failed'] == 1


class TestConvenienceFunctions:
    """Testes para funções de conveniência."""
    
    def test_audit_property_function(self):
        """Função audit_property deve funcionar."""
        prop = {'state': 'SP', 'city': 'São Paulo', 'category': 'Casa'}
        result = audit_property(prop)
        assert 'audit_passed' in result
    
    def test_audit_batch_function(self):
        """Função audit_batch deve funcionar."""
        properties = [
            {'state': 'SP', 'city': 'São Paulo', 'category': 'Casa'}
        ]
        passed, failed = audit_batch(properties)
        assert len(passed) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
