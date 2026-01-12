#!/usr/bin/env python3
"""
SCRAPER TOP 10 LEILOEIROS - LeiloHub (VERSÃO CORRIGIDA)
========================================================

Script corrigido com seletores específicos para cada leiloeiro.
Testado e validado em 12/01/2026.

Correções aplicadas:
- ARG Leilões: OK (funcionando)
- Realiza Leilões: OK (funcionando)
- Isaias Leilões: Corrigido path "/" e seletor
- Leilões Ceruli: Corrigido path e seletor
- MGL: Corrigido para usar "/leilao/" e seletor específico
- Demais: Ajustados seletores

Uso:
    python SCRAPER_TOP10_CORRIGIDO.py
    python SCRAPER_TOP10_CORRIGIDO.py --limit 5
    python SCRAPER_TOP10_CORRIGIDO.py --headless false
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
# CONFIGURAÇÃO DOS TOP 10 LEILOEIROS (CORRIGIDA)
# =============================================================================

@dataclass
class Leiloeiro:
    id: str
    name: str
    url: str
    expected_properties: int
    property_list_path: str
    property_selector: str
    alt_selectors: List[str] = None  # Seletores alternativos


TOP_10_LEILOEIROS = [
    # ✅ FUNCIONANDO
    Leiloeiro(
        id="arg_leiloes",
        name="ARG Leilões",
        url="https://www.argleiloes.com.br",
        expected_properties=599,
        property_list_path="/",
        property_selector="a[href*='/leilao/']",
        alt_selectors=["a[href*='/item/']", ".leilao-card a"]
    ),
    # ✅ FUNCIONANDO
    Leiloeiro(
        id="realiza_leiloes",
        name="Realiza Leilões",
        url="https://www.realizaleiloes.com.br",
        expected_properties=598,
        property_list_path="/leiloes",
        property_selector="a[href*='/leilao/']",
        alt_selectors=["a[href*='/item/']", ".card-leilao a"]
    ),
    # CORRIGIDO - Isaias usa mesmo padrão de ARG/Realiza
    Leiloeiro(
        id="isaias_leiloes",
        name="Isaias Leilões",
        url="https://www.isaiasleiloes.com.br",
        expected_properties=544,
        property_list_path="/",  # Corrigido de "/imoveis" para "/"
        property_selector="a[href*='/leilao/']",
        alt_selectors=["a[href*='/item/']", ".leilao-item a"]
    ),
    # CORRIGIDO - Ceruli usa mesmo sistema
    Leiloeiro(
        id="leiloes_ceruli",
        name="Leilões Ceruli",
        url="https://www.leiloesceruli.com.br",
        expected_properties=537,
        property_list_path="/",
        property_selector="a[href*='/leilao/']",
        alt_selectors=["a[href*='/item/']", "a[href*='/lotes/']"]
    ),
    # CORRIGIDO - MGL tem estrutura diferente
    Leiloeiro(
        id="mgl_leiloes",
        name="MGL Leilões",
        url="https://www.mgl.com.br",
        expected_properties=447,
        property_list_path="/",
        property_selector="a[href*='/leilao/']",
        alt_selectors=["a[href*='/lote/']", ".card-leilao a", "a.leilao-link"]
    ),
    # Leilões RN
    Leiloeiro(
        id="leiloes_rn",
        name="Leilões RN",
        url="https://www.leiloesrn.com.br",
        expected_properties=321,
        property_list_path="/",
        property_selector="a[href*='/leilao/'], a[href*='/imovel/']",
        alt_selectors=["a[href*='/lote/']", ".property-card a"]
    ),
    # Grupo Lance
    Leiloeiro(
        id="grupo_lance",
        name="Grupo Lance",
        url="https://www.grupolance.com.br",
        expected_properties=247,
        property_list_path="/",
        property_selector="a[href*='/leilao/'], a[href*='/imovel/']",
        alt_selectors=["a[href*='/lote/']", ".card a"]
    ),
    # LB Leilões
    Leiloeiro(
        id="lb_leiloes",
        name="LB Leilões",
        url="https://www.lbleiloes.com.br",
        expected_properties=213,
        property_list_path="/",
        property_selector="a[href*='/leilao/'], a[href*='/lote/']",
        alt_selectors=["a[href*='/imovel/']", ".leilao a"]
    ),
    # Globo Leilões
    Leiloeiro(
        id="globo_leiloes",
        name="Globo Leilões",
        url="https://globoleiloes.com.br",
        expected_properties=209,
        property_list_path="/",
        property_selector="a[href*='/leilao/'], a[href*='/imovel/']",
        alt_selectors=["a[href*='/lote/']", ".auction-card a"]
    ),
    # TrustBid
    Leiloeiro(
        id="trustbid_leiloes",
        name="TrustBid Leilões",
        url="https://www.trustbid.com.br",
        expected_properties=188,
        property_list_path="/",
        property_selector="a[href*='/leilao/'], a[href*='/lote/']",
        alt_selectors=["a[href*='/auction/']", ".bid-card a"]
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
Object.defineProperty(navigator, 'webdriver', { get: () => false });
delete navigator.__proto__.webdriver;
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', description: 'Portable Document Format' },
        { name: 'Chrome PDF Viewer', description: '' },
        { name: 'Native Client', description: '' }
    ]
});
Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} };
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
"""

