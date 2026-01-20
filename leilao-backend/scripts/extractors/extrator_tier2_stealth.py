#!/usr/bin/env python3
"""EXTRATOR TIER 2: Playwright com Stealth - Para sites com CloudFlare ou proteção anti-bot básica"""
import asyncio, json, re, sys, codecs
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Browser, Page
import logging

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("logs/extracao_fase2/tier2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class ExtratorTier2:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.resultados, self.falhas, self.promocoes_tier3 = [], [], []
        
    async def setup_browser(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled', '--disable-features=IsolateOrigins,site-per-process',
            '--window-size=1920,1080', '--disable-web-security'])
        
    async def criar_contexto_stealth(self):
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR', timezone_id='America/Sao_Paulo',
            extra_http_headers={'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'})
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            delete navigator.__proto__.webdriver;
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        """)
        return context
        
    async def extrair_site(self, dominio: str, config_paginacao: Optional[Dict] = None) -> Dict:
        url_base = f"https://www.{dominio}"
        logger.info(f"🔍 Extraindo (Stealth): {dominio}")
        
        resultado = {"dominio": dominio, "url_base": url_base, "timestamp": datetime.now().isoformat(),
                    "tier": "TIER_2_STEALTH", "sucesso": False, "imoveis": [], "total_imoveis": 0,
                    "paginas_processadas": 0, "bloqueio_detectado": None, "erro": None}
        
        context, page = None, None
        try:
            context = await self.criar_contexto_stealth()
            page = await context.new_page()
            url_imoveis = self._construir_url_imoveis(url_base, dominio)
            
            response = await page.goto(url_imoveis, wait_until='domcontentloaded', timeout=45000)
            await asyncio.sleep(3)
            
            content = await page.content()
            bloqueio = self._detectar_bloqueio(content)
            
            if bloqueio:
                resultado["bloqueio_detectado"] = bloqueio
                logger.warning(f"   ⚠️ Bloqueio: {bloqueio}")
                if "CLOUDFLARE" in bloqueio:
                    self.promocoes_tier3.append(dominio)
                    resultado["erro"] = f"Promovido para TIER 3: {bloqueio}"
                    return resultado
            
            await self._scroll_pagina(page)
            imoveis = await self._extrair_imoveis_pagina(page, url_imoveis)
            resultado["imoveis"].extend(imoveis)
            resultado["paginas_processadas"] = 1
            
            if config_paginacao and config_paginacao.get("tipo") == "INFINITE_SCROLL":
                imoveis_extras = await self._processar_infinite_scroll(page, config_paginacao)
                resultado["imoveis"].extend(imoveis_extras)
            elif config_paginacao and config_paginacao.get("tipo") == "NUMERIC":
                imoveis_extras = await self._processar_paginacao_numerica(page, url_base, config_paginacao)
                resultado["imoveis"].extend(imoveis_extras)
                resultado["paginas_processadas"] = config_paginacao.get("total_paginas", 1)
            
            resultado["total_imoveis"] = len(resultado["imoveis"])
            resultado["sucesso"] = resultado["total_imoveis"] > 0
            
        except Exception as e:
            resultado["erro"] = str(e)[:200]
            logger.error(f"   ❌ Erro: {e}")
        finally:
            if page: await page.close()
            if context: await context.close()
        
        return resultado
    
    def _construir_url_imoveis(self, url_base: str, dominio: str) -> str:
        urls_conhecidas = {
            "frazaoleiloes.com.br": "/sale/searchLot?&categoria=Imóveis&pesquisaSimples=false",
            "sold.com.br": "/leiloes/imoveis", "megaleiloes.com.br": "/imoveis",
            "portalzuk.com.br": "/leilao-de-imoveis"}
        return url_base + urls_conhecidas.get(dominio, "/imoveis")
    
    def _detectar_bloqueio(self, content: str) -> Optional[str]:
        c = content.lower()
        if 'cloudflare' in c and ('challenge' in c or 'ray id' in c): return "CLOUDFLARE_CHALLENGE"
        elif 'captcha' in c or 'recaptcha' in c: return "CAPTCHA"
        elif 'blocked' in c or 'denied' in c: return "WAF_BLOCKED"
        elif 'navegador incompatível' in c: return "BROWSER_CHECK"
        elif len(content) < 1000: return "PAGINA_VAZIA"
        return None
    
    async def _scroll_pagina(self, page: Page):
        try:
            await page.evaluate("""async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0; const distance = 500; const maxScroll = 10000;
                    const timer = setInterval(() => {
                        window.scrollBy(0, distance); totalHeight += distance;
                        if (totalHeight >= maxScroll) {
                            clearInterval(timer); window.scrollTo(0, 0); resolve();
                        }
                    }, 100);
                });
            }""")
            await asyncio.sleep(2)
        except: pass
    
    async def _extrair_imoveis_pagina(self, page: Page, url_origem: str) -> List[Dict]:
        imoveis = []
        seletores = ['a[href*="/imovel/"]', 'a[href*="/lote/"]', 'a[href*="/detalhes/"]',
                    'a[href*="/item/"]', '.property-card a', '.imovel-card a']
        
        for seletor in seletores:
            try:
                elementos = await page.query_selector_all(seletor)
                for elem in elementos:
                    try:
                        href = await elem.get_attribute('href')
                        texto = await elem.inner_text()
                        if href and ('/imovel' in href or '/lote' in href):
                            imovel = {
                                "url": href if href.startswith('http') else f"https://{url_origem.split('//')[1].split('/')[0]}{href}",
                                "texto_card": texto[:500] if texto else None,
                                "url_origem": url_origem, "extraido_em": datetime.now().isoformat()}
                            preco_match = re.search(r'R\$\s*([\d.,]+)', texto or '')
                            if preco_match:
                                try: imovel["preco"] = float(preco_match.group(1).replace('.', '').replace(',', '.'))
                                except: pass
                            imoveis.append(imovel)
                    except: pass
                if imoveis: break
            except: pass
        
        urls_vistas = set()
        return [i for i in imoveis if not (i["url"] in urls_vistas or urls_vistas.add(i["url"]))]
    
    async def _processar_infinite_scroll(self, page: Page, config: Dict) -> List[Dict]:
        imoveis_extras = []
        button_selector = config.get("button_selector", "button:has-text('Ver Mais')")
        for i in range(20):
            try:
                button = await page.query_selector(button_selector)
                if not button: break
                await button.click()
                await asyncio.sleep(2)
                novos = await self._extrair_imoveis_pagina(page, page.url)
                if not novos: break
                imoveis_extras.extend(novos)
                logger.info(f"      Clique {i+1}: +{len(novos)} imóveis")
            except: break
        return imoveis_extras
    
    async def _processar_paginacao_numerica(self, page: Page, url_base: str, config: Dict) -> List[Dict]:
        imoveis_extras = []
        pattern = config.get("url_pattern", "/imoveis?page={page}")
        for num_pagina in range(2, config.get("total_paginas", 5) + 1):
            try:
                url = url_base + pattern.format(page=num_pagina)
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
                novos = await self._extrair_imoveis_pagina(page, url)
                imoveis_extras.extend(novos)
                logger.info(f"      Página {num_pagina}: +{len(novos)} imóveis")
            except Exception as e:
                logger.warning(f"      Erro na página {num_pagina}: {e}")
                break
        return imoveis_extras
    
    async def processar_lista(self, dominios: List[str], config_paginacao: Dict = None):
        logger.info(f"\n{'='*60}\n🚀 TIER 2: Processando {len(dominios)} sites com Playwright Stealth\n{'='*60}\n")
        await self.setup_browser()
        try:
            for i, dominio in enumerate(dominios, 1):
                logger.info(f"\n[{i}/{len(dominios)}] {'-'*40}")
                config = config_paginacao.get(dominio) if config_paginacao else None
                resultado = await self.extrair_site(dominio, config)
                if resultado["sucesso"]:
                    self.resultados.append(resultado)
                    logger.info(f"   ✅ Sucesso: {resultado['total_imoveis']} imóveis")
                else:
                    self.falhas.append(resultado)
                    logger.warning(f"   ⚠️ Falha: {resultado.get('erro', 'Nenhum imóvel')}")
                await asyncio.sleep(3)
        finally:
            if self.browser: await self.browser.close()
        await self._salvar_resultados()
    
    async def _salvar_resultados(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = OUTPUT_DIR / f"tier2_resultados_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({"tier": "TIER_2_STEALTH", "timestamp": datetime.now().isoformat(),
                      "total_sites": len(self.resultados) + len(self.falhas),
                      "sucesso": len(self.resultados), "falhas": len(self.falhas),
                      "promocoes_tier3": self.promocoes_tier3,
                      "total_imoveis": sum(r["total_imoveis"] for r in self.resultados),
                      "resultados": self.resultados, "falhas_detalhes": self.falhas},
                     f, ensure_ascii=False, indent=2)
        if self.promocoes_tier3:
            promo_file = OUTPUT_DIR / f"promocoes_tier3_{timestamp}.json"
            with open(promo_file, 'w', encoding='utf-8') as f:
                json.dump(self.promocoes_tier3, f, ensure_ascii=False, indent=2)
            logger.info(f"\n⚠️ {len(self.promocoes_tier3)} sites promovidos para TIER 3")
        logger.info(f"\n📁 Resultados salvos em: {OUTPUT_DIR}")

async def main():
    config_path = Path("config/roteamento_sites.json")
    if not config_path.exists():
        logger.error(f"❌ Arquivo de roteamento não encontrado: {config_path}")
        return
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    sites_tier2 = config.get("TIER_2_STEALTH", {}).get("sites", [])
    config_paginacao = config.get("PAGINACAO", {}).get("sites", {})
    logger.info(f"📋 Sites TIER 2 carregados: {len(sites_tier2)}")
    extrator = ExtratorTier2()
    await extrator.processar_lista(sites_tier2, config_paginacao)

if __name__ == "__main__":
    asyncio.run(main())
