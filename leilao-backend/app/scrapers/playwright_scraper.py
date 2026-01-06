"""
Playwright Scraper - Scraper base usando Playwright para automação de browser.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class PlaywrightScraper:
    """Scraper base usando Playwright para automação de browser."""
    
    def __init__(self, headless: bool = True, timeout: float = 30000.0):
        """
        Inicializa o scraper Playwright.
        
        Args:
            headless: Se deve executar em modo headless
            timeout: Timeout em milissegundos para ações do Playwright
        """
        self.headless = headless
        self.timeout = timeout
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def start(self) -> bool:
        """
        Inicia o browser Playwright.
        
        Returns:
            True se iniciou com sucesso, False caso contrário
        """
        try:
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
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
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
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
            
            self.page = await self.context.new_page()
            
            # Injetar scripts de stealth para ocultar automação
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en']
                });
            """)
            
            logger.info("Browser Playwright iniciado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao iniciar browser Playwright: {e}")
            return False
    
    async def stop(self) -> None:
        """Para e fecha o browser Playwright."""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            logger.info("Browser Playwright fechado")
        except Exception as e:
            logger.error(f"Erro ao fechar browser Playwright: {e}")
    
    async def navigate(self, url: str, wait_until: str = 'domcontentloaded', 
                      timeout: Optional[float] = None) -> bool:
        """
        Navega para uma URL.
        
        Args:
            url: URL para navegar
            wait_until: Quando considerar a navegação completa ('load', 'domcontentloaded', 'networkidle')
            timeout: Timeout em milissegundos (usa self.timeout se None)
        
        Returns:
            True se navegou com sucesso, False caso contrário
        """
        if not self.page:
            if not await self.start():
                return False
        
        try:
            timeout_val = timeout if timeout is not None else self.timeout
            await self.page.goto(url, wait_until=wait_until, timeout=timeout_val)
            return True
        except Exception as e:
            logger.error(f"Erro ao navegar para {url}: {e}")
            return False
    
    async def get_content(self) -> Optional[str]:
        """
        Retorna o conteúdo HTML da página atual.
        
        Returns:
            HTML como string ou None em caso de erro
        """
        if not self.page:
            return None
        
        try:
            return await self.page.content()
        except Exception as e:
            logger.error(f"Erro ao obter conteúdo da página: {e}")
            return None
    
    async def wait_for_selector(self, selector: str, timeout: Optional[float] = None) -> bool:
        """
        Espera um seletor aparecer na página.
        
        Args:
            selector: Seletor CSS
            timeout: Timeout em milissegundos (usa self.timeout se None)
        
        Returns:
            True se o elemento apareceu, False caso contrário
        """
        if not self.page:
            return False
        
        try:
            timeout_val = timeout if timeout is not None else self.timeout
            await self.page.wait_for_selector(selector, timeout=timeout_val)
            return True
        except Exception as e:
            logger.debug(f"Seletor {selector} não encontrado: {e}")
            return False
    
    async def click(self, selector: str, timeout: Optional[float] = None) -> bool:
        """
        Clica em um elemento.
        
        Args:
            selector: Seletor CSS do elemento
            timeout: Timeout em milissegundos (usa self.timeout se None)
        
        Returns:
            True se clicou com sucesso, False caso contrário
        """
        if not self.page:
            return False
        
        try:
            timeout_val = timeout if timeout is not None else self.timeout
            await self.page.click(selector, timeout=timeout_val)
            return True
        except Exception as e:
            logger.error(f"Erro ao clicar em {selector}: {e}")
            return False
    
    async def evaluate(self, script: str) -> Any:
        """
        Executa JavaScript na página.
        
        Args:
            script: Código JavaScript para executar
        
        Returns:
            Resultado da execução do script
        """
        if not self.page:
            return None
        
        try:
            return await self.page.evaluate(script)
        except Exception as e:
            logger.error(f"Erro ao executar script: {e}")
            return None
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()
