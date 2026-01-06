# ============================================================
# TAREFA AUTÔNOMA: Infraestrutura Base
# ============================================================
# Para: Cursor Agent
# Modo: AUTÔNOMO - Executar sem parar para perguntar
# ============================================================

"""
INSTRUÇÕES PARA O CURSOR AGENT:

1. Execute este script no diretório leilao-backend
2. O script criará a infraestrutura base necessária
3. Verifique os arquivos criados
4. Teste a importação

NÃO PARE PARA PERGUNTAR - Execute até o fim!
"""

import os
import sys

# ============================================================
# CÓDIGO PARA: app/configs/config_manager.py
# ============================================================

CODIGO_CONFIG_MANAGER = '''"""
Config Manager - Gerencia configurações de sites de leilões.
"""
import os
import json
import logging
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigManager:
    """Gerencia configurações de sites de leilões."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Inicializa o ConfigManager.
        
        Args:
            config_dir: Diretório onde estão os arquivos de configuração.
                       Default: app/configs/sites/
        """
        if config_dir is None:
            # Tenta encontrar o diretório relativo ao módulo
            base_path = Path(__file__).parent.parent.parent
            config_dir = base_path / "app" / "configs" / "sites"
        else:
            config_dir = Path(config_dir)
        
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict] = {}
    
    def get_config(self, site_name: str) -> Optional[Dict[str, Any]]:
        """
        Carrega configuração de um site.
        
        Args:
            site_name: Nome do site (sem extensão .json)
        
        Returns:
            Dict com configuração ou None se não encontrado
        """
        if site_name in self._cache:
            return self._cache[site_name]
        
        config_file = self.config_dir / f"{site_name}.json"
        
        if not config_file.exists():
            logger.warning(f"Arquivo de configuração não encontrado: {config_file}")
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self._cache[site_name] = config
                return config
        except Exception as e:
            logger.error(f"Erro ao carregar configuração {site_name}: {e}")
            return None
    
    def save_config(self, site_name: str, config: Dict[str, Any]) -> bool:
        """
        Salva configuração de um site.
        
        Args:
            site_name: Nome do site (sem extensão .json)
            config: Dict com configuração
        
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        config_file = self.config_dir / f"{site_name}.json"
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self._cache[site_name] = config
            logger.info(f"Configuração salva: {config_file}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configuração {site_name}: {e}")
            return False
    
    def list_configs(self) -> list[str]:
        """
        Lista todos os sites configurados.
        
        Returns:
            Lista de nomes de sites (sem extensão .json)
        """
        if not self.config_dir.exists():
            return []
        
        configs = []
        for file in self.config_dir.glob("*.json"):
            configs.append(file.stem)
        
        return sorted(configs)
    
    def delete_config(self, site_name: str) -> bool:
        """
        Deleta configuração de um site.
        
        Args:
            site_name: Nome do site (sem extensão .json)
        
        Returns:
            True se deletou com sucesso, False caso contrário
        """
        config_file = self.config_dir / f"{site_name}.json"
        
        if not config_file.exists():
            return False
        
        try:
            config_file.unlink()
            if site_name in self._cache:
                del self._cache[site_name]
            logger.info(f"Configuração deletada: {config_file}")
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar configuração {site_name}: {e}")
            return False
'''

# ============================================================
# CÓDIGO PARA: app/scrapers/httpx_scraper.py
# ============================================================

CODIGO_HTTPX_SCRAPER = '''"""
HTTPX Scraper - Scraper base usando httpx para requisições HTTP assíncronas.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HttpxScraper:
    """Scraper base usando httpx para requisições HTTP assíncronas."""
    
    def __init__(self, timeout: float = 30.0, headers: Optional[Dict[str, str]] = None):
        """
        Inicializa o scraper httpx.
        
        Args:
            timeout: Timeout em segundos para requisições
            headers: Headers customizados (opcional)
        """
        self.timeout = timeout
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        if headers:
            self.default_headers.update(headers)
    
    async def fetch(self, url: str, headers: Optional[Dict[str, str]] = None, 
                    follow_redirects: bool = True) -> Optional[httpx.Response]:
        """
        Faz uma requisição HTTP GET.
        
        Args:
            url: URL para fazer a requisição
            headers: Headers adicionais (opcional)
            follow_redirects: Se deve seguir redirects
        
        Returns:
            Response object ou None em caso de erro
        """
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=follow_redirects,
                verify=False  # Para desenvolvimento, em produção usar True
            ) as client:
                response = await client.get(url, headers=request_headers)
                return response
        except Exception as e:
            logger.error(f"Erro ao fazer requisição para {url}: {e}")
            return None
    
    async def fetch_html(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Faz uma requisição HTTP GET e retorna o HTML.
        
        Args:
            url: URL para fazer a requisição
            headers: Headers adicionais (opcional)
        
        Returns:
            HTML como string ou None em caso de erro
        """
        response = await self.fetch(url, headers)
        
        if response and response.status_code == 200:
            return response.text
        else:
            if response:
                logger.warning(f"Status code {response.status_code} para {url}")
            return None
    
    async def fetch_soup(self, url: str, headers: Optional[Dict[str, str]] = None, 
                        parser: str = 'html.parser') -> Optional[BeautifulSoup]:
        """
        Faz uma requisição HTTP GET e retorna BeautifulSoup object.
        
        Args:
            url: URL para fazer a requisição
            headers: Headers adicionais (opcional)
            parser: Parser do BeautifulSoup (default: 'html.parser')
        
        Returns:
            BeautifulSoup object ou None em caso de erro
        """
        html = await self.fetch_html(url, headers)
        
        if html:
            return BeautifulSoup(html, parser)
        return None
    
    async def post(self, url: str, data: Optional[Dict] = None, 
                  json_data: Optional[Dict] = None,
                  headers: Optional[Dict[str, str]] = None) -> Optional[httpx.Response]:
        """
        Faz uma requisição HTTP POST.
        
        Args:
            url: URL para fazer a requisição
            data: Dados para enviar como form data
            json_data: Dados para enviar como JSON
            headers: Headers adicionais (opcional)
        
        Returns:
            Response object ou None em caso de erro
        """
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                verify=False
            ) as client:
                if json_data:
                    response = await client.post(url, json=json_data, headers=request_headers)
                elif data:
                    response = await client.post(url, data=data, headers=request_headers)
                else:
                    response = await client.post(url, headers=request_headers)
                return response
        except Exception as e:
            logger.error(f"Erro ao fazer POST para {url}: {e}")
            return None
'''

