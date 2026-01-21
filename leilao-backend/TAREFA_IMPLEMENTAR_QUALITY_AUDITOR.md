# TAREFA AUTÔNOMA: Implementar Sistema de Auditoria de Qualidade

**Data:** 2026-01-21
**Prioridade:** ALTA
**Tempo estimado:** 30-45 minutos
**Execução:** AUTÔNOMA (não pare para perguntar)

---

## 🎯 OBJETIVO

Implementar o sistema completo de auditoria de qualidade conforme documentado em `ESTRATEGIA_AUDITORIA_QUALIDADE_IA.md`, incluindo:

1. Classe `QualityAuditor` em Python
2. Campos de auditoria no banco de dados (Supabase)
3. Trigger de normalização automática
4. Integração com o pipeline de scraping existente

---

## 📋 CONTEXTO

### Problema Resolvido Hoje
- ~8.800 registros tinham estados inválidos (Sã, Ri, Mi, etc.)
- Corrigidos via SQL direto no Supabase
- Agora: 50.873 válidos, 2.115 NULL, 0 inválidos

### Problema a Prevenir
- Novos dados entrando sem validação
- Estados truncados, datas inválidas, valores inconsistentes
- Falta de rastreabilidade de qualidade

---

## 📁 ARQUIVOS A CRIAR

### 1. `app/services/quality_auditor.py`
Classe principal de auditoria com:
- `validate_state()` - Validar UF
- `validate_dates()` - Validar datas de leilão
- `validate_values()` - Validar valores de praça
- `validate_category()` - Normalizar categoria
- `audit_property()` - Auditar um imóvel
- `audit_batch()` - Auditar lote de imóveis
- `auto_correct()` - Correção automática quando possível

### 2. `scripts/sql/add_audit_fields.sql`
SQL para adicionar campos de auditoria à tabela properties

### 3. `scripts/sql/create_normalize_trigger.sql`
Trigger PostgreSQL para normalização automática

### 4. `tests/test_quality_auditor.py`
Testes unitários para a classe QualityAuditor

---

## 🔧 ESPECIFICAÇÕES TÉCNICAS

### Validação de Estado (UF)

```python
VALID_STATES = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']

# Mapeamento de correção automática
STATE_CORRECTIONS = {
    'Sã': 'SP', 'Sa': 'SP', 'Sp': 'SP',
    'Ri': 'RJ', 'Rj': 'RJ',
    'Mi': 'MG', 'Mg': 'MG',
    'Go': 'GO',
    'Ba': 'BA',
    'Ce': 'CE',
    'Pe': 'PE',
    'Ma': 'MA',
    'Pa': 'PA',  # Default para PA, verificar cidade para PR
    'Pr': 'PR',
    'Rs': 'RS',
    'Sc': 'SC',
    'Es': 'ES',
    'Mt': 'MT',
    'Ms': 'MS',
    'Df': 'DF', 'Di': 'DF',
    'Se': 'SE',
    'Ro': 'RO',
    'To': 'TO',
    'Pi': 'PI',
    'Al': 'AL',
    'Rn': 'RN',
    'Pb': 'PB',
    'Am': 'AM',
    'Ap': 'AP',
    'Rr': 'RR',
    'Ac': 'AC',
}

# Cidades do Paraná (para diferenciar Pa → PA vs PR)
PARANA_CITIES = ['curitiba', 'londrina', 'maringá', 'maringa', 'cascavel', 'ponta grossa', 'foz do iguaçu', 'foz do iguacu', 'colombo', 'guarapuava', 'paranaguá', 'paranagua', 'araucária', 'araucaria', 'toledo', 'apucarana', 'campo largo', 'umuarama', 'pinhais', 'são josé dos pinhais', 'sao jose dos pinhais']
```

### Validação de Datas

```python
def validate_dates(self, property_data: dict) -> tuple[bool, list[str]]:
    """
    Validar datas de leilão.
    
    Regras:
    1. first_auction_date <= second_auction_date
    2. Datas devem estar no futuro ou máx 30 dias no passado
    3. Formato válido (ISO 8601 ou DD/MM/YYYY)
    """
    errors = []
    
    first_date = property_data.get('first_auction_date')
    second_date = property_data.get('second_auction_date')
    
    # Converter para datetime se string
    # Validar cronologia
    # Validar range aceitável
    
    return len(errors) == 0, errors
```

