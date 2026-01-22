"""
Playwright Stealth Scraper - Bypass Cloudflare
Scraper genérico com Playwright Stealth para sites protegidos

PARTE 3.3 - FASE 3
"""

import asyncio
import logging
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class PlaywrightStealthScraper:
    """Scraper genérico com Playwright Stealth para bypass de Cloudflare"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    async def _setup_browser(self):
        """Setup Playwright com configuração stealth"""
        if self.playwright:
            return
            
        self.playwright = await async_playwright().start()
        
        # Launch browser com argumentos stealth
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        
        # Criar contexto com headers realistas
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        )
        
        self.page = await context.new_page()
        
        # Injetar scripts stealth
        await self.page.add_init_script("""
            // Stealth mode scripts
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
            
            // Chrome runtime
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Plugin mocking
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }
                ],
            });
        """)
        
        logger.info("Playwright Stealth configurado")
        
    async def _close_browser(self):
        """Fecha o browser"""
        if self.page:
            await self.page.close()
            self.page = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def scrape_with_stealth(self, url: str, wait_seconds: int = 5) -> Dict:
        """
        Scrape um site usando Playwright Stealth
        
        Args:
            url: URL do site
            wait_seconds: Segundos para aguardar após carregar
            
        Returns:
            Dict com HTML, cards encontrados, links, etc.
        """
        try:
            await self._setup_browser()
            
            logger.info(f"Acessando {url} com Playwright Stealth...")
            
            # Navegar com retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.page.goto(url, wait_until='networkidle', timeout=60000)
                    break
                except PlaywrightTimeoutError:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Timeout na tentativa {attempt + 1}, tentando novamente...")
                    await asyncio.sleep(2)
            
            # Aguardar carregamento dinâmico
            await asyncio.sleep(wait_seconds)
            
            # Scroll para carregar lazy content
            await self._scroll_page()
            
            # Obter HTML
            html = await self.page.content()
            
            # Verificar se passou pelo Cloudflare
            if 'cloudflare' in html.lower() and 'checking your browser' in html.lower():
                logger.warning("Cloudflare challenge detectado, aguardando...")
                await asyncio.sleep(10)
                html = await self.page.content()
            
            # Analisar com BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Procurar por cards/itens de propriedades
            card_selectors = [
                'div[class*="card"]',
                'div[class*="item"]',
                'div[class*="lote"]',
                'div[class*="property"]',
                'div[class*="imovel"]',
                'article'
            ]
            
            all_cards = []
            for selector in card_selectors:
                cards = soup.select(selector)
                if cards:
                    all_cards.extend(cards)
                    logger.info(f"  {selector}: {len(cards)} elementos")
            
            # Procurar links de propriedades
            links = soup.select('a[href]')
            property_links = [
                a.get('href') for a in links 
                if a.get('href') and any(kw in a.get('href', '').lower() 
                    for kw in ['imovel', 'lote', 'property', 'detalhes', 'leilao'])
            ]
            
            # Contar palavras-chave
            html_lower = html.lower()
            keywords = ['imovel', 'imoveis', 'apartamento', 'casa', 'terreno', 'leilao', 'lance']
            keyword_count = sum(1 for kw in keywords if kw in html_lower)
            
            result = {
                'success': True,
                'url': url,
                'final_url': self.page.url,
                'html_size': len(html),
                'cards_found': len(set(str(c) for c in all_cards)),  # Unique cards
                'property_links': len(set(property_links)),  # Unique links
                'keyword_count': keyword_count,
                'html_content': html,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Scraping completo: {result['cards_found']} cards, {result['property_links']} links")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao fazer scraping: {e}")
            return {
                'success': False,
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        finally:
            await self._close_browser()
    
    async def _scroll_page(self):
        """Scroll na página para carregar conteúdo lazy"""
        try:
            await self.page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 100;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            
                            if(totalHeight >= scrollHeight){
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            await asyncio.sleep(1)
        except Exception as e:
            logger.debug(f"Erro ao fazer scroll: {e}")
    
    async def test_multiple_sites(self, sites: List[Dict]) -> List[Dict]:
        """
        Testa múltiplos sites
        
        Args:
            sites: Lista de dicts com 'id', 'name', 'website'
            
        Returns:
            Lista de resultados
        """
        results = []
        
        for i, site in enumerate(sites):
            logger.info(f"\n[{i+1}/{len(sites)}] Testando {site['name']}...")
            
            result = await self.scrape_with_stealth(site['website'])
            result['auctioneer_id'] = site['id']
            result['auctioneer_name'] = site['name']
            results.append(result)
            
            # Delay entre requests
            if i < len(sites) - 1:
                await asyncio.sleep(2)
        
        return results


async def test_cloudflare_sites():
    """Testa alguns sites protegidos por Cloudflare"""
    
    # Carregar lista de sites Cloudflare
    import json
    with open('verificacao_completa_20260122_101237.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cloudflare_sites = data['cloudflare_protected'][:5]  # Testar primeiros 5
    
    print("="*70)
    print("TESTANDO PLAYWRIGHT STEALTH EM SITES CLOUDFLARE")
    print("="*70)
    
    scraper = PlaywrightStealthScraper(headless=True)
    results = await scraper.test_multiple_sites(cloudflare_sites)
    
    # Resumo
    print("\n" + "="*70)
    print("RESUMO DOS TESTES")
    print("="*70)
    
    successful = sum(1 for r in results if r.get('success') and r.get('cards_found', 0) > 0)
    
    for result in results:
        status = "OK" if result.get('success') and result.get('cards_found', 0) > 0 else "FALHOU"
        print(f"\n{result.get('auctioneer_name')}: {status}")
        if result.get('success'):
            print(f"  Cards: {result.get('cards_found', 0)}")
            print(f"  Links: {result.get('property_links', 0)}")
            print(f"  Keywords: {result.get('keyword_count', 0)}")
        else:
            print(f"  Erro: {result.get('error', 'Unknown')}")
    
    print(f"\n{successful}/{len(results)} sites extraídos com sucesso")
    
    # Salvar resultados
    with open('playwright_stealth_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\nResultados salvos em: playwright_stealth_test_results.json")


if __name__ == "__main__":
    asyncio.run(test_cloudflare_sites())