# ============================================================
# CÓDIGO PARA: app/scrapers/playwright_scraper.py
# ============================================================

CODIGO_PLAYWRIGHT_SCRAPER = '''"""
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
'''

# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def criar_arquivos():
    """Cria todos os arquivos necessários."""
    
    base_dir = Path(__file__).parent
    app_dir = base_dir / "app"
    
    arquivos_criados = []
    arquivos_erro = []
    
    # 1. Criar app/configs/config_manager.py
    configs_dir = app_dir / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    
    config_manager_file = configs_dir / "config_manager.py"
    try:
        with open(config_manager_file, 'w', encoding='utf-8') as f:
            f.write(CODIGO_CONFIG_MANAGER)
        arquivos_criados.append(str(config_manager_file))
        print(f"[OK] Criado: {config_manager_file}")
    except Exception as e:
        arquivos_erro.append((str(config_manager_file), str(e)))
        print(f"[ERRO] Erro ao criar {config_manager_file}: {e}")
    
    # 2. Criar app/configs/sites/ (diretório)
    sites_dir = configs_dir / "sites"
    sites_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Diretorio criado/verificado: {sites_dir}")
    
    # 3. Criar app/configs/__init__.py se não existir
    init_file = configs_dir / "__init__.py"
    if not init_file.exists():
        try:
            init_file.touch()
            print(f"[OK] Criado: {init_file}")
        except Exception as e:
            print(f"[AVISO] Aviso ao criar {init_file}: {e}")
    
    # 4. Criar app/scrapers/httpx_scraper.py
    scrapers_dir = app_dir / "scrapers"
    httpx_scraper_file = scrapers_dir / "httpx_scraper.py"
    
    # Verificar se já existe (não sobrescrever se existir)
    if httpx_scraper_file.exists():
        print(f"[AVISO] Arquivo ja existe (pulando): {httpx_scraper_file}")
    else:
        try:
            with open(httpx_scraper_file, 'w', encoding='utf-8') as f:
                f.write(CODIGO_HTTPX_SCRAPER)
            arquivos_criados.append(str(httpx_scraper_file))
            print(f"[OK] Criado: {httpx_scraper_file}")
        except Exception as e:
            arquivos_erro.append((str(httpx_scraper_file), str(e)))
            print(f"[ERRO] Erro ao criar {httpx_scraper_file}: {e}")
    
    # 5. Criar app/scrapers/playwright_scraper.py
    playwright_scraper_file = scrapers_dir / "playwright_scraper.py"
    
    # Verificar se já existe (não sobrescrever se existir)
    if playwright_scraper_file.exists():
        print(f"[AVISO] Arquivo ja existe (pulando): {playwright_scraper_file}")
    else:
        try:
            with open(playwright_scraper_file, 'w', encoding='utf-8') as f:
                f.write(CODIGO_PLAYWRIGHT_SCRAPER)
            arquivos_criados.append(str(playwright_scraper_file))
            print(f"[OK] Criado: {playwright_scraper_file}")
        except Exception as e:
            arquivos_erro.append((str(playwright_scraper_file), str(e)))
            print(f"[ERRO] Erro ao criar {playwright_scraper_file}: {e}")
    
    # 6. Verificar app/scrapers/base_scraper.py (já existe, apenas verificar)
    base_scraper_file = scrapers_dir / "base_scraper.py"
    if base_scraper_file.exists():
        print(f"[OK] Verificado: {base_scraper_file} (ja existe)")
    else:
        print(f"[AVISO] Atencao: {base_scraper_file} nao existe (esperado que exista)")
    
    # 7. Verificar app/services/scraper_orchestrator.py (já existe, apenas verificar)
    services_dir = app_dir / "services"
    scraper_orchestrator_file = services_dir / "scraper_orchestrator.py"
    if scraper_orchestrator_file.exists():
        print(f"[OK] Verificado: {scraper_orchestrator_file} (ja existe)")
    else:
        print(f"[AVISO] Atencao: {scraper_orchestrator_file} nao existe (esperado que exista)")
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO")
    print("="*60)
    print(f"Arquivos criados: {len(arquivos_criados)}")
    print(f"Erros: {len(arquivos_erro)}")
    
    if arquivos_erro:
        print("\nErros encontrados:")
        for arquivo, erro in arquivos_erro:
            print(f"  - {arquivo}: {erro}")
    
    return len(arquivos_erro) == 0

if __name__ == "__main__":
    from pathlib import Path
    
    print("="*60)
    print("TAREFA: Infraestrutura Base")
    print("="*60)
    print()
    
    sucesso = criar_arquivos()
    
    print()
    if sucesso:
        print("[OK] Tarefa concluida com sucesso!")
        sys.exit(0)
    else:
        print("[ERRO] Tarefa concluida com erros. Verifique os logs acima.")
        sys.exit(1)

