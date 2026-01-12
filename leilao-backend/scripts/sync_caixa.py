"""
Script para sincronizar imóveis da Caixa Econômica Federal.

Este script:
1. Baixa o CSV diário da Caixa (https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp)
2. Parseia e normaliza os dados para nosso schema
3. Faz upsert no Supabase com deduplicação
4. Prioriza dados da Caixa sobre leiloeiros (em caso de duplicata)

Execução recomendada: 2x/dia (6h e 18h BRT) via GitHub Actions
"""

import os
import sys
import csv
import io
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse, parse_qs

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import httpx
import psycopg
from psycopg.rows import dict_row

from app.models.property import Property, PropertyCreate, PropertyCategory, AuctionType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# URL alternativa que funciona (por estado)
CAIXA_CSV_URL_TEMPLATE = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{}.csv"
# URL antiga (bloqueada por proteção anti-bot)
CAIXA_CSV_URL_OLD = "https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp"
CAIXA_BASE_URL = "https://venda-imoveis.caixa.gov.br"
DATABASE_URL = os.getenv("DATABASE_URL")
CAIXA_AUCTIONEER_ID = "caixa_federal"
CAIXA_AUCTIONEER_NAME = "Caixa Econômica Federal"

# Lista de estados brasileiros
ESTADOS_BRASIL = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
    'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
    'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
]


def download_caixa_csv_por_estado(estado: str) -> Optional[str]:
    """
    Baixa o CSV da Caixa para um estado específico usando a URL alternativa.
    
    Args:
        estado: UF do estado (ex: 'SP', 'RJ')
    
    Returns:
        Conteúdo do CSV como string, ou None em caso de erro
    """
    try:
        url = CAIXA_CSV_URL_TEMPLATE.format(estado)
        logger.info(f"Baixando CSV da Caixa para {estado}: {url}")
        
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://venda-imoveis.caixa.gov.br/',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"Erro ao baixar CSV de {estado}: Status {response.status_code}")
                return None
            
            # Decodificar usando latin-1 (encoding do CSV da Caixa)
            try:
                content = response.content.decode('latin-1')
            except UnicodeDecodeError:
                content = response.content.decode('iso-8859-1', errors='ignore')
            
            # Verificar se é HTML (proteção anti-bot)
            if '<html' in content.lower() or 'captcha' in content.lower() or 'bot manager' in content.lower():
                logger.warning(f"Resposta é HTML para {estado} (proteção anti-bot)")
                return None
            
            # Verificar se parece CSV (tem cabeçalho esperado)
            if 'Nº do imóvel' not in content and 'N do imvel' not in content:
                logger.warning(f"Resposta não parece ser CSV válido para {estado}")
                return None
            
            logger.info(f"CSV de {estado} baixado com sucesso ({len(content)} caracteres)")
            return content
            
    except Exception as e:
        logger.error(f"Erro ao baixar CSV de {estado}: {e}")
        return None


def download_caixa_csv() -> Optional[str]:
    """
    Baixa o CSV da Caixa de todos os estados e concatena.
    Usa a URL alternativa que funciona: listaweb/Lista_imoveis_{UF}.csv
    Adiciona delay de 5 segundos entre cada estado para evitar bloqueio.
    
    Returns:
        Conteúdo do CSV concatenado como string, ou None em caso de erro
    """
    import time
    
    logger.info("Baixando CSVs da Caixa por estado (método alternativo)...")
    
    all_content = []
    estados_com_sucesso = 0
    estados_com_erro = 0
    
    for i, estado in enumerate(ESTADOS_BRASIL):
        # Delay de 5 segundos entre requisições (exceto a primeira)
        if i > 0:
            logger.info(f"Aguardando 5 segundos antes do próximo estado...")
            time.sleep(5)
        
        content = download_caixa_csv_por_estado(estado)
        if content:
            all_content.append((estado, content))
            estados_com_sucesso += 1
        else:
            estados_com_erro += 1
            logger.warning(f"Falha ao baixar CSV de {estado}")
    
    if not all_content:
        logger.error("Nenhum CSV foi baixado com sucesso")
        return None
    
    logger.info(f"CSVs baixados: {estados_com_sucesso} sucesso, {estados_com_erro} erros")
    
    # Concatenar todos os CSVs (pular cabeçalhos duplicados)
    # O primeiro CSV mantém o cabeçalho completo, os demais só os dados
    final_content = []
    header_written = False
    
    for estado, content in all_content:
        lines = content.split('\n')
        # Processar linha por linha para encontrar cabeçalho e dados
        data_started = False
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Detectar linha de cabeçalho de dados (linha 3 do arquivo original)
            # Cabeçalho contém: "Nº do imóvel" ou "N do imvel" e "UF" e "Cidade"
            line_upper = line_stripped.upper()
            if (('Nº DO IMÓVEL' in line_upper or 'N DO IMVEL' in line_upper or 'NUMERO' in line_upper) 
                and 'UF' in line_upper and 'CIDADE' in line_upper):
                if not header_written:
                    final_content.append(line_stripped)
                    header_written = True
                data_started = True
                continue
            
            # Pular linha de título
            if 'Lista de Imóveis' in line_stripped or 'Lista de Imveis' in line_stripped or 'Data de geração' in line_stripped:
                continue
            
            # Se já passou do cabeçalho, adicionar dados
            if data_started and line_stripped:
                final_content.append(line_stripped)
    
    result = '\n'.join(final_content)
    logger.info(f"CSV consolidado criado ({len(result)} caracteres, {len(final_content)-1} linhas de dados)")
    return result


