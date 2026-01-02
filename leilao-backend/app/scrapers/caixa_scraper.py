"""
Scraper especializado para imóveis da Caixa Econômica Federal.

A Caixa disponibiliza um CSV público que é atualizado diariamente.
URL: https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp

Este scraper:
1. Baixa o CSV da Caixa
2. Parseia e normaliza os dados
3. Aplica deduplicação (Caixa tem prioridade)
4. Salva no Supabase
"""

import csv
import io
import re
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import httpx

from app.utils.normalizer import (
    normalize_category,
    normalize_state,
    normalize_city,
    normalize_money
)

logger = logging.getLogger(__name__)

# URL do CSV da Caixa
CAIXA_CSV_URL = "https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp"

# Mapeamento de colunas do CSV da Caixa
# O CSV da Caixa tem colunas específicas que precisam ser mapeadas
CAIXA_COLUMN_MAP = {
    'N° do imóvel': 'external_id',
    'UF': 'state',
    'Cidade': 'city',
    'Bairro': 'neighborhood',
    'Endereço': 'address',
    'Preço': 'first_auction_value',
    'Valor de avaliação': 'evaluation_value',
    'Desconto': 'discount_percentage',
    'Descrição': 'description',
    'Modalidade de venda': 'auction_type',
    'Link de acesso': 'source_url',
    # Colunas alternativas (o formato pode variar)
    'Número do Imóvel': 'external_id',
    'Estado': 'state',
    'Município': 'city',
    'Valor de Venda': 'first_auction_value',
    'Valor Avaliação': 'evaluation_value',
    'Link': 'source_url',
}

# Mapeamento de modalidades da Caixa
MODALIDADE_MAP = {
    'Licitação Aberta': 'Licitação',
    'Licitação Fechada': 'Licitação',
    'Venda Online': 'Venda Direta',
    'Venda Direta Online': 'Venda Direta',
    'Leilão': 'Leilão',
    'Leilão SFI': 'Leilão',
    '1º Leilão SFI': 'Leilão',
    '2º Leilão SFI': 'Leilão',
}

@dataclass
class CaixaProperty:
    """Representa um imóvel da Caixa."""
    external_id: str
    title: str
    category: str
    auction_type: str
    state: str
    city: str
    neighborhood: Optional[str]
    address: Optional[str]
    description: Optional[str]
    evaluation_value: Optional[float]
    first_auction_value: Optional[float]
    discount_percentage: Optional[float]
    source_url: str
    source: str = "caixa"
    auctioneer_name: str = "Caixa Econômica Federal"