### Validação de Valores

```python
def validate_values(self, property_data: dict) -> tuple[bool, list[str]]:
    """
    Validar valores de praça.
    
    Regras:
    1. second_auction_value <= first_auction_value
    2. first_auction_value <= evaluation_value (se existir)
    3. discount_percentage entre 0% e 100%
    4. Recalcular discount_percentage se inconsistente
    """
    errors = []
    
    eval_value = property_data.get('evaluation_value')
    first_value = property_data.get('first_auction_value')
    second_value = property_data.get('second_auction_value')
    discount = property_data.get('discount_percentage')
    
    # Validar hierarquia de valores
    # Recalcular desconto se necessário
    
    return len(errors) == 0, errors
```

### Estrutura de Retorno da Auditoria

```python
{
    "audit_passed": True/False,
    "audit_errors": ["erro1", "erro2"],
    "audit_warnings": ["aviso1"],
    "audit_timestamp": "2026-01-21T14:30:00",
    "audit_version": "1.0.0",
    "corrections_applied": ["state: Sã -> SP", "category: APARTAMENTO -> Apartamento"]
}
```

---

## 📝 CÓDIGO COMPLETO - quality_auditor.py

```python
"""
Quality Auditor - Sistema de Auditoria de Qualidade para LeiloHub

Implementa validações conforme ESTRATEGIA_AUDITORIA_QUALIDADE_IA.md:
1. Validação de Estado (UF)
2. Validação de Datas de Leilão
3. Validação de Valores de Praça
4. Normalização de Categorias e Cidades

Autor: LeiloHub Team
Data: 2026-01-21
Versão: 1.0.0
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class QualityAuditor:
    """
    Auditor de qualidade para imóveis do LeiloHub.
    
    Valida e normaliza dados antes de persistir no Supabase.
    """
    
    VERSION = "1.0.0"
    
    # Estados válidos do Brasil
    VALID_STATES = [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
        'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    ]
    
    # Mapeamento de correção automática de estados
    STATE_CORRECTIONS = {
        'Sã': 'SP', 'Sa': 'SP', 'Sp': 'SP', 'sp': 'SP', 'sã': 'SP', 'sa': 'SP',
        'são paulo': 'SP', 'sao paulo': 'SP',
        'Ri': 'RJ', 'Rj': 'RJ', 'rj': 'RJ', 'ri': 'RJ',
        'rio de janeiro': 'RJ',
        'Mi': 'MG', 'Mg': 'MG', 'mg': 'MG', 'mi': 'MG',
        'minas gerais': 'MG',
        'Go': 'GO', 'go': 'GO', 'goiás': 'GO', 'goias': 'GO',
        'Ba': 'BA', 'ba': 'BA', 'bahia': 'BA',
        'Ce': 'CE', 'ce': 'CE', 'ceará': 'CE', 'ceara': 'CE',
        'Pe': 'PE', 'pe': 'PE', 'pernambuco': 'PE',
        'Ma': 'MA', 'ma': 'MA', 'maranhão': 'MA', 'maranhao': 'MA',
        'Pr': 'PR', 'pr': 'PR', 'paraná': 'PR', 'parana': 'PR',
        'Rs': 'RS', 'rs': 'RS', 'rio grande do sul': 'RS',
        'Sc': 'SC', 'sc': 'SC', 'santa catarina': 'SC',
        'Es': 'ES', 'es': 'ES', 'espírito santo': 'ES', 'espirito santo': 'ES',
        'Mt': 'MT', 'mt': 'MT', 'mato grosso': 'MT',
        'Ms': 'MS', 'ms': 'MS', 'mato grosso do sul': 'MS',
        'Df': 'DF', 'df': 'DF', 'Di': 'DF', 'di': 'DF',
        'distrito federal': 'DF', 'brasília': 'DF', 'brasilia': 'DF',
        'Se': 'SE', 'se': 'SE', 'sergipe': 'SE',
        'Ro': 'RO', 'ro': 'RO', 'rondônia': 'RO', 'rondonia': 'RO',
        'To': 'TO', 'to': 'TO', 'tocantins': 'TO',
        'Pi': 'PI', 'pi': 'PI', 'piauí': 'PI', 'piaui': 'PI',
        'Al': 'AL', 'al': 'AL', 'alagoas': 'AL',
        'Rn': 'RN', 'rn': 'RN', 'rio grande do norte': 'RN',
        'Pb': 'PB', 'pb': 'PB', 'paraíba': 'PB', 'paraiba': 'PB',
        'Am': 'AM', 'am': 'AM', 'amazonas': 'AM',
        'Ap': 'AP', 'ap': 'AP', 'amapá': 'AP', 'amapa': 'AP',
        'Rr': 'RR', 'rr': 'RR', 'roraima': 'RR',
        'Ac': 'AC', 'ac': 'AC', 'acre': 'AC',
        'Pa': 'PA', 'pa': 'PA', 'pará': 'PA', 'para': 'PA',
    }
    
    # Cidades do Paraná (para diferenciar Pa → PA vs PR)
    PARANA_CITIES = [
        'curitiba', 'londrina', 'maringá', 'maringa', 'cascavel', 
        'ponta grossa', 'foz do iguaçu', 'foz do iguacu', 'colombo', 
        'guarapuava', 'paranaguá', 'paranagua', 'araucária', 'araucaria', 
        'toledo', 'apucarana', 'campo largo', 'umuarama', 'pinhais', 
        'são josé dos pinhais', 'sao jose dos pinhais'
    ]
    
    # Categorias válidas (Title Case)
    VALID_CATEGORIES = [
        'Apartamento', 'Casa', 'Terreno', 'Comercial', 'Rural',
        'Galpão', 'Sala', 'Loja', 'Prédio', 'Fazenda', 'Sítio',
        'Chácara', 'Flat', 'Cobertura', 'Studio', 'Kitnet', 'Outro'
    ]
    
    # Mapeamento de normalização de categorias
    CATEGORY_MAPPING = {
        'apartamento': 'Apartamento',
        'apto': 'Apartamento',
        'apt': 'Apartamento',
        'casa': 'Casa',
        'residencia': 'Casa',
        'residência': 'Casa',
        'sobrado': 'Casa',
        'terreno': 'Terreno',
        'lote': 'Terreno',
        'comercial': 'Comercial',
        'loja': 'Loja',
        'sala': 'Sala',
        'sala comercial': 'Sala',
        'galpão': 'Galpão',
        'galpao': 'Galpão',
        'barracão': 'Galpão',
        'barracao': 'Galpão',
        'prédio': 'Prédio',
        'predio': 'Prédio',
        'edificio': 'Prédio',
        'edifício': 'Prédio',
        'rural': 'Rural',
        'fazenda': 'Fazenda',
        'sítio': 'Sítio',
        'sitio': 'Sítio',
        'chácara': 'Chácara',
        'chacara': 'Chácara',
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
    
    # Valores inválidos para estado
    INVALID_STATE_VALUES = ['XX', 'NI', 'N/A', 'NA', 'UF', '', None, 'NÃ', 'NÂ']
    
    def __init__(self):
        """Inicializa o auditor de qualidade."""
        self.stats = {
            'total_audited': 0,
            'passed': 0,
            'failed': 0,
            'auto_corrected': 0,
            'errors_by_type': {}
        }
    
    def validate_state(self, property_data: Dict) -> Tuple[bool, List[str], Dict]:
        """
        Valida e corrige o estado (UF).
        
        Args:
            property_data: Dicionário com dados do imóvel
            
        Returns:
            Tuple[bool, List[str], Dict]: (is_valid, errors, corrections)
        """
        errors = []
        corrections = {}
        
        state = property_data.get('state')
        city = property_data.get('city', '')
        
        # Verificar se é valor inválido conhecido
        if state in self.INVALID_STATE_VALUES or not state:
            errors.append('estado_vazio_ou_invalido')
            return False, errors, corrections
        
        # Tentar converter para string e limpar
        state = str(state).strip()
        
        # Verificar se já é válido (uppercase)
        if state.upper() in self.VALID_STATES:
            if state != state.upper():
                corrections['state'] = f"{state} -> {state.upper()}"
                property_data['state'] = state.upper()
            return True, errors, corrections
        
        # Tentar correção automática
        if state in self.STATE_CORRECTIONS:
            corrected = self.STATE_CORRECTIONS[state]
            
            # Caso especial: Pa pode ser PA (Pará) ou PR (Paraná)
            if state.lower() == 'pa' and city:
                city_lower = city.lower()
                if any(pr_city in city_lower for pr_city in self.PARANA_CITIES):
                    corrected = 'PR'
            
            corrections['state'] = f"{state} -> {corrected}"
            property_data['state'] = corrected
            return True, errors, corrections
        
        # Tentar correção por lowercase
        if state.lower() in self.STATE_CORRECTIONS:
            corrected = self.STATE_CORRECTIONS[state.lower()]
            corrections['state'] = f"{state} -> {corrected}"
            property_data['state'] = corrected
            return True, errors, corrections
        
        # Estado não reconhecido
        errors.append(f'estado_invalido: {state}')
        return False, errors, corrections
    
    def validate_dates(self, property_data: Dict) -> Tuple[bool, List[str], Dict]:
        """
        Valida datas de leilão.
        
        Regras:
        1. first_auction_date <= second_auction_date
        2. Datas devem estar no futuro ou máx 30 dias no passado
        3. Formato válido
        
        Args:
            property_data: Dicionário com dados do imóvel
            
        Returns:
            Tuple[bool, List[str], Dict]: (is_valid, errors, corrections)
        """
        errors = []
        corrections = {}
        warnings = []
        
        first_date_str = property_data.get('first_auction_date')
        second_date_str = property_data.get('second_auction_date')
        
        # Se ambas são None, não há o que validar
        if not first_date_str and not second_date_str:
            return True, errors, corrections
        
        # Parser de data flexível
        def parse_date(date_str) -> Optional[datetime]:
            if not date_str:
                return None
            if isinstance(date_str, datetime):
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
                    return datetime.strptime(str(date_str)[:19], fmt)
                except ValueError:
                    continue
            return None
        
        first_date = parse_date(first_date_str)
        second_date = parse_date(second_date_str)
        
        # Validar formato
        if first_date_str and not first_date:
            errors.append(f'first_auction_date_formato_invalido: {first_date_str}')
        
        if second_date_str and not second_date:
            errors.append(f'second_auction_date_formato_invalido: {second_date_str}')
        
        # Validar cronologia (first <= second)
        if first_date and second_date:
            if first_date > second_date:
                errors.append('datas_invertidas: first_auction_date > second_auction_date')
        
        # Validar range (não muito no passado)
        min_date = datetime.now() - timedelta(days=30)
        
        if first_date and first_date < min_date:
            warnings.append(f'first_auction_date_no_passado: {first_date_str}')
        
        if second_date and second_date < min_date:
            warnings.append(f'second_auction_date_no_passado: {second_date_str}')
        
        # Adicionar warnings ao property_data para referência
        if warnings:
            property_data['_audit_warnings'] = property_data.get('_audit_warnings', []) + warnings
        
        return len(errors) == 0, errors, corrections
    
    def validate_values(self, property_data: Dict) -> Tuple[bool, List[str], Dict]:
        """
        Valida valores de praça.
        
        Regras:
        1. second_auction_value <= first_auction_value
        2. first_auction_value <= evaluation_value (se existir)
        3. discount_percentage entre 0% e 100%
        
        Args:
            property_data: Dicionário com dados do imóvel
            
        Returns:
            Tuple[bool, List[str], Dict]: (is_valid, errors, corrections)
        """
        errors = []
        corrections = {}
        
        eval_value = property_data.get('evaluation_value')
        first_value = property_data.get('first_auction_value')
        second_value = property_data.get('second_auction_value')
        discount = property_data.get('discount_percentage')
        
        # Converter para float se necessário
        def to_float(val) -> Optional[float]:
            if val is None:
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None
        
        eval_value = to_float(eval_value)
        first_value = to_float(first_value)
        second_value = to_float(second_value)
        discount = to_float(discount)
        
        # Validar hierarquia de valores
        if eval_value and first_value:
            if first_value > eval_value * 1.1:  # 10% de tolerância
                errors.append(f'first_auction_value ({first_value}) > evaluation_value ({eval_value})')
        
        if first_value and second_value:
            if second_value > first_value * 1.1:  # 10% de tolerância
                errors.append(f'second_auction_value ({second_value}) > first_auction_value ({first_value})')
        
        # Recalcular discount_percentage se necessário
        if eval_value and second_value and eval_value > 0:
            calculated_discount = ((eval_value - second_value) / eval_value) * 100
            if calculated_discount >= 0 and calculated_discount <= 100:
                if discount is None or abs(discount - calculated_discount) > 5:
                    corrections['discount_percentage'] = f"{discount} -> {round(calculated_discount, 2)}"
                    property_data['discount_percentage'] = round(calculated_discount, 2)
        elif first_value and second_value and first_value > 0:
            calculated_discount = ((first_value - second_value) / first_value) * 100
            if calculated_discount >= 0 and calculated_discount <= 100:
                if discount is None or abs(discount - calculated_discount) > 5:
                    corrections['discount_percentage'] = f"{discount} -> {round(calculated_discount, 2)}"
                    property_data['discount_percentage'] = round(calculated_discount, 2)
        
        # Validar range do desconto
        current_discount = to_float(property_data.get('discount_percentage'))
        if current_discount is not None:
            if current_discount < 0 or current_discount > 100:
                errors.append(f'discount_percentage_fora_do_range: {current_discount}')
        
        return len(errors) == 0, errors, corrections
    
    def validate_category(self, property_data: Dict) -> Tuple[bool, List[str], Dict]:
        """
        Valida e normaliza categoria.
        
        Args:
            property_data: Dicionário com dados do imóvel
            
        Returns:
            Tuple[bool, List[str], Dict]: (is_valid, errors, corrections)
        """
        errors = []
        corrections = {}
        
        category = property_data.get('category')
        
        if not category:
            property_data['category'] = 'Outro'
            corrections['category'] = "None -> Outro"
            return True, errors, corrections
        
        category_str = str(category).strip()
        
        # Verificar se já está normalizado
        if category_str in self.VALID_CATEGORIES:
            return True, errors, corrections
        
        # Tentar mapear
        category_lower = category_str.lower()
        if category_lower in self.CATEGORY_MAPPING:
            normalized = self.CATEGORY_MAPPING[category_lower]
            corrections['category'] = f"{category_str} -> {normalized}"
            property_data['category'] = normalized
            return True, errors, corrections
        
        # Tentar Title Case
        title_case = category_str.title()
        if title_case in self.VALID_CATEGORIES:
            corrections['category'] = f"{category_str} -> {title_case}"
            property_data['category'] = title_case
            return True, errors, corrections
        
        # Categoria não reconhecida - usar "Outro"
        corrections['category'] = f"{category_str} -> Outro"
        property_data['category'] = 'Outro'
        return True, errors, corrections
    
    def validate_city(self, property_data: Dict) -> Tuple[bool, List[str], Dict]:
        """
        Valida e normaliza cidade (Title Case, remove estado se presente).
        
        Args:
            property_data: Dicionário com dados do imóvel
            
        Returns:
            Tuple[bool, List[str], Dict]: (is_valid, errors, corrections)
        """
        errors = []
        corrections = {}
        
        city = property_data.get('city')
        
        if not city:
            return True, errors, corrections
        
        city_str = str(city).strip()
        original_city = city_str
        
        # Remover estado se presente no formato "Cidade - UF"
        if ' - ' in city_str and len(city_str.split(' - ')[-1]) == 2:
            parts = city_str.rsplit(' - ', 1)
            city_str = parts[0].strip()
            # Se estado não está definido, extrair
            if not property_data.get('state'):
                property_data['state'] = parts[1].strip().upper()
                corrections['state_from_city'] = f"Extraído: {parts[1].strip().upper()}"
        
        # Remover " / UF" no final
        city_str = re.sub(r'\s*/\s*[A-Za-z]{2}\s*$', '', city_str)
        
        # Aplicar Title Case
        normalized = city_str.title()
        
        if normalized != original_city:
            corrections['city'] = f"{original_city} -> {normalized}"
            property_data['city'] = normalized
        
        return True, errors, corrections
    
    def audit_property(self, property_data: Dict) -> Dict:
        """
        Audita um único imóvel.
        
        Args:
            property_data: Dicionário com dados do imóvel
            
        Returns:
            Dict: Dicionário com resultado da auditoria
        """
        all_errors = []
        all_corrections = []
        
        # Validar estado
        state_valid, state_errors, state_corrections = self.validate_state(property_data)
        all_errors.extend(state_errors)
        if state_corrections:
            all_corrections.append(state_corrections)
        
        # Validar datas
        dates_valid, dates_errors, dates_corrections = self.validate_dates(property_data)
        all_errors.extend(dates_errors)
        if dates_corrections:
            all_corrections.append(dates_corrections)
        
        # Validar valores
        values_valid, values_errors, values_corrections = self.validate_values(property_data)
        all_errors.extend(values_errors)
        if values_corrections:
            all_corrections.append(values_corrections)
        
        # Validar categoria
        category_valid, category_errors, category_corrections = self.validate_category(property_data)
        all_errors.extend(category_errors)
        if category_corrections:
            all_corrections.append(category_corrections)
        
        # Validar cidade
        city_valid, city_errors, city_corrections = self.validate_city(property_data)
        all_errors.extend(city_errors)
        if city_corrections:
            all_corrections.append(city_corrections)
        
        # Consolidar resultado
        audit_passed = len(all_errors) == 0
        
        # Atualizar estatísticas
        self.stats['total_audited'] += 1
        if audit_passed:
            self.stats['passed'] += 1
        else:
            self.stats['failed'] += 1
        if all_corrections:
            self.stats['auto_corrected'] += 1
        
        for error in all_errors:
            error_type = error.split(':')[0]
            self.stats['errors_by_type'][error_type] = self.stats['errors_by_type'].get(error_type, 0) + 1
        
        # Adicionar metadados de auditoria ao imóvel
        property_data['audit_status'] = 'passed' if audit_passed else 'failed'
        property_data['audit_errors'] = all_errors if all_errors else None
        property_data['audit_warnings'] = property_data.pop('_audit_warnings', None)
        property_data['audit_timestamp'] = datetime.now().isoformat()
        property_data['audit_version'] = self.VERSION
        
        return {
            'property': property_data,
            'audit_passed': audit_passed,
            'audit_errors': all_errors,
            'audit_warnings': property_data.get('audit_warnings', []),
            'corrections_applied': all_corrections,
            'audit_timestamp': property_data['audit_timestamp'],
            'audit_version': self.VERSION
        }
    
    def audit_batch(self, properties: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Audita um lote de imóveis.
        
        Args:
            properties: Lista de dicionários com dados dos imóveis
            
        Returns:
            Tuple[List[Dict], List[Dict]]: (passed, failed)
        """
        passed = []
        failed = []
        
        for prop in properties:
            result = self.audit_property(prop)
            if result['audit_passed']:
                passed.append(result['property'])
            else:
                failed.append(result)
        
        logger.info(f"Auditoria concluída: {len(passed)} aprovados, {len(failed)} reprovados")
        
        return passed, failed
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas de auditoria."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reseta estatísticas de auditoria."""
        self.stats = {
            'total_audited': 0,
            'passed': 0,
            'failed': 0,
            'auto_corrected': 0,
            'errors_by_type': {}
        }


# Singleton para uso global
quality_auditor = QualityAuditor()


def audit_property(property_data: Dict) -> Dict:
    """Função de conveniência para auditar um imóvel."""
    return quality_auditor.audit_property(property_data)


def audit_batch(properties: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Função de conveniência para auditar um lote."""
    return quality_auditor.audit_batch(properties)
```

