"""
Scraper baseado em Crawl4AI + GPT-4o-mini
Portado de leilohub-scraper-final (95% sucesso em 116 leiloeiros - Dez/2025)

Fluxo:
1. Crawl4AI baixa página HTML
2. LLMExtractionStrategy + GPT-4o-mini extrai dados estruturados
3. Regex fallback para fotos
4. Normalização e retorno

Arquitetura:
- Usa AsyncWebCrawler do Crawl4AI para navegação
- LLMExtractionStrategy com GPT-4o-mini para extração estruturada
- Schema JSON para garantir formato consistente
- Normalização de dados para o formato do banco
"""
import os
import sys
import json
import re
import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Verificar dependências
try:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
except ImportError:
    AsyncWebCrawler = None
    CrawlerRunConfig = None
    CacheMode = None

try:
    from crawl4ai.extraction_strategy import LLMExtractionStrategy
except ImportError:
    try:
        from crawl4ai.strategies import LLMExtractionStrategy
    except ImportError:
        LLMExtractionStrategy = None

CRAWL4AI_AVAILABLE = AsyncWebCrawler is not None and LLMExtractionStrategy is not None

if not CRAWL4AI_AVAILABLE:
    logger.warning("crawl4ai não instalado. Execute: pip install crawl4ai")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Schema para extração de imóveis (mesmo usado nos testes de 95%)
IMOVEL_SCHEMA = {
    "type": "object",
    "properties": {
        "imoveis": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string", "description": "Título ou descrição do imóvel"},
                    "endereco": {"type": "string", "description": "Endereço completo"},
                    "cidade": {"type": "string", "description": "Cidade"},
                    "estado": {"type": "string", "description": "Estado (sigla UF de 2 letras)"},
                    "tipo": {"type": "string", "description": "Tipo: Apartamento, Casa, Terreno, Comercial, Rural"},
                    "area": {"type": "number", "description": "Área em m²"},
                    "valor_avaliacao": {"type": "number", "description": "Valor de avaliação em R$"},
                    "valor_minimo": {"type": "number", "description": "Lance mínimo ou valor de 2ª praça em R$"},
                    "desconto": {"type": "number", "description": "Percentual de desconto"},
                    "data_leilao": {"type": "string", "description": "Data do leilão"},
                    "modalidade": {"type": "string", "description": "Judicial, Extrajudicial ou Venda Direta"},
                    "url": {"type": "string", "description": "URL da página do imóvel"},
                    "imagem": {"type": "string", "description": "URL da imagem principal"}
                }
            }
        }
    }
}

# Prompt otimizado (baseado nos testes de Dez/2025)
EXTRACTION_PROMPT = """
Extraia TODOS os imóveis disponíveis para leilão nesta página.

Para cada imóvel, extraia:
- titulo: Nome/descrição do imóvel
- endereco: Endereço completo se disponível
- cidade: Cidade do imóvel
- estado: Sigla do estado (UF) com 2 letras (SP, RJ, MG, etc.)
- tipo: Apartamento, Casa, Terreno, Comercial ou Rural
- area: Área em m² (apenas número)
- valor_avaliacao: Valor de avaliação em R$ (apenas número)
- valor_minimo: Lance mínimo ou 2ª praça em R$ (apenas número)
- desconto: Percentual de desconto (apenas número)
- data_leilao: Data do leilão (formato DD/MM/YYYY)
- modalidade: Judicial, Extrajudicial ou Venda Direta
- url: URL completa da página do imóvel
- imagem: URL da imagem principal

REGRAS:
- Se um campo não estiver disponível, deixe em branco ou null
- Para valores monetários, extraia apenas o número (sem R$, pontos ou vírgulas)
- Para área, extraia apenas o número (sem m²)
- Foque em imóveis reais, ignore anúncios, banners e menus
- Estado deve ser sigla de 2 letras maiúsculas
"""