def download_caixa_csv_with_playwright() -> Optional[str]:
    """
    Baixa o CSV da Caixa usando Playwright para contornar proteção anti-bot.
    
    Returns:
        Conteúdo do CSV como string, ou None em caso de erro
    """
    try:
        from playwright.sync_api import sync_playwright
        
        logger.info("Iniciando download com Playwright...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-BR',
            )
            
            page = context.new_page()
            
            # Injetar scripts de stealth
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            """)
            
            # Navegar e aguardar
            page.goto(CAIXA_CSV_URL, wait_until='networkidle', timeout=60000)
            
            # Aguardar um pouco para garantir que o conteúdo carregou
            page.wait_for_timeout(3000)
            
            # Obter conteúdo
            content = page.content()
            
            # Verificar se é HTML (ainda bloqueado)
            if '<html' in content.lower() or 'captcha' in content.lower():
                logger.error("Ainda recebendo HTML/CAPTCHA mesmo com Playwright")
                browser.close()
                return None
            
            browser.close()
            
            logger.info(f"CSV baixado com Playwright ({len(content)} caracteres)")
            return content
            
    except ImportError:
        logger.error("Playwright não está instalado. Instale com: pip install playwright && playwright install chromium")
        return None
    except Exception as e:
        logger.error(f"Erro ao baixar CSV com Playwright: {e}")
        logger.error(traceback.format_exc())
        return None


def parse_csv_row(row: Dict[str, str]) -> Optional[Dict]:
    """
    Parseia uma linha do CSV da Caixa e converte para nosso formato.
    
    O formato esperado do CSV (segundo o documento):
    UF,CIDADE,BAIRRO,ENDERECO,PRECO_VENDA,VALOR_AVALIACAO,DESCONTO,AREA,TIPO,LINK
    
    Args:
        row: Dicionário com os campos do CSV
        
    Returns:
        Dicionário com dados normalizados ou None se inválido
    """
    try:
        # Filtrar chaves None e normalizar chaves do CSV (pode variar entre maiúsculas/minúsculas)
        # Normalizar chaves do CSV (formato da Caixa pode ter espaços e acentos)
        row_normalized = {}
        for k, v in row.items():
            if k is not None:  # Ignorar chaves None
                # Normalizar chave: remover espaços, normalizar acentos
                key = k.strip() if isinstance(k, str) else str(k).strip()
                # Mapear nomes de colunas possíveis
                key_upper = key.upper()
                if 'Nº' in key or 'N' in key or 'NÚMERO' in key_upper or 'NUMERO' in key_upper:
                    key = 'NUMERO_IMOVEL'
                elif 'UF' in key_upper:
                    key = 'UF'
                elif 'CIDADE' in key_upper:
                    key = 'CIDADE'
                elif 'BAIRRO' in key_upper:
                    key = 'BAIRRO'
                elif 'ENDEREÇO' in key_upper or 'ENDERECO' in key_upper:
                    key = 'ENDERECO'
                elif 'PREÇO' in key_upper or 'PRECO' in key_upper:
                    key = 'PRECO'
                elif 'VALOR DE AVALIAÇÃO' in key_upper or 'VALOR DE AVALIACAO' in key_upper or 'AVALIAÇÃO' in key_upper:
                    key = 'VALOR_AVALIACAO'
                elif 'DESCONTO' in key_upper:
                    key = 'DESCONTO'
                elif 'DESCRIÇÃO' in key_upper or 'DESCRICAO' in key_upper:
                    key = 'DESCRICAO'
                elif 'LINK' in key_upper:
                    key = 'LINK'
                else:
                    key = key_upper.replace(' ', '_')
                
                value = v.strip() if v and isinstance(v, str) else (str(v).strip() if v else '')
                row_normalized[key] = value
        
        # Extrair campos básicos
        uf = row_normalized.get('UF', '').strip()
        cidade = row_normalized.get('CIDADE', '').strip()
        bairro = row_normalized.get('BAIRRO', '').strip()
        endereco = row_normalized.get('ENDERECO', '').strip()
        numero_imovel = row_normalized.get('NUMERO_IMOVEL', '').strip()
        
        if not uf or not cidade:
            logger.debug(f"Linha ignorada: sem UF ou Cidade")
            return None
        
        # Valores monetários (formato brasileiro: 398.873,99)
        try:
            preco_str = row_normalized.get('PRECO', '').replace(' ', '')
            if preco_str:
                preco_venda = float(preco_str.replace('.', '').replace(',', '.'))
            else:
                preco_venda = None
        except (ValueError, AttributeError):
            preco_venda = None
        
        try:
            valor_avaliacao_str = row_normalized.get('VALOR_AVALIACAO', '').replace(' ', '')
            if valor_avaliacao_str:
                valor_avaliacao = float(valor_avaliacao_str.replace('.', '').replace(',', '.'))
            else:
                valor_avaliacao = None
        except (ValueError, AttributeError):
            valor_avaliacao = None
        
        # Desconto
        desconto = None
        if row_normalized.get('DESCONTO'):
            try:
                desconto = float(row_normalized['DESCONTO'].replace('%', '').replace(',', '.'))
            except (ValueError, AttributeError):
                pass
        
        # Calcular desconto se não fornecido
        if desconto is None and valor_avaliacao and preco_venda and valor_avaliacao > 0:
            desconto = round((1 - preco_venda / valor_avaliacao) * 100, 2)
        
        # Área
        area = None
        if row_normalized.get('AREA'):
            try:
                area = float(row_normalized['AREA'].replace(',', '.'))
            except (ValueError, AttributeError):
                pass
        
        # Tipo/Categoria (extrair da descrição)
        descricao = row_normalized.get('DESCRICAO', '').lower()
        category = PropertyCategory.OUTRO
        if 'apartamento' in descricao or 'apto' in descricao:
            category = PropertyCategory.APARTAMENTO
        elif 'casa' in descricao:
            category = PropertyCategory.CASA
        elif 'terreno' in descricao:
            category = PropertyCategory.TERRENO
        elif 'comercial' in descricao or 'loja' in descricao or 'sala' in descricao:
            category = PropertyCategory.COMERCIAL
        
        # Link/URL
        link = row_normalized.get('LINK', '').strip()
        if link and not link.startswith('http'):
            link = urljoin(CAIXA_BASE_URL, link)
        
        # Tentar extrair número do imóvel do link se não tiver no campo
        if not numero_imovel and link:
            try:
                parsed = urlparse(link)
                params = parse_qs(parsed.query)
                if 'hdnimovel' in params:
                    numero_imovel = params['hdnimovel'][0]
                elif 'imovel' in params:
                    numero_imovel = params['imovel'][0]
            except Exception:
                pass
        
        # Criar ID único baseado no número do imóvel ou endereço
        if numero_imovel:
            prop_id = f"caixa-{numero_imovel.strip()}"
        else:
            # Fallback: usar hash do endereço
            import hashlib
            address_hash = hashlib.md5(f"{uf}{cidade}{endereco}".encode()).hexdigest()[:12]
            prop_id = f"caixa-{address_hash}"
        
        # Montar título
        title = endereco[:100] if endereco else f"{category.value} em {cidade}, {uf}"
        
        return {
            'id': prop_id,
            'title': title,
            'address': endereco or None,
            'city': cidade,
            'state': uf.upper()[:2],
            'neighborhood': bairro if bairro else None,
            'category': category,
            'auction_type': AuctionType.EXTRAJUDICIAL,  # Caixa é geralmente extrajudicial
            'evaluation_value': valor_avaliacao,
            'first_auction_value': preco_venda,
            'second_auction_value': preco_venda,
            'discount_percentage': desconto,
            'area_total': area,
            'source_url': link if link else f"{CAIXA_BASE_URL}/sistema/detalhe-imovel.asp?hdnimovel={numero_imovel}" if numero_imovel else None,
            'auctioneer_id': CAIXA_AUCTIONEER_ID,
            'auctioneer_name': CAIXA_AUCTIONEER_NAME,
            'auctioneer_url': CAIXA_BASE_URL,
            'source': 'caixa',
            'accepts_financing': True,  # Caixa geralmente aceita
            'accepts_fgts': True,  # Caixa aceita FGTS
        }
        
    except Exception as e:
        logger.error(f"Erro ao parsear linha do CSV: {e}")
        logger.error(traceback.format_exc())
        return None


def ensure_caixa_auctioneer_exists():
    """Garante que a entrada da Caixa existe na tabela auctioneers."""
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Verificar se existe
                cur.execute(
                    "SELECT id FROM auctioneers WHERE id = %s",
                    (CAIXA_AUCTIONEER_ID,)
                )
                if cur.fetchone():
                    logger.info(f"Leiloeiro {CAIXA_AUCTIONEER_ID} já existe")
                    return
                
                # Criar entrada
                cur.execute(
                    """
                    INSERT INTO auctioneers (id, name, website, is_active, scrape_status)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        CAIXA_AUCTIONEER_ID,
                        CAIXA_AUCTIONEER_NAME,
                        CAIXA_BASE_URL,
                        True,
                        'success'
                    )
                )
                conn.commit()
                logger.info(f"Leiloeiro {CAIXA_AUCTIONEER_ID} criado")
                
    except Exception as e:
        logger.error(f"Erro ao criar leiloeiro Caixa: {e}")
        logger.error(traceback.format_exc())