BROWSER_CONTEXT_OPTIONS = {
    'viewport': {'width': 1920, 'height': 1080},
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'locale': 'pt-BR',
    'timezone_id': 'America/Sao_Paulo',
    'extra_http_headers': {
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
}


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class Top10Scraper:
    """Scraper para os TOP 10 leiloeiros (versão corrigida)."""
    
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
            
            # Scroll para carregar conteúdo
            await self._scroll_page()
            
            # Tentar seletor principal
            property_links = await self.page.query_selector_all(leiloeiro.property_selector)
            
            # Se não encontrou, tentar seletores alternativos
            if len(property_links) == 0 and leiloeiro.alt_selectors:
                for alt_selector in leiloeiro.alt_selectors:
                    logger.info(f"  Tentando seletor alternativo: {alt_selector}")
                    property_links = await self.page.query_selector_all(alt_selector)
                    if len(property_links) > 0:
                        break
            
            # Extrair URLs únicas
            urls = set()
            for link in property_links:
                href = await link.get_attribute('href')
                if href:
                    if href.startswith('/'):
                        href = f"{leiloeiro.url}{href}"
                    # Filtrar apenas URLs do próprio site
                    if leiloeiro.url.replace('https://', '').replace('http://', '').replace('www.', '') in href.replace('www.', ''):
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
                    await asyncio.sleep(1.5)
                except Exception as e:
                    logger.warning(f"  ❌ Erro: {str(e)[:50]}")
                    
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
        except Exception:
            pass
            
    async def _extract_property(self, url: str, leiloeiro: Leiloeiro) -> Optional[Dict]:
        """Extrai dados de uma propriedade."""
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
            
            html = await self.page.content()
            text = await self.page.evaluate("() => document.body.innerText || ''")
            
            property_data = {
                'source_url': url,
                'auctioneer_id': leiloeiro.id,
                'auctioneer_name': leiloeiro.name,
                'auctioneer_url': leiloeiro.url,
            }
            
            # Título - múltiplos seletores
            for selector in ['h1', 'h2.title', '.titulo-lote', '.property-title', '.leilao-title']:
                title_elem = await self.page.query_selector(selector)
                if title_elem:
                    title_text = await title_elem.inner_text()
                    if title_text and len(title_text.strip()) > 5:
                        property_data['title'] = title_text.strip()[:200]
                        break
                    
            # Fallback: regex no HTML
            if not property_data.get('title'):
                title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
                if title_match:
                    property_data['title'] = title_match.group(1).strip()[:200]
                    
            # Localização
            state, city = self._extract_location(text + ' ' + html)
            property_data['state'] = state
            property_data['city'] = city
            
            # Categoria
            property_data['category'] = self._determine_category(property_data.get('title', '') + ' ' + text)
            
            # Preços
            prices = self._extract_prices(text + ' ' + html)
            property_data.update(prices)
            
            # Imagem
            for selector in ['img.property-image', 'img.lote-image', '.gallery img', '.carousel img', '.foto-principal img']:
                img_elem = await self.page.query_selector(selector)
                if img_elem:
                    img_src = await img_elem.get_attribute('src')
                    if img_src and not any(x in img_src.lower() for x in ['logo', 'icon', 'placeholder', 'banner']):
                        if img_src.startswith('/'):
                            img_src = f"{leiloeiro.url}{img_src}"
                        property_data['image_url'] = img_src
                        break
                    
            # Área
            area_match = re.search(r'(\d+[\d.,]*)\s*m[²2]', text)
            if area_match:
                property_data['area_total'] = self._parse_number(area_match.group(1))
                
            # Tipo de leilão
            text_lower = text.lower()
            if 'judicial' in text_lower and 'extrajudicial' not in text_lower:
                property_data['auction_type'] = 'Judicial'
            else:
                property_data['auction_type'] = 'Extrajudicial'
                
            # Data do leilão
            date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', text)
            if date_match:
                day, month, year = date_match.groups()
                property_data['first_auction_date'] = f"{year}-{month}-{day}"
                
            return property_data
            
        except Exception as e:
            logger.debug(f"Erro ao extrair: {e}")
            return None
            
    def _extract_location(self, text: str) -> tuple:
        """Extrai estado e cidade."""
        states = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 
                  'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 
                  'SP', 'SE', 'TO']
        
        patterns = [
            r'([A-Za-zÀ-ú\s]+)\s*[-/]\s*([A-Z]{2})\b',
            r'([A-Za-zÀ-ú\s]+),\s*([A-Z]{2})\b',
            r'em\s+([A-Za-zÀ-ú\s]+)/([A-Z]{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                city = match.group(1).strip()
                state = match.group(2).upper()
                if state in states and 2 < len(city) < 50:
                    return state, city.title()
                    
        return None, None
        
    def _determine_category(self, text: str) -> str:
        """Determina categoria."""
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
        return 'Outro'
            
    def _extract_prices(self, text: str) -> Dict:
        """Extrai preços."""
        prices = {}
        
        patterns = {
            'evaluation_value': [r'avalia[çc][ãa]o[:\s]*R\$\s*([\d.,]+)'],
            'first_auction_value': [r'1[ªº°]\s*(?:pra[çc]a|leil[ãa]o)[:\s]*R\$\s*([\d.,]+)'],
            'second_auction_value': [r'2[ªº°]\s*(?:pra[çc]a|leil[ãa]o)[:\s]*R\$\s*([\d.,]+)'],
        }
        
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    prices[field] = self._parse_number(match.group(1))
                    break
                    
        if not prices:
            all_prices = re.findall(r'R\$\s*([\d.,]+)', text)
            valid_prices = [self._parse_number(p) for p in all_prices if self._parse_number(p) and self._parse_number(p) > 10000]
            if valid_prices:
                prices['first_auction_value'] = max(valid_prices)
                if len(valid_prices) > 1:
                    prices['second_auction_value'] = min(valid_prices)
                    
        if prices.get('evaluation_value') and prices.get('second_auction_value'):
            eval_val = prices['evaluation_value']
            second_val = prices['second_auction_value']
            if eval_val > 0:
                prices['discount_percentage'] = round((eval_val - second_val) / eval_val * 100, 1)
                
        return prices
        
    def _parse_number(self, value: str) -> Optional[float]:
        """Converte string para float."""
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
            logger.error("❌ Playwright não disponível")
            return
            
        leiloeiros = leiloeiros or TOP_10_LEILOEIROS
        
        logger.info("=" * 70)
        logger.info("🚀 SCRAPING TOP 10 LEILOEIROS (VERSÃO CORRIGIDA)")
        logger.info("=" * 70)
        logger.info(f"Total: {len(leiloeiros)} | Máx/leiloeiro: {max_per_leiloeiro}")
        logger.info("=" * 70)
        
        try:
            await self.setup_browser()
            
            for i, leiloeiro in enumerate(leiloeiros, 1):
                logger.info(f"\n[{i}/{len(leiloeiros)}] === {leiloeiro.name} ===")
                
                properties = await self.scrape_leiloeiro(leiloeiro, max_per_leiloeiro)
                self.results[leiloeiro.id] = properties
                
                if i < len(leiloeiros):
                    logger.info("⏳ Aguardando 5s...")
                    await asyncio.sleep(5)
                    
        finally:
            await self.close_browser()
            
        self._print_report()
        
        if self.save_to_db:
            self._save_to_database()
            
        self._save_json()
        
    def _print_report(self):
        """Imprime relatório."""
        logger.info("\n" + "=" * 70)
        logger.info("📊 RELATÓRIO FINAL")
        logger.info("=" * 70)
        
        total = 0
        success = 0
        for leiloeiro in TOP_10_LEILOEIROS:
            count = len(self.results.get(leiloeiro.id, []))
            total += count
            if count > 0:
                success += 1
            status = "✅" if count > 0 else "❌"
            logger.info(f"{status} {leiloeiro.name:<25} {count:>5} imóveis")
            
        logger.info("-" * 70)
        logger.info(f"📈 TOTAL: {total} imóveis")
        logger.info(f"✅ Sucesso: {success}/{len(TOP_10_LEILOEIROS)}")
        logger.info("=" * 70)
        
    def _save_to_database(self):
        """Salva no Supabase."""
        if not PSYCOPG2_AVAILABLE:
            logger.warning("⚠️ psycopg2 não disponível")
            return
            
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            logger.warning("⚠️ DATABASE_URL não configurada")
            return
            
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            saved = 0
            for leiloeiro_id, properties in self.results.items():
                for prop in properties:
                    if not prop.get('title') or not prop.get('source_url'):
                        continue
                        
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
            
            logger.info(f"💾 {saved} propriedades salvas no banco")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar: {e}")
            
    def _save_json(self):
        """Salva JSON."""
        output = {
            'timestamp': datetime.now().isoformat(),
            'total_properties': sum(len(props) for props in self.results.values()),
            'leiloeiros': {}
        }
        
        for leiloeiro in TOP_10_LEILOEIROS:
            output['leiloeiros'][leiloeiro.id] = {
                'name': leiloeiro.name,
                'collected': len(self.results.get(leiloeiro.id, [])),
                'error': self.errors.get(leiloeiro.id),
                'properties': self.results.get(leiloeiro.id, [])
            }
            
        filename = f"top10_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
            
        logger.info(f"📁 Salvos em: {filename}")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scraper TOP 10 (Corrigido)')
    parser.add_argument('--limit', type=int, default=10, help='Limite de leiloeiros')
    parser.add_argument('--max-properties', type=int, default=50, help='Máx propriedades/leiloeiro')
    parser.add_argument('--headless', type=str, default='true', help='Modo headless')
    parser.add_argument('--no-db', action='store_true', help='Não salvar no banco')
    
    args = parser.parse_args()
    
    headless = args.headless.lower() != 'false'
    leiloeiros = TOP_10_LEILOEIROS[:args.limit]
    
    scraper = Top10Scraper(headless=headless, save_to_db=not args.no_db)
    await scraper.run(leiloeiros=leiloeiros, max_per_leiloeiro=args.max_properties)


if __name__ == '__main__':
    asyncio.run(main())