class CaixaScraper:
    """
    Scraper para imóveis da Caixa Econômica Federal.
    """
    
    def __init__(self):
        self.session = None
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Executa o scraping completo da Caixa.
        
        Returns:
            Lista de imóveis extraídos e normalizados
        """
        logger.info("Iniciando scraping da Caixa Econômica Federal")
        
        # Baixa o CSV
        csv_content = await self._download_csv()
        
        if not csv_content:
            logger.error("Falha ao baixar CSV da Caixa")
            return []
        
        # Parseia o CSV
        properties = self._parse_csv(csv_content)
        
        logger.info(f"Caixa: {len(properties)} imóveis extraídos")
        
        return properties
    
    async def _download_csv(self) -> Optional[str]:
        """
        Baixa o CSV da Caixa.
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Headers que simulam navegador
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                }
                
                logger.info(f"Baixando CSV de {CAIXA_CSV_URL}")
                
                response = await client.get(CAIXA_CSV_URL, headers=headers, follow_redirects=True)
                
                if response.status_code == 200:
                    # O CSV da Caixa usa encoding ISO-8859-1 (Latin-1)
                    content = response.content.decode('iso-8859-1', errors='replace')
                    logger.info(f"CSV baixado: {len(content)} caracteres")
                    return content
                else:
                    logger.error(f"Erro HTTP {response.status_code} ao baixar CSV")
                    return None
                    
        except Exception as e:
            logger.error(f"Erro ao baixar CSV da Caixa: {e}")
            return None
    
    def _parse_csv(self, csv_content: str) -> List[Dict[str, Any]]:
        """
        Parseia o conteúdo do CSV.
        Suporta CSV com cabeçalhos (DictReader) e sem cabeçalhos (posicional).
        """
        properties = []
        
        try:
            # Tenta diferentes delimitadores
            for delimiter in [';', ',', '\t']:
                try:
                    # Primeiro tenta com cabeçalhos (DictReader)
                    reader = csv.DictReader(
                        io.StringIO(csv_content),
                        delimiter=delimiter
                    )
                    
                    # Tenta ler primeira linha para verificar se o delimitador está correto
                    rows = list(reader)
                    
                    if rows and len(rows[0]) > 3:
                        logger.info(f"CSV parseado com delimitador '{delimiter}' (com cabeçalhos): {len(rows)} linhas")
                        
                        for row in rows:
                            prop = self._parse_row(row)
                            if prop:
                                properties.append(prop)
                        
                        break
                        
                except Exception as e:
                    # Se falhar, tenta parsing posicional (sem cabeçalhos)
                    try:
                        reader = csv.reader(
                            io.StringIO(csv_content),
                            delimiter=delimiter
                        )
                        
                        rows = list(reader)
                        
                        # Verifica se tem pelo menos 11 colunas (formato esperado da Caixa)
                        if rows and len(rows) > 0 and len(rows[0]) >= 11:
                            logger.info(f"CSV parseado com delimitador '{delimiter}' (posicional): {len(rows)} linhas")
                            
                            # Pula primeira linha se parecer cabeçalho
                            start_idx = 0
                            if rows[0][0] and not rows[0][0].isdigit():
                                start_idx = 1
                            
                            for row in rows[start_idx:]:
                                prop = self._parse_row_positional(row)
                                if prop:
                                    properties.append(prop)
                            
                            break
                    except Exception as e2:
                        continue
            
            if not properties:
                logger.warning("Nenhum imóvel extraído do CSV")
                
        except Exception as e:
            logger.error(f"Erro ao parsear CSV: {e}")
        
        return properties
    
    def _parse_row(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Parseia uma linha do CSV e retorna um dicionário normalizado.
        """
        try:
            # Mapeia colunas
            mapped = {}
            for csv_col, prop_col in CAIXA_COLUMN_MAP.items():
                if csv_col in row and row[csv_col]:
                    mapped[prop_col] = row[csv_col].strip()
            
            # Validação mínima
            if not mapped.get('external_id') and not mapped.get('source_url'):
                return None
            
            # Gera ID único
            external_id = mapped.get('external_id', '')
            source_url = mapped.get('source_url', '')
            
            if not external_id:
                # Gera ID a partir da URL
                external_id = hashlib.md5(source_url.encode()).hexdigest()[:12]
            
            prop_id = f"caixa-{external_id}"
            
            # Normaliza estado
            state = normalize_state(mapped.get('state', ''))
            
            # Normaliza cidade
            city = normalize_city(mapped.get('city', ''))
            
            # Detecta categoria a partir da descrição
            description = mapped.get('description', '')
            category = self._detect_category(description)
            
            # Normaliza valores monetários
            evaluation_value = normalize_money(mapped.get('evaluation_value', ''))
            first_auction_value = normalize_money(mapped.get('first_auction_value', ''))
            
            # Calcula desconto se não vier no CSV
            discount = None
            discount_str = mapped.get('discount_percentage', '')
            if discount_str:
                discount = self._parse_discount(discount_str)
            elif evaluation_value and first_auction_value and evaluation_value > 0:
                discount = round((1 - first_auction_value / evaluation_value) * 100, 2)
            
            # Mapeia modalidade
            auction_type = mapped.get('auction_type', 'Venda Direta')
            auction_type = MODALIDADE_MAP.get(auction_type, auction_type)
            
            # Gera título
            title = self._generate_title(category, city, state, mapped.get('neighborhood'))
            
            # Monta dicionário final
            return {
                'id': prop_id,
                'external_id': external_id,
                'title': title,
                'category': category,
                'auction_type': auction_type,
                'state': state,
                'city': city,
                'neighborhood': mapped.get('neighborhood'),
                'address': mapped.get('address'),
                'description': description,
                'evaluation_value': evaluation_value,
                'first_auction_value': first_auction_value,
                'discount_percentage': discount,
                'source_url': source_url or f"https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel={external_id}",
                'source': 'caixa',
                'auctioneer_id': 'caixa',
                'auctioneer_name': 'Caixa Econômica Federal',
                'auctioneer_url': 'https://venda-imoveis.caixa.gov.br',
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.warning(f"Erro ao parsear linha: {e}")
            return None
    
    def _parse_row_positional(self, row: List[str]) -> Optional[Dict[str, Any]]:
        """
        Parseia uma linha do CSV usando posições fixas (quando não há cabeçalhos).
        
        Formato esperado (11 colunas):
        0: N° do imóvel
        1: UF
        2: Cidade
        3: Bairro
        4: Endereço
        5: Preço
        6: Valor de avaliação
        7: Desconto
        8: Descrição
        9: Modalidade de venda
        10: Link de acesso
        """
        try:
            # Limpar valores (remover espaços extras)
            row = [col.strip() if isinstance(col, str) else str(col).strip() if col else '' for col in row]
            
            # Garantir que temos pelo menos 11 colunas
            while len(row) < 11:
                row.append('')
            
            # Mapear colunas posicionais
            external_id = row[0] if len(row) > 0 else ''
            state = row[1] if len(row) > 1 else ''
            city = row[2] if len(row) > 2 else ''
            neighborhood = row[3] if len(row) > 3 else ''
            address = row[4] if len(row) > 4 else ''
            first_auction_value_str = row[5] if len(row) > 5 else ''
            evaluation_value_str = row[6] if len(row) > 6 else ''
            discount_str = row[7] if len(row) > 7 else ''
            description = row[8] if len(row) > 8 else ''
            auction_type = row[9] if len(row) > 9 else ''
            source_url = row[10] if len(row) > 10 else ''  # <-- IMPORTANTE: Link de acesso
            
            # Validação mínima
            if not external_id and not source_url:
                return None
            
            # Gera ID único
            if not external_id:
                # Gera ID a partir da URL
                external_id = hashlib.md5(source_url.encode()).hexdigest()[:12]
            
            prop_id = f"caixa-{external_id}"
            
            # Normaliza estado
            state = normalize_state(state)
            
            # Normaliza cidade
            city = normalize_city(city)
            
            # Detecta categoria a partir da descrição
            category = self._detect_category(description)
            
            # Normaliza valores monetários
            evaluation_value = normalize_money(evaluation_value_str)
            first_auction_value = normalize_money(first_auction_value_str)
            
            # Calcula desconto se não vier no CSV
            discount = None
            if discount_str:
                discount = self._parse_discount(discount_str)
            elif evaluation_value and first_auction_value and evaluation_value > 0:
                discount = round((1 - first_auction_value / evaluation_value) * 100, 2)
            
            # Mapeia modalidade
            auction_type = MODALIDADE_MAP.get(auction_type, auction_type)
            
            # Gera título
            title = self._generate_title(category, city, state, neighborhood)
            
            # Garante source_url (gera se não vier)
            if not source_url:
                source_url = f"https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel={external_id}"
            
            # Monta dicionário final
            return {
                'id': prop_id,
                'external_id': external_id,
                'title': title,
                'category': category,
                'auction_type': auction_type,
                'state': state,
                'city': city,
                'neighborhood': neighborhood,
                'address': address,
                'description': description,
                'evaluation_value': evaluation_value,
                'first_auction_value': first_auction_value,
                'discount_percentage': discount,
                'source_url': source_url,  # <-- Garantido
                'source': 'caixa',
                'auctioneer_id': 'caixa',
                'auctioneer_name': 'Caixa Econômica Federal',
                'auctioneer_url': 'https://venda-imoveis.caixa.gov.br',
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.warning(f"Erro ao parsear linha posicional: {e}")
            return None
    
    def _detect_category(self, description: str) -> str:
        """
        Detecta a categoria do imóvel a partir da descrição.
        """
        if not description:
            return "Outros"
        
        desc_lower = description.lower()
        
        if any(term in desc_lower for term in ['apartamento', 'apto', 'ap.', 'cobertura', 'flat', 'kitnet']):
            return "Apartamento"
        elif any(term in desc_lower for term in ['casa', 'sobrado', 'residência', 'residencia', 'chalé', 'chale']):
            return "Casa"
        elif any(term in desc_lower for term in ['terreno', 'lote', 'gleba', 'área', 'area', 'chácara', 'chacara', 'sítio', 'sitio', 'fazenda']):
            return "Terreno"
        elif any(term in desc_lower for term in ['comercial', 'sala', 'loja', 'galpão', 'galpao', 'prédio', 'predio', 'escritório', 'escritorio']):
            return "Comercial"
        
        return "Outros"
    
    def _generate_title(
        self,
        category: str,
        city: str,
        state: str,
        neighborhood: Optional[str]
    ) -> str:
        """
        Gera um título descritivo para o imóvel.
        """
        parts = [category]
        
        if neighborhood:
            parts.append(f"em {neighborhood}")
        
        if city:
            parts.append(f"- {city}")
        
        if state:
            parts.append(f"/{state}")
        
        return ' '.join(parts)
    
    def _parse_discount(self, discount_str: str) -> Optional[float]:
        """
        Parseia string de desconto para float.
        """
        if not discount_str:
            return None
        
        # Remove % e outros caracteres
        clean = re.sub(r'[^\d,.]', '', discount_str)
        clean = clean.replace(',', '.')
        
        try:
            return float(clean)
        except ValueError:
            return None


async def scrape_caixa() -> List[Dict[str, Any]]:
    """
    Função de conveniência para executar o scraping da Caixa.
    """
    scraper = CaixaScraper()
    return await scraper.scrape()