def deduplicate_with_caixa_priority(property_data: Dict) -> Optional[str]:
    """
    Verifica duplicatas e retorna o ID do imóvel original se existir.
    Caixa tem prioridade sobre outros leiloeiros.
    
    Args:
        property_data: Dados do imóvel
        
    Returns:
        ID do imóvel original se for duplicata, None caso contrário
    """
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Buscar por endereço normalizado ou dedup_key
                # Se já existe um imóvel da Caixa com mesmo ID, é atualização
                cur.execute(
                    "SELECT id, auctioneer_id, is_duplicate FROM properties WHERE id = %s",
                    (property_data['id'],)
                )
                existing = cur.fetchone()
                
                if existing:
                    # Se já existe e é da Caixa, permitir atualização
                    if existing['auctioneer_id'] == CAIXA_AUCTIONEER_ID:
                        return None  # Não é duplicata, é atualização
                    else:
                        # Existe de outro leiloeiro com mesmo ID - isso não deveria acontecer,
                        # mas se acontecer, manter a Caixa (mais recente)
                        logger.warning(f"Conflito: ID {property_data['id']} já existe de {existing['auctioneer_id']}. Caixa terá prioridade.")
                        # Não retornar original_id, deixar o upsert sobrescrever
                        return None
                
                # Buscar por dedup_key (endereço normalizado)
                if property_data.get('address'):
                    import re
                    # Normalizar endereço para deduplicação
                    normalized_addr = re.sub(r'[^\w\s]', '', property_data['address'].lower())
                    normalized_addr = re.sub(r'\s+', ' ', normalized_addr).strip()
                    
                    cur.execute(
                        """
                        SELECT id, auctioneer_id, is_duplicate 
                        FROM properties 
                        WHERE dedup_key = %s 
                          AND city = %s 
                          AND state = %s
                        """,
                        (normalized_addr, property_data['city'], property_data['state'])
                    )
                    similar = cur.fetchone()
                    
                    if similar:
                        # Se encontrou similar e NÃO é da Caixa, marcar o similar como duplicata da Caixa
                        if similar['auctioneer_id'] != CAIXA_AUCTIONEER_ID:
                            logger.info(f"Marcando {similar['id']} ({similar['auctioneer_id']}) como duplicata de {property_data['id']} (prioridade Caixa)")
                            cur.execute(
                                "UPDATE properties SET is_duplicate = TRUE, original_id = %s WHERE id = %s",
                                (property_data['id'], similar['id'])
                            )
                            conn.commit()
                            return None  # Permite inserir/atualizar a propriedade da Caixa
                        else:
                            # É duplicata dentro da própria Caixa (pouco provável mas possível)
                            # Retornar o ID existente para evitar duplicação
                            logger.debug(f"Imóvel {property_data['id']} é duplicata interna da Caixa de {similar['id']}")
                            return similar['id']
                
                return None
                
    except Exception as e:
        logger.error(f"Erro na deduplicação: {e}")
        logger.error(traceback.format_exc())
        return None


