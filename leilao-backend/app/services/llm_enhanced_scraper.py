"""
LLMEnhancedScraper - Alternativa ao Crawl4AI para Windows
Usa Playwright + GPT-4o-mini para extração inteligente

Funciona no Windows sem dependência lxml (que o Crawl4AI requer).
Mantém interface compatível com crawl4ai_scraper.py para drop-in replacement.
"""

import asyncio
import json
import logging
import re
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from openai import OpenAI
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Flag de disponibilidade
LLM_ENHANCED_AVAILABLE = True

try:
    from playwright.async_api import async_playwright
except ImportError:
    LLM_ENHANCED_AVAILABLE = False
    logger.warning("playwright não instalado. Execute: pip install playwright && playwright install chromium")


class LLMEnhancedScraper:
    """
    Scraper que combina Playwright (renderização JS) + GPT-4o-mini (extração inteligente).
    Alternativa ao Crawl4AI que funciona no Windows sem lxml.
    
    Portado para replicar 95% de sucesso do leilohub-scraper-final.
    """
    
    # Schema de extração (mesmo do Crawl4AI)
    EXTRACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "imoveis": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "titulo": {"type": "string", "description": "Título do imóvel"},
                        "endereco": {"type": "string", "description": "Endereço completo"},
                        "cidade": {"type": "string", "description": "Cidade"},
                        "estado": {"type": "string", "description": "UF (2 letras)"},
                        "tipo": {"type": "string", "description": "Apartamento, Casa, Terreno, Comercial, Rural"},
                        "area": {"type": "number", "description": "Área em m²"},
                        "valor_avaliacao": {"type": "number", "description": "Valor de avaliação em R$"},
                        "valor_minimo": {"type": "number", "description": "Lance mínimo ou 2ª praça em R$"},
                        "desconto": {"type": "number", "description": "Desconto %"},
                        "data_leilao": {"type": "string", "description": "Data do leilão"},
                        "modalidade": {"type": "string", "description": "Judicial, Extrajudicial, Venda Direta"},
                        "url": {"type": "string", "description": "URL do imóvel"},
                        "imagem": {"type": "string", "description": "URL da imagem principal"}
                    }
                }
            }
        }
    }
    
    def __init__(self, headless: bool = True):
        """
        Inicializa o scraper.
        
        Args:
            headless: Se True, executa browser sem interface gráfica
        """
        if not LLM_ENHANCED_AVAILABLE:
            raise ImportError("playwright não está instalado. Execute: pip install playwright && playwright install chromium")
        
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não configurada no .env")
        
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
    async def _setup_browser(self):
        """Configura browser com stealth mode."""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
        )
        
        # Injetar scripts de stealth
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            delete navigator.__proto__.webdriver;
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)
        
        self.page = await self.context.new_page()
        logger.debug("Browser configurado com stealth mode")
        
    async def _close_browser(self):
        """Fecha browser de forma segura."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.debug(f"Erro ao fechar browser: {e}")
            
    async def _fetch_page(self, url: str, wait_for_js: bool = True) -> str:
        """
        Busca página usando Playwright.
        Renderiza JavaScript e retorna HTML.
        """
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                # Usar domcontentloaded para ser mais rápido
                await self.page.goto(url, wait_until='domcontentloaded', timeout=90000)
                
                if wait_for_js:
                    # Aguardar um pouco mais para JS carregar
                    await asyncio.sleep(5)
                    
                    # Scroll para carregar lazy content
                    try:
                        await self.page.evaluate("""
                            async () => {
                                await new Promise((resolve) => {
                                    let totalHeight = 0;
                                    const distance = 300;
                                    const timer = setInterval(() => {
                                        window.scrollBy(0, distance);
                                        totalHeight += distance;
                                        if (totalHeight >= document.body.scrollHeight || totalHeight > 5000) {
                                            clearInterval(timer);
                                            resolve();
                                        }
                                    }, 100);
                                    setTimeout(resolve, 3000);  // Max 3s scroll
                                });
                            }
                        """)
                    except Exception as e:
                        logger.debug(f"Erro no scroll: {e}")
                        
                    await asyncio.sleep(2)
                
                html = await self.page.content()
                
                if html and len(html) > 500:
                    return html
                
                logger.warning(f"Tentativa {attempt+1}: HTML muito pequeno ({len(html)} chars)")
                
            except Exception as e:
                logger.warning(f"Tentativa {attempt+1} falhou para {url}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(3)
        
        logger.error(f"Todas as tentativas falharam para {url}")
        return ""
            
    def _clean_html(self, html: str) -> str:
        """
        Limpa HTML removendo scripts, styles e elementos desnecessários.
        Similar ao que Crawl4AI faz internamente.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remover elementos desnecessários
        for tag in soup.find_all(['script', 'style', 'noscript', 'iframe', 'svg', 'path', 'nav', 'footer', 'header']):
            tag.decompose()
            
        # Remover comentários
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and '<!--' in text):
            try:
                comment.extract()
            except:
                pass
            
        # Pegar texto visível
        text = soup.get_text(separator='\n', strip=True)
        
        # Limpar linhas vazias múltiplas
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        clean_text = '\n'.join(lines)
        
        # Limitar tamanho para não estourar contexto do LLM (GPT-4o-mini suporta 128k tokens)
        if len(clean_text) > 15000:
            clean_text = clean_text[:15000] + "\n... [truncado para caber no contexto]"
            
        return clean_text
        
    def _extract_with_llm(self, text: str, url: str) -> List[Dict]:
        """
        Usa GPT-4o-mini para extrair dados estruturados do texto.
        Prompt otimizado baseado nos 95% de sucesso do leilohub-scraper-final.
        """
        try:
            prompt = f"""Analise o conteúdo de uma página de leilões de imóveis e extraia TODOS os dados estruturados.

URL: {url}

CONTEÚDO DA PÁGINA:
{text}

INSTRUÇÕES DE EXTRAÇÃO:
1. Extraia TODOS os imóveis encontrados (não pule nenhum)
2. Para cada imóvel, extraia os campos disponíveis
3. Valores monetários: apenas números (sem R$, pontos ou vírgulas). Exemplo: "R$ 250.000,00" → 250000
4. Datas: formato DD/MM/YYYY ou deixe em branco
5. Estado: sigla UF com 2 letras maiúsculas (SP, RJ, MG, etc.)
6. Se um campo não estiver disponível, omita-o ou use null
7. URLs de imóveis devem ser completas (adicione domínio se necessário)

TIPOS DE IMÓVEL VÁLIDOS:
- Apartamento
- Casa
- Terreno
- Comercial (inclui galpão, sala, loja)
- Rural (inclui fazenda, sítio, chácara)
- Outro

MODALIDADES VÁLIDAS:
- Judicial
- Extrajudicial
- Venda Direta

Retorne APENAS um JSON válido no formato:
{{
    "imoveis": [
        {{
            "titulo": "string",
            "endereco": "string", 
            "cidade": "string",
            "estado": "UF",
            "tipo": "Apartamento|Casa|Terreno|Comercial|Rural|Outro",
            "area": number,
            "valor_avaliacao": number,
            "valor_minimo": number,
            "desconto": number,
            "data_leilao": "DD/MM/YYYY",
            "modalidade": "Judicial|Extrajudicial|Venda Direta",
            "url": "string",
            "imagem": "string"
        }}
    ]
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um extrator de dados especializado em leilões de imóveis brasileiros. Retorne apenas JSON válido, sem explicações adicionais."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            imoveis = result.get('imoveis', [])
            
            logger.info(f"LLM extraiu {len(imoveis)} imóveis")
            return imoveis
            
        except Exception as e:
            logger.error(f"Erro na extração LLM: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
            
    def _safe_str(self, value: any, default: str = '') -> str:
        """Converte valor para string de forma segura, tratando None."""
        if value is None:
            return default
        return str(value).strip()
    
    def _safe_float(self, value: any) -> Optional[float]:
        """Converte valor para float de forma segura."""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                # Limpar formatação brasileira
                value = value.replace('.', '').replace(',', '.').replace('R$', '').strip()
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _extract_photos_regex(self, html: str) -> List[str]:
        """
        Extrai URLs de fotos usando regex (fallback confiável).
        Mais preciso que LLM para URLs de imagens.
        """
        patterns = [
            r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?',
            r'src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
            r'data-src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
        ]
        
        photos = set()
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                url = match if isinstance(match, str) else match
                # Filtrar logos e placeholders
                if any(x in url.lower() for x in ['logo', 'icon', 'placeholder', 'banner', 'favicon', 'sprite']):
                    continue
                # Verificar se é URL válida de imagem
                if url.startswith(('http://', 'https://')):
                    photos.add(url)
                    
        return list(photos)[:20]  # Max 20 fotos
        
    def _normalize_property(self, raw: Dict, url: str, auctioneer_id: str, auctioneer_name: str) -> Dict:
        """
        Normaliza dados extraídos para o formato do banco.
        Compatível com crawl4ai_scraper.py
        """
        # Normalizar categoria
        tipo = self._safe_str(raw.get('tipo')).lower()
        category_map = {
            'apartamento': 'Apartamento',
            'apto': 'Apartamento',
            'casa': 'Casa',
            'terreno': 'Terreno',
            'lote': 'Terreno',
            'comercial': 'Comercial',
            'galpão': 'Comercial',
            'galpao': 'Comercial',
            'sala': 'Comercial',
            'loja': 'Comercial',
            'prédio': 'Comercial',
            'predio': 'Comercial',
            'rural': 'Rural',
            'fazenda': 'Rural',
            'sítio': 'Rural',
            'sitio': 'Rural',
            'chácara': 'Rural',
            'chacara': 'Rural',
        }
        category = category_map.get(tipo, 'Outro')
        
        # Normalizar estado
        state = self._safe_str(raw.get('estado')).upper()
        valid_states = {'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
                       'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 
                       'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'}
        if state not in valid_states:
            state = ''
            
        # Normalizar cidade (Title Case)
        city = self._safe_str(raw.get('cidade'))
        if city:
            city = city.title()
        
        # Normalizar título
        title = self._safe_str(raw.get('titulo'))
        if title:
            title = title.title()
        
        # Normalizar modalidade
        modalidade = self._safe_str(raw.get('modalidade')).lower()
        if 'judicial' in modalidade and 'extra' not in modalidade:
            auction_type = 'Judicial'
        elif 'extrajudicial' in modalidade:
            auction_type = 'Extrajudicial'
        elif 'direta' in modalidade or 'venda' in modalidade:
            auction_type = 'Venda Direta'
        else:
            auction_type = 'Extrajudicial'
        
        # Parsear data
        date_str = self._safe_str(raw.get('data_leilao'))
        auction_date = None
        if date_str and '/' in date_str:
            try:
                parts = date_str.split('/')
                if len(parts) == 3:
                    auction_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            except:
                pass
        
        return {
            'title': title,
            'address': self._safe_str(raw.get('endereco')),
            'city': city,
            'state': state,
            'category': category,
            'area_total': self._safe_float(raw.get('area')),
            'evaluation_value': self._safe_float(raw.get('valor_avaliacao')),
            'first_auction_value': self._safe_float(raw.get('valor_minimo')),
            'second_auction_value': self._safe_float(raw.get('valor_minimo')),
            'discount_percentage': self._safe_float(raw.get('desconto')),
            'first_auction_date': auction_date,
            'auction_type': auction_type,
            'source_url': self._safe_str(raw.get('url')) or url,
            'image_url': self._safe_str(raw.get('imagem')) or None,
            'auctioneer_id': auctioneer_id or 'llm_enhanced',
            'auctioneer_name': auctioneer_name or 'LLM Enhanced',
            'source': 'llm_enhanced_scraper',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        
    async def scrape_url(self, url: str, auctioneer_id: str = None, auctioneer_name: str = None) -> List[Dict]:
        """
        Método principal de scraping assíncrono.
        Interface compatível com crawl4ai_scraper.py
        
        Args:
            url: URL da página de listagem
            auctioneer_id: ID do leiloeiro
            auctioneer_name: Nome do leiloeiro
        
        Returns:
            Lista de dicionários com dados dos imóveis
        """
        properties = []
        
        try:
            await self._setup_browser()
            
            # 1. Buscar página com Playwright
            logger.info(f"LLMEnhanced: Buscando {url}")
            html = await self._fetch_page(url)
            
            if not html or len(html) < 500:
                logger.warning(f"Página vazia ou muito pequena: {url}")
                return []
                
            # 2. Limpar HTML
            clean_text = self._clean_html(html)
            logger.debug(f"HTML limpo: {len(clean_text)} chars")
            
            # 3. Extrair com LLM
            raw_properties = self._extract_with_llm(clean_text, url)
            
            # 4. Extrair fotos com regex
            photos = self._extract_photos_regex(html)
            
            # 5. Normalizar propriedades
            for raw in raw_properties:
                prop = self._normalize_property(raw, url, auctioneer_id, auctioneer_name)
                
                # Atribuir foto se disponível e não foi extraída pelo LLM
                if not prop.get('image_url') and photos:
                    prop['image_url'] = photos.pop(0)
                    
                properties.append(prop)
                
            logger.info(f"LLMEnhanced: {len(properties)} imóveis extraídos de {url}")
            
        except Exception as e:
            logger.error(f"Erro no scraping de {url}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        finally:
            await self._close_browser()
            
        return properties
    
    def scrape_url_sync(self, url: str, auctioneer_id: str = None, auctioneer_name: str = None) -> List[Dict]:
        """
        Método síncrono para compatibilidade com código existente.
        Interface compatível com crawl4ai_scraper.py
        """
        return asyncio.run(self.scrape_url(url, auctioneer_id, auctioneer_name))


# Funções de conveniência (compatibilidade com crawl4ai_scraper.py)
async def scrape_with_llm(url: str, auctioneer_id: str = None, auctioneer_name: str = None, headless: bool = True) -> List[Dict]:
    """
    Função helper para scraping rápido assíncrono.
    """
    scraper = LLMEnhancedScraper(headless=headless)
    return await scraper.scrape_url(url, auctioneer_id, auctioneer_name)


def scrape_with_llm_enhanced(url: str, auctioneer_id: str = None, auctioneer_name: str = None) -> List[Dict]:
    """
    Função de conveniência síncrona.
    Compatível com scrape_with_crawl4ai()
    """
    scraper = LLMEnhancedScraper(headless=True)
    return scraper.scrape_url_sync(url, auctioneer_id, auctioneer_name)