---

## 📝 SQL - CAMPOS DE AUDITORIA

```sql
-- ============================================================
-- ADICIONAR CAMPOS DE AUDITORIA À TABELA PROPERTIES
-- Execute no Supabase SQL Editor
-- ============================================================

-- Adicionar campos de auditoria
ALTER TABLE properties ADD COLUMN IF NOT EXISTS audit_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE properties ADD COLUMN IF NOT EXISTS audit_errors TEXT[];
ALTER TABLE properties ADD COLUMN IF NOT EXISTS audit_warnings TEXT[];
ALTER TABLE properties ADD COLUMN IF NOT EXISTS audit_timestamp TIMESTAMP;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS audit_version VARCHAR(10);

-- Criar índice para busca por status de auditoria
CREATE INDEX IF NOT EXISTS idx_properties_audit_status ON properties(audit_status);

-- Comentários para documentação
COMMENT ON COLUMN properties.audit_status IS 'Status da auditoria: pending, passed, failed';
COMMENT ON COLUMN properties.audit_errors IS 'Array de erros encontrados na auditoria';
COMMENT ON COLUMN properties.audit_warnings IS 'Array de avisos (não bloqueiam commit)';
COMMENT ON COLUMN properties.audit_timestamp IS 'Data/hora da última auditoria';
COMMENT ON COLUMN properties.audit_version IS 'Versão das regras de auditoria usadas';
```