def upsert_property(property_data: Dict):
    """
    Faz upsert de um imóvel no banco de dados.
    
    Args:
        property_data: Dados do imóvel já parseados
    """
    try:
        # Verificar deduplicação
        original_id = deduplicate_with_caixa_priority(property_data)
        if original_id and original_id != property_data['id']:
            logger.debug(f"Imóvel {property_data['id']} é duplicata de {original_id}, pulando")
            return False
        
        # Preparar dados para inserção
        now = datetime.utcnow()
        
        # Criar dedup_key
        import re
        address = property_data.get('address') or ''
        normalized_addr = re.sub(r'[^\w\s]', '', address.lower())
        normalized_addr = re.sub(r'\s+', ' ', normalized_addr).strip()
        dedup_key = normalized_addr if normalized_addr else property_data['id']
        
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Verificar se já existe
                cur.execute("SELECT id FROM properties WHERE id = %s", (property_data['id'],))
                exists = cur.fetchone()
                
                if exists:
                    # UPDATE
                    cur.execute(
                        """
                        UPDATE properties SET
                            title = %s,
                            address = %s,
                            city = %s,
                            state = %s,
                            neighborhood = %s,
                            category = %s,
                            auction_type = %s,
                            evaluation_value = %s,
                            first_auction_value = %s,
                            second_auction_value = %s,
                            discount_percentage = %s,
                            area_total = %s,
                            source_url = %s,
                            auctioneer_id = %s,
                            auctioneer_name = %s,
                            auctioneer_url = %s,
                            source = %s,
                            accepts_financing = %s,
                            accepts_fgts = %s,
                            dedup_key = %s,
                            updated_at = %s,
                            last_seen_at = %s,
                            is_duplicate = FALSE,
                            is_active = TRUE
                        WHERE id = %s
                        """,
                        (
                            property_data['title'],
                            property_data.get('address'),
                            property_data['city'],
                            property_data['state'],
                            property_data.get('neighborhood'),
                            property_data['category'].value,
                            property_data['auction_type'].value,
                            property_data.get('evaluation_value'),
                            property_data.get('first_auction_value'),
                            property_data.get('second_auction_value'),
                            property_data.get('discount_percentage'),
                            property_data.get('area_total'),
                            property_data.get('source_url'),
                            property_data['auctioneer_id'],
                            property_data['auctioneer_name'],
                            property_data.get('auctioneer_url'),
                            property_data.get('source'),
                            property_data.get('accepts_financing'),
                            property_data.get('accepts_fgts'),
                            dedup_key,
                            now,
                            now,
                            property_data['id']
                        )
                    )
                else:
                    # INSERT
                    cur.execute(
                        """
                        INSERT INTO properties (
                            id, title, address, city, state, neighborhood,
                            category, auction_type, evaluation_value,
                            first_auction_value, second_auction_value, discount_percentage,
                            area_total, source_url, auctioneer_id, auctioneer_name,
                            auctioneer_url, source, accepts_financing, accepts_fgts,
                            dedup_key, created_at, updated_at, last_seen_at,
                            is_duplicate, is_active
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s
                        )
                        """,
                        (
                            property_data['id'],
                            property_data['title'],
                            property_data.get('address'),
                            property_data['city'],
                            property_data['state'],
                            property_data.get('neighborhood'),
                            property_data['category'].value,
                            property_data['auction_type'].value,
                            property_data.get('evaluation_value'),
                            property_data.get('first_auction_value'),
                            property_data.get('second_auction_value'),
                            property_data.get('discount_percentage'),
                            property_data.get('area_total'),
                            property_data.get('source_url'),
                            property_data['auctioneer_id'],
                            property_data['auctioneer_name'],
                            property_data.get('auctioneer_url'),
                            property_data.get('source'),
                            property_data.get('accepts_financing'),
                            property_data.get('accepts_fgts'),
                            dedup_key,
                            now,
                            now,
                            now,
                            False,
                            True
                        )
                    )
                
                conn.commit()
                return True
                
    except Exception as e:
        logger.error(f"Erro ao fazer upsert do imóvel {property_data.get('id')}: {e}")
        logger.error(traceback.format_exc())
        return False


