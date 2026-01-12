#!/usr/bin/env python3
"""
SCRAPER TOP 10 LEILOEIROS - LeiloHub
=====================================

Script para fazer scraping dos 10 maiores leiloeiros identificados no concorrente.
Usa Playwright com técnicas de Stealth para bypass de Cloudflare.

Uso:
    python SCRAPER_TOP10_LEILOEIROS.py
    python SCRAPER_TOP10_LEILOEIROS.py --limit 5  # Testar apenas 5 leiloeiros
    python SCRAPER_TOP10_LEILOEIROS.py --headless false  # Ver navegador

Requisitos:
    pip install playwright psycopg2-binary python-dotenv
    playwright install chromium
"""

import asyncio
import re
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Tentar importar dependências
try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("⚠️ Playwright não instalado. Execute: pip install playwright && playwright install chromium")

try:
    import psycopg2
    from psycopg2.extras import execute_values
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("⚠️ psycopg2 não instalado. Execute: pip install psycopg2-binary")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# =============================================================================
# CONFIGURAÇÃO DOS TOP 10 LEILOEIROS
# =============================================================================

@dataclass
class Leiloeiro:
    id: str
    name: str
    url: str
    expected_properties: int
    property_list_path: str = "/imoveis"  # Caminho padrão para lista de imóveis
    property_selector: str = "a[href*='/imovel']"  # Seletor padrão


TOP_10_LEILOEIROS = [
    Leiloeiro(
        id="arg_leiloes",
        name="ARG Leilões",
        url="https://www.argleiloes.com.br",
        expected_properties=599,
        property_list_path="/",
        property_selector="a[href*='/leilao/'], a[href*='/imovel/']"
    ),
    Leiloeiro(
        id="realiza_leiloes",
        name="Realiza Leilões",
        url="https://www.realizaleiloes.com.br",
        expected_properties=598,
        property_list_path="/leiloes",
        property_selector="a[href*='/leilao/'], a[href*='/lote/']"
    ),
    Leiloeiro(
        id="isaias_leiloes",
        name="Isaias Leilões",
        url="https://www.isaiasleiloes.com.br",
        expected_properties=544,
        property_list_path="/imoveis",
        property_selector="a[href*='/imovel/'], a[href*='/lote/']"
    ),
    Leiloeiro(
        id="leiloes_ceruli",
        name="Leilões Ceruli",
        url="http://www.leiloesceruli.com.br",
        expected_properties=537,
        property_list_path="/",
        property_selector="a[href*='/leilao/'], a[href*='/imovel/']"
    ),
    Leiloeiro(
        id="mgl_leiloes",
        name="MGL Leilões",
        url="https://www.mgl.com.br",
        expected_properties=447,
        property_list_path="/leiloes",
        property_selector="a[href*='/leilao/'], a[href*='/imovel/']"
    ),
    Leiloeiro(
        id="leiloes_rn",
        name="Leilões RN",
        url="https://www.leiloesrn.com.br",
        expected_properties=321,
        property_list_path="/",
        property_selector="a[href*='/leilao/'], a[href*='/imovel/']"
    ),
    Leiloeiro(
        id="grupo_lance",
        name="Grupo Lance",
        url="https://www.grupolance.com.br",
        expected_properties=247,
        property_list_path="/imoveis",
        property_selector="a[href*='/imovel/'], a[href*='/lote/']"
    ),
    Leiloeiro(
        id="lb_leiloes",
        name="LB Leilões",
        url="https://www.lbleiloes.com.br",
        expected_properties=213,
        property_list_path="/leiloes",
        property_selector="a[href*='/leilao/'], a[href*='/lote/']"
    ),
    Leiloeiro(
        id="globo_leiloes",
        name="Globo Leilões",
        url="https://globoleiloes.com.br",
        expected_properties=209,
        property_list_path="/",
        property_selector="a[href*='/leilao/'], a[href*='/imovel/']"
    ),
    Leiloeiro(
        id="trustbid_leiloes",
        name="TrustBid Leilões",
        url="https://www.trustbid.com.br",
        expected_properties=188,
        property_list_path="/leiloes",
        property_selector="a[href*='/leilao/'], a[href*='/lote/']"
    ),
]