class Crawl4AIScraper:
    """
    Scraper usando Crawl4AI + GPT-4o-mini.
    Portado de leilohub-scraper-final com 95% de sucesso.
    """
    
    def __init__(self):
        if not CRAWL4AI_AVAILABLE:
            raise ImportError("crawl4ai não está instalado. Execute: pip install crawl4ai")
        
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não configurada no .env")
        
        self.extraction_strategy = LLMExtractionStrategy(
            provider="openai/gpt-4o-mini",
            api_token=OPENAI_API_KEY,
            schema=IMOVEL_SCHEMA,
            extraction_type="schema",
            instruction=EXTRACTION_PROMPT,
            chunk_token_threshold=8000,  # Otimizado nos testes
            overlap_rate=0.1,
        )
    
    async def scrape_url(self, url: str, auctioneer_id: str = None, auctioneer_name: str = None) -> List[Dict]:
        """
        Extrai imóveis de uma URL usando Crawl4AI + GPT-4o-mini.
        
        Args:
            url: URL da página de listagem do leiloeiro
            auctioneer_id: ID do leiloeiro (para normalização)
            auctioneer_name: Nome do leiloeiro
        
        Returns:
            Lista de dicionários com dados dos imóveis
        """
        logger.info(f"Crawl4AI: Iniciando scrape de {url}")
        
        try:
            # Configurar crawl4ai
            config = CrawlerRunConfig(
                delay_before_return_html=3,  # 3 segundos de espera para JS
                wait_for="body",
                excluded_tags=[
                    "nav", "footer", "header", "aside",
                    "script", "style", "noscript", "iframe"
                ],
            )
            
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=config,
                    extraction_strategy=self.extraction_strategy,
                    bypass_cache=True,
                )
                
                if not result.success:
                    logger.error(f"Crawl4AI: Falha ao acessar {url}: {result.error_message}")
                    return []
                
                # Parsear resultado
                imoveis = self._parse_result(result.extracted_content)
                
                # Extrair fotos via regex (mais confiável que LLM para URLs)
                fotos = self._extract_fotos_regex(result.html)
                
                # Normalizar e enriquecer dados
                normalized = []
                for i, imovel in enumerate(imoveis):
                    prop = self._normalize_property(imovel, auctioneer_id, auctioneer_name, url)
                    
                    # Adicionar foto se disponível
                    if i < len(fotos) and not prop.get('image_url'):
                        prop['image_url'] = fotos[i]
                    
                    normalized.append(prop)
                
                logger.info(f"Crawl4AI: Extraídos {len(normalized)} imóveis de {url}")
                return normalized
                
        except Exception as e:
            logger.error(f"Crawl4AI: Erro em {url}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _parse_result(self, extracted_content: str) -> List[Dict]:
        """Parseia o JSON retornado pelo LLM."""
        if not extracted_content:
            return []
        
        try:
            data = json.loads(extracted_content)
            return data.get("imoveis", [])
        except json.JSONDecodeError as e:
            logger.warning(f"Erro ao parsear JSON: {e}")
            return []
    
    def _extract_fotos_regex(self, html: str) -> List[str]:
        """
        Extrai URLs de fotos via regex.
        Mais confiável que LLM para URLs de imagens.
        """
        if not html:
            return []
        
        # Padrões comuns de URLs de fotos de imóveis
        patterns = [
            r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?',
            r'https?://cdn[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
            r'https?://[^\s"\'<>]*imovel[^\s"\'<>]*\.(?:jpg|jpeg|png|webp)',
        ]
        
        fotos = set()
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            fotos.update(matches)
        
        # Filtrar logos e placeholders
        fotos_filtradas = [
            f for f in fotos 
            if not any(x in f.lower() for x in ['logo', 'banner', 'placeholder', 'icon', 'avatar'])
        ]
        
        return list(fotos_filtradas)[:20]  # Limitar a 20 fotos
    
    def _normalize_property(self, imovel: Dict, auctioneer_id: str, auctioneer_name: str, source_url: str) -> Dict:
        """Normaliza dados do imóvel para o formato do banco."""
        
        # Inferir auctioneer_id da URL se não fornecido
        if not auctioneer_id:
            domain = urlparse(source_url).netloc
            auctioneer_id = domain.replace('www.', '').replace('.com.br', '').replace('.', '_')
        
        return {
            # Identificação
            'source': auctioneer_id.lower(),
            'auctioneer_id': auctioneer_id.lower(),
            'auctioneer_name': auctioneer_name or auctioneer_id.title(),
            'source_url': imovel.get('url') or source_url,
            
            # Dados básicos
            'title': imovel.get('titulo', '').strip(),
            'address': imovel.get('endereco', '').strip(),
            'city': self._title_case(imovel.get('cidade', '')),
            'state': self._normalize_state(imovel.get('estado', '')),
            'category': self._normalize_category(imovel.get('tipo', '')),
            
            # Valores
            'evaluation_value': self._parse_number(imovel.get('valor_avaliacao')),
            'first_auction_value': self._parse_number(imovel.get('valor_avaliacao')),
            'second_auction_value': self._parse_number(imovel.get('valor_minimo')),
            'discount_percentage': self._parse_number(imovel.get('desconto')),
            'area_total': self._parse_number(imovel.get('area')),
            
            # Datas e modalidade
            'first_auction_date': self._parse_date(imovel.get('data_leilao')),
            'auction_type': self._normalize_modalidade(imovel.get('modalidade', '')),
            
            # Imagem
            'image_url': imovel.get('imagem'),
            
            # Metadata
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
    
    def _title_case(self, text: str) -> str:
        """Converte para Title Case."""
        if not text:
            return ''
        return ' '.join(word.capitalize() for word in text.strip().split())
    
    def _normalize_state(self, state: str) -> str:
        """Normaliza sigla do estado."""
        if not state:
            return ''
        state = state.strip().upper()
        valid_states = {'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
                       'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 
                       'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'}
        return state if state in valid_states else ''
    
    def _normalize_category(self, tipo: str) -> str:
        """Normaliza categoria do imóvel."""
        if not tipo:
            return 'Outro'
        tipo_lower = tipo.lower()
        
        if 'apartamento' in tipo_lower or 'apto' in tipo_lower:
            return 'Apartamento'
        elif 'casa' in tipo_lower:
            return 'Casa'
        elif 'terreno' in tipo_lower or 'lote' in tipo_lower:
            return 'Terreno'
        elif 'comercial' in tipo_lower or 'sala' in tipo_lower or 'loja' in tipo_lower:
            return 'Comercial'
        elif 'rural' in tipo_lower or 'fazenda' in tipo_lower or 'sítio' in tipo_lower:
            return 'Rural'
        else:
            return 'Outro'
    
    def _normalize_modalidade(self, modalidade: str) -> str:
        """Normaliza modalidade do leilão."""
        if not modalidade:
            return 'Extrajudicial'
        modalidade_lower = modalidade.lower()
        
        if 'judicial' in modalidade_lower and 'extra' not in modalidade_lower:
            return 'Judicial'
        elif 'extrajudicial' in modalidade_lower:
            return 'Extrajudicial'
        elif 'direta' in modalidade_lower or 'venda' in modalidade_lower:
            return 'Venda Direta'
        else:
            return 'Extrajudicial'
    
    def _parse_number(self, value) -> Optional[float]:
        """Converte valor para float."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remover formatação brasileira
            clean = re.sub(r'[R$\s.]', '', value).replace(',', '.')
            try:
                return float(clean)
            except ValueError:
                return None
        return None
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Converte data para formato ISO."""
        if not date_str:
            return None
        
        # Tentar diversos formatos
        formats = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y']
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None
    
    def scrape_url_sync(self, url: str, auctioneer_id: str = None, auctioneer_name: str = None) -> List[Dict]:
        """Versão síncrona do scrape_url."""
        return asyncio.run(self.scrape_url(url, auctioneer_id, auctioneer_name))


# Função de conveniência
def scrape_with_crawl4ai(url: str, auctioneer_id: str = None, auctioneer_name: str = None) -> List[Dict]:
    """
    Função de conveniência para scraping com Crawl4AI.
    
    Uso:
        from app.services.crawl4ai_scraper import scrape_with_crawl4ai
        imoveis = scrape_with_crawl4ai("https://www.megaleiloes.com.br")
    """
    scraper = Crawl4AIScraper()
    return scraper.scrape_url_sync(url, auctioneer_id, auctioneer_name)
