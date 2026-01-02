"""
BrazilianDateParser - Parser robusto para datas brasileiras.

Formatos suportados:
- "15/01/2025" (DD/MM/YYYY)
- "15/01/2025 às 14h" (com hora)
- "15/01/2025 14:00" (com hora:minuto)
- "15 de janeiro de 2025" (por extenso)
- "Segunda-feira, 15/01/2025" (com dia da semana)
- "2025-01-15" (ISO)
- "2025-01-15T14:00:00" (ISO com hora)
- "Encerra em 2d 14h" (countdown - calcula data futura)
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class BrazilianDateParser:
    """
    Parser de datas para formatos brasileiros.
    """
    
    # Meses em português
    MESES = {
        'janeiro': 1, 'jan': 1,
        'fevereiro': 2, 'fev': 2,
        'março': 3, 'mar': 3, 'marco': 3,
        'abril': 4, 'abr': 4,
        'maio': 5, 'mai': 5,
        'junho': 6, 'jun': 6,
        'julho': 7, 'jul': 7,
        'agosto': 8, 'ago': 8,
        'setembro': 9, 'set': 9,
        'outubro': 10, 'out': 10,
        'novembro': 11, 'nov': 11,
        'dezembro': 12, 'dez': 12,
    }
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compila os padrões regex para melhor performance."""
        
        # DD/MM/YYYY ou DD-MM-YYYY (com hora opcional)
        self.pattern_ddmmyyyy = re.compile(
            r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})'
            r'(?:\s+(?:às?\s*)?(\d{1,2})[:h](\d{0,2}))?',
            re.IGNORECASE
        )
        
        # "15 de janeiro de 2025" (com hora opcional)
        meses_pattern = '|'.join(self.MESES.keys())
        self.pattern_extenso = re.compile(
            rf'(\d{{1,2}})\s+(?:de\s+)?({meses_pattern})\s+(?:de\s+)?(\d{{4}})'
            rf'(?:\s+(?:às?\s*)?(\d{{1,2}})[:h](\d{{0,2}}))?',
            re.IGNORECASE
        )
        
        # ISO format: YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS
        self.pattern_iso = re.compile(
            r'(\d{4})-(\d{2})-(\d{2})'
            r'(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?'
        )
        
        # Countdown: "2d 14h 32m" ou "Encerra em 2 dias"
        self.pattern_countdown = re.compile(
            r'(?:encerra|termina|acaba|faltam?|restam?)\s*(?:em\s*)?'
            r'(?:(\d+)\s*d(?:ias?)?)?'
            r'(?:\s*(\d+)\s*h(?:oras?)?)?'
            r'(?:\s*(\d+)\s*m(?:in(?:utos?)?)?)?',
            re.IGNORECASE
        )
        
        # Padrão alternativo para countdown: "2d 14h"
        self.pattern_countdown_short = re.compile(
            r'(\d+)d\s*(\d+)h'
        )
    
    def parse(self, text: str) -> Optional[datetime]:
        """
        Tenta parsear uma data de um texto.
        
        Args:
            text: Texto contendo uma data
            
        Returns:
            datetime se encontrou data válida, None caso contrário
        """
        if not text or not isinstance(text, str):
            return None
        
        text = text.strip()
        
        # Tenta cada padrão em ordem de especificidade
        
        # 1. Formato ISO (mais específico)
        result = self._try_iso(text)
        if result:
            return result
        
        # 2. Formato brasileiro por extenso
        result = self._try_extenso(text)
        if result:
            return result
        
        # 3. Formato DD/MM/YYYY
        result = self._try_ddmmyyyy(text)
        if result:
            return result
        
        # 4. Countdown (menos específico)
        result = self._try_countdown(text)
        if result:
            return result
        
        return None
    
    def parse_all(self, text: str) -> List[datetime]:
        """
        Extrai todas as datas de um texto.
        
        Returns:
            Lista de datetimes encontrados
        """
        if not text:
            return []
        
        dates = []
        
        # Tenta todos os padrões
        for match in self.pattern_iso.finditer(text):
            try:
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                hour = int(match.group(4)) if match.group(4) else 0
                minute = int(match.group(5)) if match.group(5) else 0
                dates.append(datetime(year, month, day, hour, minute))
            except ValueError:
                continue
        
        for match in self.pattern_extenso.finditer(text):
            try:
                day = int(match.group(1))
                month = self.MESES.get(match.group(2).lower())
                year = int(match.group(3))
                hour = int(match.group(4)) if match.group(4) else 0
                minute = int(match.group(5)) if match.group(5) else 0
                if month:
                    dates.append(datetime(year, month, day, hour, minute))
            except ValueError:
                continue
        
        for match in self.pattern_ddmmyyyy.finditer(text):
            try:
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                hour = int(match.group(4)) if match.group(4) else 0
                minute_str = match.group(5)
                minute = int(minute_str) if minute_str else 0
                dates.append(datetime(year, month, day, hour, minute))
            except ValueError:
                continue
        
        # Remove duplicatas mantendo ordem
        seen = set()
        unique_dates = []
        for d in dates:
            if d not in seen:
                seen.add(d)
                unique_dates.append(d)
        
        return unique_dates
    
    def find_auction_dates(self, text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Encontra datas de 1º e 2º leilão em um texto.
        
        Procura por padrões como:
        - "1º Leilão: 15/01/2025" / "2º Leilão: 20/01/2025"
        - "Primeira praça: 15/01" / "Segunda praça: 20/01"
        
        Returns:
            Tupla (primeira_data, segunda_data)
        """
        first_date = None
        second_date = None
        
        # Padrões para primeiro leilão
        first_patterns = [
            r'1[ºªo]\s*(?:leilão|praça|hasta).*?(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'primeir[oa]\s*(?:leilão|praça|hasta).*?(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'1[ºªo]\s*leilão.*?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
        ]
        
        # Padrões para segundo leilão
        second_patterns = [
            r'2[ºªo]\s*(?:leilão|praça|hasta).*?(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'segund[oa]\s*(?:leilão|praça|hasta).*?(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'2[ºªo]\s*leilão.*?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
        ]
        
        for pattern in first_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                first_date = self.parse(match.group(1))
                if first_date:
                    break
        
        for pattern in second_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                second_date = self.parse(match.group(1))
                if second_date:
                    break
        
        return first_date, second_date
    
    def _try_iso(self, text: str) -> Optional[datetime]:
        """Tenta parsear formato ISO."""
        match = self.pattern_iso.search(text)
        if match:
            try:
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                hour = int(match.group(4)) if match.group(4) else 0
                minute = int(match.group(5)) if match.group(5) else 0
                return datetime(year, month, day, hour, minute)
            except ValueError:
                pass
        return None
    
    def _try_extenso(self, text: str) -> Optional[datetime]:
        """Tenta parsear formato por extenso."""
        match = self.pattern_extenso.search(text)
        if match:
            try:
                day = int(match.group(1))
                month = self.MESES.get(match.group(2).lower())
                year = int(match.group(3))
                hour = int(match.group(4)) if match.group(4) else 0
                minute = int(match.group(5)) if match.group(5) else 0
                if month:
                    return datetime(year, month, day, hour, minute)
            except ValueError:
                pass
        return None
    
    def _try_ddmmyyyy(self, text: str) -> Optional[datetime]:
        """Tenta parsear formato DD/MM/YYYY."""
        match = self.pattern_ddmmyyyy.search(text)
        if match:
            try:
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                hour = int(match.group(4)) if match.group(4) else 0
                minute_str = match.group(5)
                minute = int(minute_str) if minute_str else 0
                return datetime(year, month, day, hour, minute)
            except ValueError:
                pass
        return None
    
    def _try_countdown(self, text: str) -> Optional[datetime]:
        """Tenta parsear countdown e calcular data futura."""
        match = self.pattern_countdown.search(text)
        if not match:
            match = self.pattern_countdown_short.search(text)
        
        if match:
            try:
                days = int(match.group(1)) if match.group(1) else 0
                hours = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 0
                minutes = int(match.group(3)) if len(match.groups()) > 2 and match.group(3) else 0
                
                if days or hours or minutes:
                    return datetime.now() + timedelta(days=days, hours=hours, minutes=minutes)
            except (ValueError, IndexError):
                pass
        
        return None


# Instância global para uso conveniente
_parser = BrazilianDateParser()

def parse_brazilian_date(text: str) -> Optional[datetime]:
    """Função de conveniência para parsear uma data brasileira."""
    return _parser.parse(text)

def parse_all_dates(text: str) -> List[datetime]:
    """Função de conveniência para extrair todas as datas."""
    return _parser.parse_all(text)

def find_auction_dates(text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Função de conveniência para encontrar datas de leilão."""
    return _parser.find_auction_dates(text)