# =============================================================================
# STEALTH CONFIGURATION
# =============================================================================

CHROMIUM_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-blink-features=AutomationControlled',
    '--disable-features=IsolateOrigins,site-per-process',
    '--window-size=1920,1080',
    '--disable-web-security',
    '--disable-features=VizDisplayCompositor',
    '--disable-infobars',
    '--disable-notifications',
]

STEALTH_SCRIPT = """
// Ocultar webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => false });
delete navigator.__proto__.webdriver;

// Plugins falsos
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', description: 'Portable Document Format' },
        { name: 'Chrome PDF Viewer', description: '' },
        { name: 'Native Client', description: '' }
    ]
});

// Languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['pt-BR', 'pt', 'en-US', 'en']
});

// Chrome object
window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} };

// Platform
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
"""

BROWSER_CONTEXT_OPTIONS = {
    'viewport': {'width': 1920, 'height': 1080},
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'locale': 'pt-BR',
    'timezone_id': 'America/Sao_Paulo',
    'extra_http_headers': {
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
}


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class Top10Scraper:
    """Scraper para os TOP 10 leiloeiros."""
    
    def __init__(self, headless: bool = True, save_to_db: bool = True):
        self.headless = headless
        self.save_to_db = save_to_db
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.results: Dict[str, List[Dict]] = {}
        self.errors: Dict[str, str] = {}
        
    async def setup_browser(self):
        """Inicializa browser com stealth."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=CHROMIUM_ARGS
        )
        context = await self.browser.new_context(**BROWSER_CONTEXT_OPTIONS)
        await context.add_init_script(STEALTH_SCRIPT)
        self.page = await context.new_page()
        logger.info("✅ Browser inicializado com stealth")
        
    async def close_browser(self):
        """Fecha browser."""
        if self.browser:
            await self.browser.close()
            logger.info("🔒 Browser fechado")
            
    async def scrape_leiloeiro(self, leiloeiro: Leiloeiro, max_properties: int = 50) -> List[Dict]:
        """Faz scraping de um leiloeiro específico."""
        properties = []
        
        try:
            # Navegar para página de listagem
            url = f"{leiloeiro.url}{leiloeiro.property_list_path}"
            logger.info(f"🌐 Acessando: {url}")
            
            await self.page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)
            
            # Verificar bloqueio
            page_text = await self.page.evaluate("() => document.body.innerText || ''")
            if 'navegador incompatível' in page_text.lower() or 'acesso negado' in page_text.lower():
                logger.warning(f"⚠️ Possível bloqueio detectado em {leiloeiro.name}")
                await asyncio.sleep(5)
                
            # Scroll para carregar conteúdo lazy
            await self._scroll_page()
            
            # Encontrar links de propriedades
            property_links = await self.page.query_selector_all(leiloeiro.property_selector)
            
            # Extrair URLs únicas
            urls = set()
            for link in property_links:
                href = await link.get_attribute('href')
                if href:
                    if href.startswith('/'):
                        href = f"{leiloeiro.url}{href}"
                    if leiloeiro.url in href or href.startswith('http'):
                        urls.add(href)
                        
            logger.info(f"📋 Encontradas {len(urls)} URLs de propriedades")
            
            # Limitar quantidade
            urls_list = list(urls)[:max_properties]
            
            # Extrair dados de cada propriedade
            for i, prop_url in enumerate(urls_list, 1):
                try:
                    logger.info(f"  [{i}/{len(urls_list)}] Extraindo: {prop_url[:60]}...")
                    prop_data = await self._extract_property(prop_url, leiloeiro)
                    if prop_data and prop_data.get('title'):
                        properties.append(prop_data)
                    await asyncio.sleep(1.5)  # Rate limiting
                except Exception as e:
                    logger.warning(f"  ❌ Erro ao extrair {prop_url}: {str(e)[:50]}")
                    
            logger.info(f"✅ {leiloeiro.name}: {len(properties)} propriedades extraídas")
            
        except PlaywrightTimeout:
            error = f"Timeout ao acessar {leiloeiro.url}"
            logger.error(f"❌ {error}")
            self.errors[leiloeiro.id] = error
        except Exception as e:
            error = str(e)[:100]
            logger.error(f"❌ Erro em {leiloeiro.name}: {error}")
            self.errors[leiloeiro.id] = error
            
        return properties
    
    async def _scroll_page(self):
        """Scroll para carregar conteúdo lazy-loaded."""
        try:
            await self.page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 300;
                        const timer = setInterval(() => {
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if (totalHeight >= 3000) {
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            await asyncio.sleep(2)
        except Exception as e:
            logger.debug(f"Erro no scroll: {e}")
            
    async def _extract_property(self, url: str, leiloeiro: Leiloeiro) -> Optional[Dict]:
        """Extrai dados de uma propriedade."""
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
            
            # Obter HTML e texto
            html = await self.page.content()
            text = await self.page.evaluate("() => document.body.innerText || ''")
            
            # Extrair dados
            property_data = {
                'source_url': url,
                'auctioneer_id': leiloeiro.id,
                'auctioneer_name': leiloeiro.name,
                'auctioneer_url': leiloeiro.url,
            }
            
            # Título
            title_elem = await self.page.query_selector('h1, h2.title, .titulo-lote, .property-title')
            if title_elem:
                property_data['title'] = (await title_elem.inner_text()).strip()
                
            # Se não encontrou título, tentar do HTML
            if not property_data.get('title'):
                title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
                if title_match:
                    property_data['title'] = title_match.group(1).strip()
                    
            # Localização (Estado e Cidade)
            state, city = self._extract_location(text + ' ' + html)
            property_data['state'] = state
            property_data['city'] = city
            
            # Categoria
            property_data['category'] = self._determine_category(property_data.get('title', '') + ' ' + text)
            
            # Preços
            prices = self._extract_prices(text + ' ' + html)
            property_data.update(prices)
            
            # Imagem
            img_elem = await self.page.query_selector('img.property-image, img.lote-image, .gallery img, .carousel img')
            if img_elem:
                img_src = await img_elem.get_attribute('src')
                if img_src and not any(x in img_src.lower() for x in ['logo', 'icon', 'placeholder']):
                    property_data['image_url'] = img_src
                    
            # Área
            area_match = re.search(r'(\d+[\d.,]*)\s*m[²2]', text)
            if area_match:
                property_data['area_total'] = self._parse_number(area_match.group(1))
                
            # Tipo de leilão
            if 'judicial' in text.lower():
                property_data['auction_type'] = 'Judicial'
            elif 'extrajudicial' in text.lower():
                property_data['auction_type'] = 'Extrajudicial'
            else:
                property_data['auction_type'] = 'Extrajudicial'
                
            # Data do leilão
            date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', text)
            if date_match:
                day, month, year = date_match.groups()
                property_data['first_auction_date'] = f"{year}-{month}-{day}"
                
            return property_data
            
        except Exception as e:
            logger.debug(f"Erro ao extrair propriedade: {e}")
            return None
            
    def _extract_location(self, text: str) -> tuple:
        """Extrai estado e cidade do texto."""
        # Padrão: Cidade/UF ou Cidade - UF
        patterns = [
            r'([A-Za-zÀ-ú\s]+)\s*[-/]\s*([A-Z]{2})\b',
            r'([A-Za-zÀ-ú\s]+),\s*([A-Z]{2})\b',
        ]
        
        states = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 
                  'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 
                  'SP', 'SE', 'TO']
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                city = match.group(1).strip()
                state = match.group(2).upper()
                if state in states and len(city) > 2:
                    return state, city.title()
                    
        return None, None
        
    def _determine_category(self, text: str) -> str:
        """Determina categoria do imóvel."""
        text_lower = text.lower()
        
        if 'apartamento' in text_lower or 'apto' in text_lower:
            return 'Apartamento'
        elif 'casa' in text_lower:
            return 'Casa'
        elif 'terreno' in text_lower or 'lote' in text_lower:
            return 'Terreno'
        elif 'sala' in text_lower or 'comercial' in text_lower or 'loja' in text_lower:
            return 'Comercial'
        elif 'galpão' in text_lower or 'galpao' in text_lower:
            return 'Galpão'
        elif 'fazenda' in text_lower or 'rural' in text_lower or 'sítio' in text_lower:
            return 'Rural'
        else:
            return 'Outro'
            
    def _extract_prices(self, text: str) -> Dict:
        """Extrai preços do texto."""
        prices = {}
        
        # Padrões de preço
        patterns = {
            'evaluation_value': [r'avalia[çc][ãa]o[:\s]*R\$\s*([\d.,]+)', r'valor\s+de\s+avalia[çc][ãa]o[:\s]*R\$\s*([\d.,]+)'],
            'first_auction_value': [r'1[ªº°]\s*pra[çc]a[:\s]*R\$\s*([\d.,]+)', r'primeiro\s+leil[ãa]o[:\s]*R\$\s*([\d.,]+)'],
            'second_auction_value': [r'2[ªº°]\s*pra[çc]a[:\s]*R\$\s*([\d.,]+)', r'segundo\s+leil[ãa]o[:\s]*R\$\s*([\d.,]+)'],
        }
        
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    prices[field] = self._parse_number(match.group(1))
                    break
                    
        # Se não encontrou preços específicos, procurar qualquer preço
        if not prices:
            all_prices = re.findall(r'R\$\s*([\d.,]+)', text)
            valid_prices = [self._parse_number(p) for p in all_prices if self._parse_number(p) and self._parse_number(p) > 10000]
            if valid_prices:
                prices['first_auction_value'] = max(valid_prices)
                if len(valid_prices) > 1:
                    prices['second_auction_value'] = min(valid_prices)
                    
        # Calcular desconto
        if prices.get('evaluation_value') and prices.get('second_auction_value'):
            eval_val = prices['evaluation_value']
            second_val = prices['second_auction_value']
            if eval_val > 0:
                prices['discount_percentage'] = round((eval_val - second_val) / eval_val * 100, 1)
                
        return prices
        
    def _parse_number(self, value: str) -> Optional[float]:
        """Converte string de número brasileiro para float."""
        if not value:
            return None
        try:
            clean = re.sub(r'[^\d.,]', '', str(value))
            clean = clean.replace('.', '').replace(',', '.')
            return float(clean)
        except (ValueError, AttributeError):
            return None
            
    async def run(self, leiloeiros: List[Leiloeiro] = None, max_per_leiloeiro: int = 50):
        """Executa scraping de todos os leiloeiros."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("❌ Playwright não disponível. Instale com: pip install playwright && playwright install chromium")
            return
            
        leiloeiros = leiloeiros or TOP_10_LEILOEIROS
        
        logger.info("=" * 70)
        logger.info("🚀 INICIANDO SCRAPING DOS TOP 10 LEILOEIROS")
        logger.info("=" * 70)
        logger.info(f"Total de leiloeiros: {len(leiloeiros)}")
        logger.info(f"Máximo por leiloeiro: {max_per_leiloeiro}")
        logger.info("=" * 70)
        
        try:
            await self.setup_browser()
            
            for i, leiloeiro in enumerate(leiloeiros, 1):
                logger.info(f"\n[{i}/{len(leiloeiros)}] === {leiloeiro.name} ===")
                logger.info(f"URL: {leiloeiro.url}")
                logger.info(f"Esperado: ~{leiloeiro.expected_properties} imóveis")
                
                properties = await self.scrape_leiloeiro(leiloeiro, max_per_leiloeiro)
                self.results[leiloeiro.id] = properties
                
                # Pausa entre leiloeiros
                if i < len(leiloeiros):
                    logger.info("⏳ Aguardando 5 segundos antes do próximo...")
                    await asyncio.sleep(5)
                    
        finally:
            await self.close_browser()
            
        # Relatório final
        self._print_report()
        
        # Salvar no banco
        if self.save_to_db:
            self._save_to_database()
            
        # Salvar JSON
        self._save_json()
        
    def _print_report(self):
        """Imprime relatório final."""
        logger.info("\n" + "=" * 70)
        logger.info("📊 RELATÓRIO FINAL")
        logger.info("=" * 70)
        
        total = 0
        for leiloeiro in TOP_10_LEILOEIROS:
            count = len(self.results.get(leiloeiro.id, []))
            total += count
            status = "✅" if count > 0 else "❌"
            error = self.errors.get(leiloeiro.id, "")
            error_str = f" ({error[:30]}...)" if error else ""
            logger.info(f"{status} {leiloeiro.name:<25} {count:>5} imóveis{error_str}")
            
        logger.info("-" * 70)
        logger.info(f"📈 TOTAL: {total} imóveis coletados")
        logger.info(f"✅ Sucesso: {sum(1 for lid in self.results if len(self.results[lid]) > 0)}/{len(TOP_10_LEILOEIROS)}")
        logger.info(f"❌ Erros: {len(self.errors)}")
        logger.info("=" * 70)
        
    def _save_to_database(self):
        """Salva propriedades no Supabase."""
        if not PSYCOPG2_AVAILABLE:
            logger.warning("⚠️ psycopg2 não disponível, pulando salvamento no banco")
            return
            
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            logger.warning("⚠️ DATABASE_URL não configurada, pulando salvamento")
            return
            
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            saved = 0
            for leiloeiro_id, properties in self.results.items():
                for prop in properties:
                    if not prop.get('title') or not prop.get('source_url'):
                        continue
                        
                    # Gerar ID único
                    prop_id = f"{leiloeiro_id}_{hash(prop['source_url']) % 10000000}"
                    
                    cursor.execute("""
                        INSERT INTO properties (
                            id, title, source_url, auctioneer_id, auctioneer_name,
                            state, city, category, auction_type,
                            evaluation_value, first_auction_value, second_auction_value,
                            discount_percentage, area_total, image_url,
                            first_auction_date, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            evaluation_value = EXCLUDED.evaluation_value,
                            first_auction_value = EXCLUDED.first_auction_value,
                            second_auction_value = EXCLUDED.second_auction_value,
                            updated_at = NOW()
                    """, (
                        prop_id,
                        prop.get('title'),
                        prop.get('source_url'),
                        prop.get('auctioneer_id'),
                        prop.get('auctioneer_name'),
                        prop.get('state'),
                        prop.get('city'),
                        prop.get('category'),
                        prop.get('auction_type'),
                        prop.get('evaluation_value'),
                        prop.get('first_auction_value'),
                        prop.get('second_auction_value'),
                        prop.get('discount_percentage'),
                        prop.get('area_total'),
                        prop.get('image_url'),
                        prop.get('first_auction_date'),
                    ))
                    saved += 1
                    
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"💾 {saved} propriedades salvas no banco de dados")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar no banco: {e}")
            
    def _save_json(self):
        """Salva resultados em JSON."""
        output = {
            'timestamp': datetime.now().isoformat(),
            'total_properties': sum(len(props) for props in self.results.values()),
            'leiloeiros': {}
        }
        
        for leiloeiro in TOP_10_LEILOEIROS:
            output['leiloeiros'][leiloeiro.id] = {
                'name': leiloeiro.name,
                'url': leiloeiro.url,
                'expected': leiloeiro.expected_properties,
                'collected': len(self.results.get(leiloeiro.id, [])),
                'error': self.errors.get(leiloeiro.id),
                'properties': self.results.get(leiloeiro.id, [])
            }
            
        filename = f"top10_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
            
        logger.info(f"📁 Resultados salvos em: {filename}")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scraper TOP 10 Leiloeiros')
    parser.add_argument('--limit', type=int, default=10, help='Limite de leiloeiros a processar')
    parser.add_argument('--max-properties', type=int, default=50, help='Máximo de propriedades por leiloeiro')
    parser.add_argument('--headless', type=str, default='true', help='Executar em modo headless')
    parser.add_argument('--no-db', action='store_true', help='Não salvar no banco de dados')
    
    args = parser.parse_args()
    
    headless = args.headless.lower() != 'false'
    leiloeiros = TOP_10_LEILOEIROS[:args.limit]
    
    scraper = Top10Scraper(headless=headless, save_to_db=not args.no_db)
    await scraper.run(leiloeiros=leiloeiros, max_per_leiloeiro=args.max_properties)


if __name__ == '__main__':
    asyncio.run(main())
