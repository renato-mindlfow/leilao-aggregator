import os
import re
import json
import httpx
import asyncio
import logging
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


def parse_brazilian_date(date_str: str) -> str | None:
    """
    Converte datas em formato brasileiro para formato PostgreSQL TIMESTAMP.
    
    Exemplos de entrada:
    - "29/12/2025 às 14:00"
    - "29/12/2025 14:00"
    - "29/12/2025"
    - "2025-12-29T14:00:00" (já está em formato válido, será convertido)
    - "2025-12-29 14:00:00" (já está no formato correto)
    
    Retorna: "2025-12-29 14:00:00" (formato PostgreSQL) ou None se inválido
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    
    # Se já está em formato PostgreSQL (YYYY-MM-DD HH:MM:SS), retornar
    if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', date_str):
        return date_str
    
    # Se está em formato ISO (YYYY-MM-DDTHH:MM:SS), converter para PostgreSQL
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', date_str):
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    
    # Remover "às" e outros textos
    date_str = re.sub(r'\s*às\s*', ' ', date_str)
    date_str = re.sub(r'\s+', ' ', date_str).strip()
    
    # Tentar diferentes formatos brasileiros
    formats = [
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Retornar no formato PostgreSQL: YYYY-MM-DD HH:MM:SS
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    
    # Se nenhum formato funcionou, retornar None
    return None

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
JINA_API_KEY = os.environ.get('JINA_API_KEY', '')  # Opcional

class UniversalScraper:
    """Scraper universal que funciona com qualquer site de leilão"""
    
    def __init__(self):
        self.timeout = 30.0
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    
    async def scrape_auctioneer(self, auctioneer: Dict) -> List[Dict]:
        """Scrape um leiloeiro específico usando múltiplas estratégias"""
        
        try:
            if not auctioneer:
                logger.error("Auctioneer é None")
                return []
            
            website = auctioneer.get('website', '')
            name = auctioneer.get('name', 'Unknown')
            
            if not website:
                logger.error(f"Leiloeiro {name} sem URL")
                return []
            
            logger.info(f"Iniciando scraping de {name}: {website}")
            
            properties = []
            working_url = None  # URL que funcionou
            
            # Tentar encontrar página de imóveis
            possible_paths = [
                '/imoveis',
                '/leiloes',
                '/leiloes/imoveis',
                '/busca?tipo=imovel',
                '/busca/imoveis',
                '/catalogo',
                '/catalogo/imoveis',
                '/',
            ]
            
            for path in possible_paths:
                url = urljoin(website, path)
                
                try:
                    # Estratégia 1: Requisição direta
                    result = await self._try_direct_request(url, name)
                    if result and isinstance(result, list):
                        properties.extend(result)
                        working_url = url  # Salvar URL que funcionou
                        logger.info(f"URL funcionou: {url} - {len(result)} imóveis")
                        break
                    
                    # Estratégia 2: Jina Reader (para sites protegidos)
                    result = await self._try_jina_reader(url, name)
                    if result and isinstance(result, list):
                        properties.extend(result)
                        working_url = url  # Salvar URL que funcionou
                        logger.info(f"URL funcionou via Jina: {url} - {len(result)} imóveis")
                        break
                        
                except Exception as e:
                    logger.warning(f"Erro ao tentar {url}: {e}")
                    logger.debug(traceback.format_exc())
                    continue
            
            # Paginação: tentar buscar mais páginas usando a URL que funcionou
            if properties and working_url:
                logger.info(f"Iniciando paginação para {name}...")
                try:
                    more_properties = await self._scrape_pagination(working_url, name, len(properties))
                    if more_properties and isinstance(more_properties, list):
                        properties.extend(more_properties)
                    logger.info(f"Após paginação: {len(properties)} imóveis total")
                except Exception as e:
                    logger.warning(f"Erro na paginação de {name}: {e}")
                    logger.debug(traceback.format_exc())
            
            logger.info(f"Scraping de {name} finalizado: {len(properties)} imóveis encontrados")
            
            return properties
            
        except Exception as e:
            logger.error(f"Erro no scraping: {e}")
            logger.error(traceback.format_exc())
            return []
    
    async def _try_direct_request(self, url: str, source: str) -> Optional[List[Dict]]:
        """Tenta requisição HTTP direta"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                
                if not response:
                    logger.warning(f"Resposta vazia de {url}")
                    return None
                
                if response.status_code != 200:
                    logger.debug(f"Status code {response.status_code} de {url}")
                    return None
                
                content_type = response.headers.get('content-type', '')
                
                # Se for JSON, processar diretamente
                if 'application/json' in content_type:
                    try:
                        data = response.json()
                        if data is None:
                            logger.warning(f"JSON vazio de {url}")
                            return None
                        return self._parse_json_response(data, source, url)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Erro ao parsear JSON de {url}: {e}")
                        return None
                
                # Se for HTML, usar IA para extrair
                html = response.text
                
                if not html:
                    logger.warning(f"HTML vazio de {url}")
                    return None
                
                # Verificar se tem conteúdo de imóveis
                if not self._has_property_content(html):
                    return None
                
                return await self._extract_with_ai(html, source, url)
                
        except Exception as e:
            logger.debug(f"Requisição direta falhou para {url}: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    async def _try_jina_reader(self, url: str, source: str) -> Optional[List[Dict]]:
        """Usa Jina Reader para sites protegidos por Cloudflare"""
        
        if not JINA_API_KEY:
            # Jina Reader gratuito (sem API key)
            jina_url = f"https://r.jina.ai/{url}"
        else:
            jina_url = f"https://r.jina.ai/{url}"
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {'Accept': 'text/plain'}
                if JINA_API_KEY:
                    headers['Authorization'] = f'Bearer {JINA_API_KEY}'
                
                response = await client.get(jina_url, headers=headers)
                
                if not response:
                    logger.warning(f"Resposta vazia do Jina Reader para {url}")
                    return None
                
                if response.status_code != 200:
                    logger.debug(f"Jina Reader retornou status {response.status_code} para {url}")
                    return None
                
                text = response.text
                
                if not text:
                    logger.warning(f"Texto vazio do Jina Reader para {url}")
                    return None
                
                if not self._has_property_content(text):
                    return None
                
                return await self._extract_with_ai(text, source, url, is_markdown=True)
                
        except Exception as e:
            logger.debug(f"Jina Reader falhou para {url}: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def _has_property_content(self, content: str) -> bool:
        """Verifica se o conteúdo parece ter imóveis"""
        
        keywords = [
            'apartamento', 'casa', 'terreno', 'imóvel', 'imovel',
            'leilão', 'leilao', 'lance', 'avaliação', 'avaliacao',
            'r$', 'reais', 'desconto', 'arrematação',
            'm²', 'm2', 'metros', 'quartos', 'dormitórios'
        ]
        
        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw in content_lower)
        
        return matches >= 3
    
    def _parse_json_response(self, data: Any, source: str, url: str) -> List[Dict]:
        """Parseia resposta JSON de APIs"""
        
        properties = []
        
        if not data:
            logger.warning(f"JSON vazio de {url}")
            return []
        
        # Tentar encontrar array de imóveis em diferentes estruturas
        items = []
        
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Procurar em campos comuns
            for key in ['data', 'items', 'results', 'imoveis', 'leiloes', 'properties', 'lotes']:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
        
        if not items:
            logger.debug(f"Nenhum item encontrado no JSON de {url}")
            return []
        
        for item in items:
            if not item or not isinstance(item, dict):
                continue
            
            prop = self._normalize_json_item(item, source, url)
            if prop:
                properties.append(prop)
        
        return properties
    
    def _normalize_json_item(self, item: Dict, source: str, base_url: str) -> Optional[Dict]:
        """Normaliza um item JSON para o formato padrão"""
        
        # Mapear campos comuns
        field_mappings = {
            'title': ['titulo', 'title', 'nome', 'name', 'descricao_resumida', 'description'],
            'description': ['descricao', 'description', 'detalhes', 'details', 'observacao'],
            'price': ['valor', 'price', 'preco', 'lance_inicial', 'valor_minimo', 'valor_avaliacao', 'first_auction_value'],
            'evaluated_price': ['valor_avaliacao', 'avaliacao', 'valor_mercado', 'evaluation', 'evaluation_value'],
            'discount': ['desconto', 'discount', 'percentual_desconto', 'discount_percentage'],
            'address': ['endereco', 'address', 'localizacao', 'location', 'logradouro'],
            'city': ['cidade', 'city', 'municipio'],
            'state': ['estado', 'state', 'uf'],
            'category': ['tipo', 'category', 'categoria', 'tipo_imovel', 'property_type'],
            'area': ['area', 'metragem', 'area_total', 'area_privativa', 'm2'],
            'image_url': ['imagem', 'image', 'foto', 'photo', 'thumbnail', 'imagem_url', 'image_url'],
            'url': ['url', 'link', 'href', 'detalhes_url', 'source_url'],
            'auction_date': ['data_leilao', 'auction_date', 'data', 'date', 'data_praca', 'first_auction_date'],
            'external_id': ['id', 'codigo', 'code', 'ref', 'referencia', 'lote'],
        }
        
        prop = {'source': source}
        
        for standard_field, possible_fields in field_mappings.items():
            for field in possible_fields:
                if field in item and item[field]:
                    prop[standard_field] = item[field]
                    break
        
        # Garantir que tem pelo menos título ou ID
        if not prop.get('title') and not prop.get('external_id'):
            return None
        
        # Ajustar URL da imagem
        if prop.get('image_url') and not prop['image_url'].startswith('http'):
            prop['image_url'] = urljoin(base_url, prop['image_url'])
        
        # Ajustar URL do imóvel
        if prop.get('url') and not prop['url'].startswith('http'):
            prop['url'] = urljoin(base_url, prop['url'])
        
        # Criar external_id se não existir
        if not prop.get('external_id'):
            prop['external_id'] = f"{source}_{hash(str(item))}"
        else:
            prop['external_id'] = f"{source}_{prop['external_id']}"
        
        return prop
    
    async def _extract_with_ai(self, content: str, source: str, url: str, is_markdown: bool = False) -> List[Dict]:
        """Usa IA para extrair imóveis do HTML/texto"""
        
        if not content:
            logger.warning(f"Conteúdo vazio para extração com IA de {url}")
            return []
        
        if not OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY não configurada, pulando extração com IA")
            return []
        
        # Limitar tamanho do conteúdo
        content = content[:50000]
        
        prompt = f"""Analise o conteúdo abaixo de um site de leilão de imóveis e extraia TODOS os imóveis listados.

Conteúdo do site ({source}):
{content[:30000]}

Para cada imóvel encontrado, extraia:
- title: título ou descrição curta
- price: valor do lance/leilão (número)
- evaluated_price: valor de avaliação (número)
- discount: percentual de desconto (número)
- address: endereço completo
- city: cidade
- state: estado (sigla UF)
- category: tipo (Apartamento, Casa, Terreno, Comercial, etc)
- area: área em m² (número)
- image_url: URL da imagem
- url: URL da página do imóvel
- auction_date: data do leilão
- external_id: código/referência do lote

Retorne APENAS um JSON array válido com os imóveis. Se não encontrar imóveis, retorne [].
Exemplo: [{{"title": "...", "price": 100000, ...}}]"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 4000
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Erro na API OpenAI: {response.text}")
                    return []
                
                result = response.json()
                
                # Verificar se a resposta é válida
                if not result or not result.get('choices'):
                    logger.error("Resposta vazia da OpenAI ou sem choices")
                    return []
                
                if not result['choices'] or len(result['choices']) == 0:
                    logger.error("Lista de choices vazia da OpenAI")
                    return []
                
                message = result['choices'][0].get('message')
                if not message:
                    logger.error("Mensagem vazia na resposta da OpenAI")
                    return []
                
                content = message.get('content')
                if not content:
                    logger.error("Conteúdo vazio na resposta da OpenAI")
                    return []
                
                # Limpar resposta
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                items = json.loads(content)
                
                if not isinstance(items, list):
                    return []
                
                # Adicionar source e ajustar IDs
                properties = []
                for item in items:
                    if isinstance(item, dict):
                        item['source'] = source
                        if not item.get('external_id'):
                            item['external_id'] = f"{source}_{hash(str(item))}"
                        else:
                            item['external_id'] = f"{source}_{item['external_id']}"
                        
                        # Ajustar URLs
                        if item.get('image_url') and not item['image_url'].startswith('http'):
                            item['image_url'] = urljoin(url, item['image_url'])
                        if item.get('url') and not item['url'].startswith('http'):
                            item['url'] = urljoin(url, item['url'])
                        
                        properties.append(item)
                
                return properties
                
        except json.JSONDecodeError as e:
            logger.warning(f"Erro ao parsear JSON da IA: {e}")
            logger.debug(traceback.format_exc())
            return []
        except Exception as e:
            logger.error(f"Erro na extração com IA: {e}")
            logger.error(traceback.format_exc())
            return []
    
    async def _scrape_pagination(self, working_url: str, source: str, initial_count: int) -> List[Dict]:
        """Tenta buscar páginas adicionais a partir da URL que funcionou"""
        
        additional = []
        
        # Padrões comuns de paginação
        pagination_patterns = [
            '?page={page}',
            '?pagina={page}',
            '?p={page}',
            '&page={page}',
            '&pagina={page}',
            '&p={page}',
        ]
        
        # Verificar se a URL já tem query string
        has_query = '?' in working_url
        
        logger.info(f"Iniciando paginação para {source} a partir de {working_url}")
        
        for pattern in pagination_patterns:
            # Ajustar padrão se URL já tem query string
            if has_query and pattern.startswith('?'):
                pattern = pattern.replace('?', '&')
            
            found_pages = False
            
            for page in range(2, 51):  # Aumentado para 50 páginas
                url = working_url.rstrip('/') + pattern.format(page=page)
                
                logger.debug(f"Tentando página {page}: {url}")
                
                try:
                    result = await self._try_direct_request(url, source)
                    
                    if result and len(result) > 0:
                        found_pages = True
                        additional.extend(result)
                        logger.info(f"Página {page} de {source}: +{len(result)} imóveis (total acumulado: {initial_count + len(additional)})")
                        
                        # Pequeno delay para não sobrecarregar
                        await asyncio.sleep(0.5)
                    else:
                        # Sem mais resultados, parar de tentar este padrão
                        logger.info(f"Página {page} vazia para {source}, parando paginação com padrão {pattern}")
                        break
                        
                except Exception as e:
                    logger.warning(f"Erro na página {page} de {source}: {e}")
                    break
            
            # Se encontrou resultados com este padrão, não tentar outros
            if found_pages:
                logger.info(f"Paginação de {source} completa: +{len(additional)} imóveis adicionais")
                break
        
        return additional


# Instância global
universal_scraper = UniversalScraper()