def sync_caixa() -> Dict:
    """
    Função principal que executa toda a sincronização.
    
    Returns:
        Dicionário com estatísticas da sincronização
    """
    stats = {
        'started_at': datetime.utcnow().isoformat(),
        'csv_downloaded': False,
        'rows_parsed': 0,
        'rows_valid': 0,
        'rows_inserted': 0,
        'rows_updated': 0,
        'rows_failed': 0,
        'errors': []
    }
    
    try:
        # 1. Garantir que o leiloeiro Caixa existe
        ensure_caixa_auctioneer_exists()
        
        # 2. Baixar CSV
        csv_content = download_caixa_csv()
        if not csv_content:
            stats['errors'].append("Falha ao baixar CSV")
            return stats
        
        stats['csv_downloaded'] = True
        
        # 3. Parsear CSV (formato da Caixa usa ';' como delimitador e latin-1)
        # Processar: encontrar cabeçalho e dados
        lines = csv_content.split('\n')
        data_lines = []
        header_found = False
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Detectar linha de cabeçalho de dados
            # Cabeçalho contém: "Nº do imóvel" ou "N do imvel" e "UF" e "Cidade"
            line_upper = line_stripped.upper()
            if (('Nº DO IMÓVEL' in line_upper or 'N DO IMVEL' in line_upper or 'NUMERO' in line_upper) 
                and 'UF' in line_upper and 'CIDADE' in line_upper):
                data_lines.append(line_stripped)
                header_found = True
                continue
            
            # Pular linha de título
            if 'Lista de Imóveis' in line_stripped or 'Lista de Imveis' in line_stripped or 'Data de geração' in line_stripped:
                continue
            
            # Adicionar linhas de dados (após o cabeçalho)
            if header_found and line_stripped:
                data_lines.append(line_stripped)
        
        csv_content_clean = '\n'.join(data_lines)
        csv_reader = csv.DictReader(io.StringIO(csv_content_clean), delimiter=';')
        
        properties = []
        for row in csv_reader:
            stats['rows_parsed'] += 1
            parsed = parse_csv_row(row)
            if parsed:
                properties.append(parsed)
                stats['rows_valid'] += 1
            else:
                stats['rows_failed'] += 1
        
        logger.info(f"CSV parseado: {stats['rows_valid']} imóveis válidos de {stats['rows_parsed']} linhas")
        
        # 4. Fazer upsert de cada imóvel
        for prop_data in properties:
            try:
                # Verificar se é inserção ou atualização
                with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id FROM properties WHERE id = %s", (prop_data['id'],))
                        exists = cur.fetchone()
                        
                        if upsert_property(prop_data):
                            if exists:
                                stats['rows_updated'] += 1
                            else:
                                stats['rows_inserted'] += 1
                        else:
                            stats['rows_failed'] += 1
            except Exception as e:
                logger.error(f"Erro ao processar imóvel {prop_data.get('id')}: {e}")
                stats['rows_failed'] += 1
                stats['errors'].append(f"Erro ao processar {prop_data.get('id')}: {str(e)}")
        
        # 5. Atualizar contador do leiloeiro
        try:
            with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE auctioneers 
                        SET property_count = (
                            SELECT COUNT(*) FROM properties 
                            WHERE auctioneer_id = %s AND is_duplicate = FALSE AND is_active = TRUE
                        ),
                        last_scrape = %s,
                        scrape_status = 'success',
                        scrape_error = NULL
                        WHERE id = %s
                        """,
                        (CAIXA_AUCTIONEER_ID, datetime.utcnow(), CAIXA_AUCTIONEER_ID)
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Erro ao atualizar contador do leiloeiro: {e}")
        
        stats['completed_at'] = datetime.utcnow().isoformat()
        logger.info(f"Sync concluído: {stats['rows_inserted']} inseridos, {stats['rows_updated']} atualizados, {stats['rows_failed']} falhas")
        
    except Exception as e:
        logger.error(f"Erro crítico na sincronização: {e}")
        logger.error(traceback.format_exc())
        stats['errors'].append(f"Erro crítico: {str(e)}")
        
        # Marcar leiloeiro com erro
        try:
            with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE auctioneers SET scrape_status = 'error', scrape_error = %s WHERE id = %s",
                        (str(e), CAIXA_AUCTIONEER_ID)
                    )
                    conn.commit()
        except Exception:
            pass
    
    return stats


def read_local_csvs(directory: str) -> Optional[str]:
    """
    Lê CSVs locais da pasta especificada e concatena.
    
    Args:
        directory: Diretório contendo os CSVs (ex: 'data/caixa')
    
    Returns:
        Conteúdo do CSV concatenado como string, ou None em caso de erro
    """
    import glob
    from pathlib import Path
    
    csv_dir = Path(directory)
    if not csv_dir.exists():
        logger.error(f"Diretório não encontrado: {directory}")
        return None
    
    # Buscar todos os CSVs no formato Lista_imoveis_{UF}.csv
    csv_files = sorted(csv_dir.glob("Lista_imoveis_*.csv"))
    
    if not csv_files:
        logger.error(f"Nenhum arquivo CSV encontrado em {directory}")
        return None
    
    logger.info(f"Encontrados {len(csv_files)} arquivos CSV em {directory}")
    
    all_content = []
    header_line = None  # Guardar linha de cabeçalho (será usada uma vez)
    
    for csv_file in csv_files:
        estado = csv_file.stem.replace('Lista_imoveis_', '')
        logger.info(f"Lendo CSV de {estado}: {csv_file.name}")
        
        try:
            with open(csv_file, 'r', encoding='latin-1') as f:
                content = f.read()
            
            # Processar conteúdo: encontrar cabeçalho e dados
            lines = content.split('\n')
            arquivo_dados = []  # Dados deste arquivo específico
            found_header = False  # Se encontramos cabeçalho neste arquivo
            
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                line_upper = line_stripped.upper()
                
                # Pular linha de título/metadados
                if 'Lista de Imóveis' in line_stripped or 'Lista de Imveis' in line_stripped or 'Data de geração' in line_stripped or 'Data de geracao' in line_stripped:
                    continue
                
                # Detectar linha de cabeçalho de dados
                has_numero = ('Nº DO IMÓVEL' in line_upper or 'N DO IMVEL' in line_upper or 'NUMERO' in line_upper or 'N°' in line_upper or ' DO IMOVEL' in line_upper)
                has_uf = 'UF' in line_upper
                has_cidade = 'CIDADE' in line_upper
                is_header = has_numero and has_uf and has_cidade
                
                if is_header:
                    # Encontramos cabeçalho
                    found_header = True
                    if header_line is None:
                        # Primeiro arquivo: guardar cabeçalho
                        header_line = line_stripped
                        all_content.append(line_stripped)
                        logger.debug(f"  Cabeçalho encontrado e adicionado em {estado}")
                    else:
                        # Arquivo subsequente: cabeçalho repetido, apenas marcar que encontramos
                        logger.debug(f"  Cabeçalho repetido encontrado em {estado} (pulando)")
                    # Continuar para próxima linha (não adicionar cabeçalho aos dados)
                    continue
                
                # Se já encontramos cabeçalho neste arquivo, processar como dados
                # OU se já temos cabeçalho globalmente (de arquivo anterior) e esta linha parece ser dados
                if found_header:
                    # Após encontrar cabeçalho neste arquivo, todas as linhas são dados
                    arquivo_dados.append(line_stripped)
                elif header_line is not None and ';' in line_stripped:
                    # Já temos cabeçalho de arquivo anterior, mas ainda não encontramos neste arquivo
                    # Se a linha parece ser dados (tem ponto-e-vírgula e não é cabeçalho), assumir que são dados
                    arquivo_dados.append(line_stripped)
                    found_header = True  # Marcar que começamos a processar dados
                elif header_line is None and 'UF' in line_upper and has_cidade:
                    # Ainda não encontramos cabeçalho globalmente - tentar detectar formato alternativo
                    header_line = line_stripped
                    all_content.append(line_stripped)
                    found_header = True
                    logger.debug(f"  Cabeçalho alternativo encontrado em {estado}")
            
            # Acumular dados deste arquivo ao resultado final
            all_content.extend(arquivo_dados)
            logger.info(f"  {estado}: {len(arquivo_dados)} linhas de dados adicionadas")
            
        except Exception as e:
            logger.error(f"Erro ao ler {csv_file}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue
    
    if not all_content:
        logger.error("Nenhum dado válido encontrado nos CSVs")
        return None
    
    result = '\n'.join(all_content)
    logger.info(f"CSV consolidado criado ({len(result)} caracteres, {len(all_content)-1} linhas de dados)")
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Sincronizar imóveis da Caixa Econômica Federal')
    parser.add_argument('--dry-run', action='store_true', help='Apenas parsear CSV, não salvar no banco')
    parser.add_argument('--local', type=str, metavar='DIR', help='Ler CSVs locais do diretório especificado (ex: data/caixa)')
    args = parser.parse_args()
    
    if not DATABASE_URL and not args.dry_run:
        logger.error("DATABASE_URL não configurada no ambiente")
        sys.exit(1)
    
    if args.dry_run:
        logger.info("MODO DRY-RUN: CSV será parseado mas não será salvo no banco")
        
        # Usar CSVs locais se especificado, senão baixar
        if args.local:
            csv_content = read_local_csvs(args.local)
        else:
            csv_content = download_caixa_csv()
        
        if csv_content:
            # Verificar se ainda é HTML
            if '<html' in csv_content.lower() or 'captcha' in csv_content.lower():
                logger.error("[ERRO] Ainda recebendo HTML/CAPTCHA. O site está bloqueando o acesso.")
                logger.error("Primeiros 500 caracteres da resposta:")
                logger.error(csv_content[:500])
                sys.exit(1)
            
            try:
                # O csv_content já vem processado (com cabeçalho e dados)
                # Usar diretamente com csv.DictReader
                csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=';')
                
                # Verificar se o CSV tem cabeçalho válido
                if csv_reader.fieldnames is None or len(csv_reader.fieldnames) == 0:
                    logger.error("[ERRO] CSV não tem cabeçalho válido")
                    logger.error(f"Primeira linha: {repr(data_lines[0] if data_lines else 'VAZIO')}")
                    logger.error(f"Total de linhas: {len(data_lines)}")
                    sys.exit(1)
                
                logger.info(f"[OK] Cabeçalhos encontrados: {list(csv_reader.fieldnames)}")
                
                count = 0
                errors = 0
                for row in csv_reader:
                    parsed = parse_csv_row(row)
                    if parsed:
                        count += 1
                        if count <= 5:  # Mostrar primeiros 5
                            logger.info(f"Exemplo {count}: {parsed.get('id')} - {parsed.get('city')}, {parsed.get('state')}")
                    else:
                        errors += 1
                        if errors <= 3:  # Mostrar primeiros 3 erros
                            logger.debug(f"Linha ignorada: {row}")
                
                logger.info(f"[OK] Total de imoveis validos: {count}")
                if errors > 0:
                    logger.warning(f"[AVISO] {errors} linhas foram ignoradas (sem UF/Cidade ou erro de parsing)")
            except Exception as e:
                logger.error(f"[ERRO] Erro ao parsear CSV: {e}")
                logger.error(traceback.format_exc())
                logger.error("Primeiros 1000 caracteres do CSV:")
                logger.error(csv_content[:1000])
                sys.exit(1)
        else:
            logger.error("[ERRO] Falha ao baixar CSV")
            sys.exit(1)
    else:
        # Usar CSVs locais se especificado
        if args.local:
            logger.info(f"Modo local: lendo CSVs de {args.local}")
            csv_content = read_local_csvs(args.local)
            if not csv_content:
                logger.error("Falha ao ler CSVs locais")
                sys.exit(1)
            
            # Processar CSV local
            stats = {
                'started_at': datetime.utcnow().isoformat(),
                'csv_downloaded': True,
                'rows_parsed': 0,
                'rows_valid': 0,
                'rows_inserted': 0,
                'rows_updated': 0,
                'rows_failed': 0,
                'errors': []
            }
            
            try:
                # O csv_content já vem processado de read_local_csvs() (cabeçalho + dados)
                # Usar diretamente com csv.DictReader
                csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=';')
                
                properties = []
                for row in csv_reader:
                    stats['rows_parsed'] += 1
                    parsed = parse_csv_row(row)
                    if parsed:
                        properties.append(parsed)
                        stats['rows_valid'] += 1
                    else:
                        stats['rows_failed'] += 1
                
                logger.info(f"CSV parseado: {stats['rows_valid']} imoveis validos de {stats['rows_parsed']} linhas")
                
                # Garantir que o leiloeiro Caixa existe (após parsear CSV)
                try:
                    ensure_caixa_auctioneer_exists()
                except Exception as e:
                    logger.error(f"Erro ao criar leiloeiro Caixa: {e}")
                    logger.warning("Continuando com upsert de imoveis mesmo com erro ao criar leiloeiro...")
                
                # Fazer upsert de cada imóvel
                for prop_data in properties:
                    try:
                        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
                            with conn.cursor() as cur:
                                cur.execute("SELECT id FROM properties WHERE id = %s", (prop_data['id'],))
                                exists = cur.fetchone()
                                
                                if upsert_property(prop_data):
                                    if exists:
                                        stats['rows_updated'] += 1
                                    else:
                                        stats['rows_inserted'] += 1
                                else:
                                    stats['rows_failed'] += 1
                    except Exception as e:
                        logger.error(f"Erro ao processar imóvel {prop_data.get('id')}: {e}")
                        stats['rows_failed'] += 1
                        stats['errors'].append(f"Erro ao processar {prop_data.get('id')}: {str(e)}")
                
                # Atualizar contador do leiloeiro
                try:
                    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                UPDATE auctioneers 
                                SET property_count = (
                                    SELECT COUNT(*) FROM properties 
                                    WHERE auctioneer_id = %s AND is_duplicate = FALSE AND is_active = TRUE
                                ),
                                last_scrape = %s,
                                scrape_status = 'success',
                                scrape_error = NULL
                                WHERE id = %s
                                """,
                                (CAIXA_AUCTIONEER_ID, datetime.utcnow(), CAIXA_AUCTIONEER_ID)
                            )
                            conn.commit()
                except Exception as e:
                    logger.error(f"Erro ao atualizar contador do leiloeiro: {e}")
                
                stats['completed_at'] = datetime.utcnow().isoformat()
                logger.info(f"Sync concluído: {stats['rows_inserted']} inseridos, {stats['rows_updated']} atualizados, {stats['rows_failed']} falhas")
            
            except Exception as e:
                logger.error(f"Erro crítico na sincronização: {e}")
                logger.error(traceback.format_exc())
                stats['errors'].append(f"Erro crítico: {str(e)}")
        else:
            stats = sync_caixa()
        print(f"\n{'='*60}")
        print(f"RESULTADO DA SINCRONIZACAO")
        print(f"{'='*60}")
        print(f"CSV baixado: {'[OK]' if stats['csv_downloaded'] else '[ERRO]'}")
        print(f"Linhas parseadas: {stats['rows_parsed']}")
        print(f"Imoveis validos: {stats['rows_valid']}")
        print(f"Novos imoveis: {stats['rows_inserted']}")
        print(f"Imoveis atualizados: {stats['rows_updated']}")
        print(f"Falhas: {stats['rows_failed']}")
        if stats['errors']:
            print(f"\nErros encontrados: {len(stats['errors'])}")
            for error in stats['errors'][:5]:  # Mostrar apenas primeiros 5
                print(f"  - {error}")
        print(f"{'='*60}\n")