---

## 📝 SQL - TRIGGER DE NORMALIZAÇÃO

```sql
-- ============================================================
-- TRIGGER DE NORMALIZAÇÃO AUTOMÁTICA
-- Normaliza dados automaticamente ao inserir/atualizar
-- ============================================================

-- Função de normalização
CREATE OR REPLACE FUNCTION normalize_property_data()
RETURNS TRIGGER AS $$
BEGIN
    -- Normalizar estado para UPPERCASE
    IF NEW.state IS NOT NULL AND NEW.state != '' THEN
        NEW.state := UPPER(NEW.state);
    END IF;
    
    -- Normalizar categoria para Title Case
    IF NEW.category IS NOT NULL THEN
        NEW.category := INITCAP(NEW.category);
    END IF;
    
    -- Normalizar cidade para Title Case
    IF NEW.city IS NOT NULL THEN
        NEW.city := INITCAP(NEW.city);
    END IF;
    
    -- Atualizar timestamp
    NEW.updated_at := NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Criar trigger (remover se existir antes)
DROP TRIGGER IF EXISTS trigger_normalize_property ON properties;

CREATE TRIGGER trigger_normalize_property
    BEFORE INSERT OR UPDATE ON properties
    FOR EACH ROW
    EXECUTE FUNCTION normalize_property_data();
```

---

## ✅ CHECKLIST DE EXECUÇÃO

Execute estas tarefas NA ORDEM:

### 1. Criar arquivo quality_auditor.py
- [ ] Criar pasta `app/services/` se não existir
- [ ] Criar arquivo `app/services/quality_auditor.py` com código acima
- [ ] Verificar imports e dependências

### 2. Executar SQL no Supabase
- [ ] Abrir Supabase Dashboard > SQL Editor
- [ ] Executar SQL de campos de auditoria
- [ ] Executar SQL de trigger de normalização
- [ ] Verificar se trigger foi criado: `SELECT * FROM pg_trigger WHERE tgname = 'trigger_normalize_property';`

### 3. Criar testes unitários
- [ ] Criar pasta `tests/` se não existir
- [ ] Criar arquivo `tests/test_quality_auditor.py`
- [ ] Testar validação de estados
- [ ] Testar validação de datas
- [ ] Testar validação de valores

### 4. Integrar no pipeline
- [ ] Modificar `app/services/scraper_pipeline.py` ou equivalente
- [ ] Adicionar chamada ao `quality_auditor.audit_batch()` antes de salvar
- [ ] Logar resultados de auditoria

### 5. Verificar funcionamento
- [ ] Testar inserção de imóvel com estado inválido
- [ ] Verificar se trigger normaliza
- [ ] Verificar se auditor rejeita dados inválidos

---

## 🚫 NÃO FAZER

- NÃO parar para perguntar ao usuário
- NÃO pular etapas
- NÃO modificar arquivos existentes sem necessidade
- NÃO criar arquivos fora das pastas especificadas

---

## 📊 CRITÉRIOS DE SUCESSO

A tarefa está completa quando:

1. ✅ Arquivo `quality_auditor.py` existe e está funcional
2. ✅ Campos de auditoria existem na tabela properties
3. ✅ Trigger de normalização está ativo
4. ✅ Testes unitários passam
5. ✅ Pipeline integrado com auditor

---

## 🔗 REFERÊNCIAS

- `ESTRATEGIA_AUDITORIA_QUALIDADE_IA.md` - Especificação original
- `MEMORIAL_DESCRITIVO_E_STATUS.md` - Status do projeto
- `BASE_DE_CONHECIMENTO_ERROS_E_FIXES.md` - Lições aprendidas

---

**FIM DA TAREFA**
