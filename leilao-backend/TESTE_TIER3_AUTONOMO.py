# ============================================================
# TESTE AUTÔNOMO: 5 Sites do Tier 3
# ============================================================
# Para: Cursor Agent
# Modo: AUTÔNOMO COMPLETO
# Tempo estimado: 15-20 minutos
# ============================================================

"""
╔══════════════════════════════════════════════════════════════╗
║  OBJETIVO                                                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Testar cada um dos 5 sites descobertos e extrair imóveis:  ║
║                                                              ║
║  1. Super Leilões      - ~527 imóveis (limite 600)          ║
║  2. Leilões Judiciais  - ~270 imóveis (limite 300)          ║
║  3. Leilões Online     - ~167 imóveis (limite 200)          ║
║  4. Zukerman           - ~127 imóveis (limite 150)          ║
║  5. Leilo Master       - ~1 imóvel                          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict
import traceback

# Stealth scripts
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
"""


@dataclass
class Property:
    """Estrutura de dados de um imóvel."""
    url: str
    title: str = ""
    price: str = ""
    location: str = ""
    category: str = ""
    area: str = ""
    image_url: str = ""
    auctioneer_id: str = ""
    auctioneer_name: str = ""
    extracted_at: str = ""


# Configurações dos 5 sites Tier 3
TIER3_SITES = [
    {
        "id": "superleiles",
        "name": "Super Leilões",
        "website": "https://www.superleiloes.com.br",
        "listing_url": "/imovel",
        "config_file": "app/configs/sites/superleiles.json",
        "max_properties": 600,
        "expected": 527,
    },
    {
        "id": "leilesjudiciais",
        "name": "Leilões Judiciais",
        "website": "https://www.leiloesjudiciais.com.br",
        "listing_url": "/imoveis",
        "config_file": "app/configs/sites/leilesjudiciais.json",
        "max_properties": 300,
        "expected": 270,
    },
    {
        "id": "leilesonline",
        "name": "Leilões Online",
        "website": "https://www.leiloesonline.com.br",
        "listing_url": "/imoveis",
        "config_file": "app/configs/sites/leilesonline.json",
        "max_properties": 200,
        "expected": 167,
    },
    {
        "id": "zukerman",
        "name": "Zukerman",
        "website": "https://www.zukerman.com.br",
        "listing_url": "/imoveis",
        "config_file": "app/configs/sites/zukerman.json",
        "max_properties": 150,
        "expected": 127,
    },
    {
        "id": "leilomaster",
        "name": "Leilo Master",
        "website": "https://www.leilomaster.com.br",
        "listing_url": "/imoveis",
        "config_file": "app/configs/sites/leilomaster.json",
        "max_properties": 50,
        "expected": 1,
    },
]


class Tier3Scraper:
    """Scraper para sites do Tier 3."""
    
    def __init__(self, site_config: Dict, file_config: Dict):
        self.site_config = site_config
        self.file_config = file_config
        self.id = site_config["id"]
        self.name = site_config["name"]
        self.website = site_config["website"]
        self.listing_url = site_config["listing_url"]
        self.max_properties = site_config["max_properties"]
        self.properties: List[Property] = []
        self.property_urls: Set[str] = set()
        self.pages_scraped = 0
        self.errors: List[str] = []
        
        # Extrair seletores do config
        self.selectors = file_config.get("selectors", {})
        self.pagination = file_config.get("pagination", {})
        
    async def scrape(self) -> Dict:
        """Executa scraping completo do site."""
        
        result = {
            "id": self.id,
            "name": self.name,
            "website": self.website,
            "listing_url": self.listing_url,
            "success": False,
            "total_properties": 0,
            "pages_scraped": 0,
            "properties": [],
            "errors": [],
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
        }
        
        print(f"\n{'='*70}")
        print(f"[SCRAPING] {self.name}")
        print(f"   URL: {self.website}{self.listing_url}")
        print(f"   Maximo: {self.max_properties} imoveis")
        print(f"{'='*70}")
        
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                    ]
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='pt-BR',
                    timezone_id='America/Sao_Paulo',
                )
                
                await context.add_init_script(STEALTH_SCRIPT)
                
                page = await context.new_page()
                
                # Acessar página inicial
                base_url = self.website.rstrip('/') + self.listing_url
                print(f"\n   [ACESSO] {base_url}")
                
                try:
                    response = await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
                    
                    if not response or response.status != 200:
                        print(f"      [ERRO] HTTP {response.status if response else 'N/A'}")
                        result["errors"].append(f"HTTP {response.status if response else 'N/A'}")
                        await browser.close()
                        return result
                    
                    # Aguardar renderização
                    await asyncio.sleep(5)  # Aumentar tempo de espera
                    
                    # Scroll para carregar conteúdo lazy
                    await self._scroll_page(page)
                    await asyncio.sleep(3)
                    
                    # Verificar se há conteúdo carregado
                    html = await page.content()
                    print(f"      [DEBUG] Tamanho HTML: {len(html)} caracteres")
                    
                    # Verificar se há cards ou elementos de listagem
                    card_count = await page.evaluate("document.querySelectorAll('[class*=\"card\"], [class*=\"item\"], article, .property').length")
                    print(f"      [DEBUG] Cards encontrados: {card_count}")
                    
                    # Extrair links iniciais
                    initial_links = await self._extract_links(page)
                    print(f"      Links iniciais: {len(initial_links)}")
                    
                    # Se não encontrou links, tentar estratégias alternativas
                    if len(initial_links) == 0:
                        print(f"      [WARN] Nenhum link encontrado, tentando estrategias alternativas...")
                        initial_links = await self._extract_links_alternative(page)
                        print(f"      Links alternativos: {len(initial_links)}")
                    
                    # Adicionar links iniciais
                    for link in initial_links:
                        if len(self.properties) >= self.max_properties:
                            break
                        if link not in self.property_urls:
                            self.property_urls.add(link)
                            prop = Property(
                                url=link,
                                auctioneer_id=self.id,
                                auctioneer_name=self.name,
                                extracted_at=datetime.now().isoformat(),
                            )
                            self.properties.append(prop)
                    
                    self.pages_scraped = 1
                    
                    # Tentar paginação se configurada
                    if self.pagination.get("type") != "none":
                        await self._handle_pagination(page)
                    
                    # Extrair detalhes de algumas propriedades (amostra)
                    print(f"\n   [DETALHES] Extraindo amostra ({min(10, len(self.properties))} imoveis)...")
                    
                    for i, prop in enumerate(self.properties[:10]):
                        try:
                            details = await self._extract_property_details(page, prop.url)
                            if details:
                                prop.title = details.get("title", "")
                                prop.price = details.get("price", "")
                                prop.location = details.get("location", "")
                                prop.category = details.get("category", "")
                                prop.image_url = details.get("image_url", "")
                            
                            await asyncio.sleep(1)
                            
                        except Exception as e:
                            print(f"      [ERRO] Erro ao extrair detalhes: {str(e)[:30]}")
                    
                    await browser.close()
                    
                    # Resultado
                    result["success"] = len(self.properties) > 0
                    result["total_properties"] = len(self.properties)
                    result["pages_scraped"] = self.pages_scraped
                    result["properties"] = [asdict(p) for p in self.properties]
                    result["errors"] = self.errors
                    result["finished_at"] = datetime.now().isoformat()
                    
                    print(f"\n   [OK] Concluido: {len(self.properties)} imoveis em {self.pages_scraped} paginas")
                    
                except Exception as e:
                    print(f"      [ERRO] {str(e)}")
                    result["errors"].append(str(e))
                    await browser.close()
                    
        except Exception as e:
            result["errors"].append(str(e))
            print(f"\n   [ERRO FATAL] {e}")
            traceback.print_exc()
        
        return result
    
    async def _extract_links(self, page) -> List[str]:
        """Extrai links de imóveis da página."""
        
        links = set()
        link_selector = self.selectors.get("link", "a[href*='/leilao/'], a[href*='/imovel/']")
        
        try:
            # Primeiro, tentar com o seletor configurado
            link_elements = await page.query_selector_all(link_selector)
            
            # Se não encontrar, tentar seletores alternativos
            if len(link_elements) == 0:
                # Tentar seletores mais genéricos
                alternative_selectors = [
                    "a[href*='/imovel']",
                    "a[href*='/leilao']",
                    "a[href*='/lote']",
                    "a[href*='/produto']",
                    ".card a",
                    "[class*='card'] a",
                    "article a",
                ]
                
                for alt_selector in alternative_selectors:
                    link_elements = await page.query_selector_all(alt_selector)
                    if len(link_elements) > 0:
                        print(f"      [INFO] Usando seletor alternativo: {alt_selector}")
                        break
            
            for element in link_elements:
                href = await element.get_attribute("href")
                if href:
                    full_url = urljoin(self.website, href)
                    # Limpar URL
                    parsed = urlparse(full_url)
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    
                    # Filtrar apenas URLs de imóveis (não listagens)
                    # Aceitar URLs que contenham padrões de imóveis
                    url_lower = clean_url.lower()
                    if any(pattern in url_lower for pattern in ["/imovel", "/leilao", "/lote", "/produto"]):
                        # Excluir URLs de listagem
                        if clean_url != self.website + self.listing_url:
                            if not any(exclude in url_lower for exclude in ["/imoveis", "/leiloes", "/categoria"]):
                                links.add(clean_url)
            
            # Se ainda não encontrou, tentar extrair do HTML
            if len(links) == 0:
                html = await page.content()
                # Buscar padrões de URLs no HTML
                patterns = [
                    r'href=["\']([^"\']*?/imovel/[^"\']+)["\']',
                    r'href=["\']([^"\']*?/leilao/[^"\']+)["\']',
                    r'href=["\']([^"\']*?/lote/[^"\']+)["\']',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, html, re.I)
                    for match in matches:
                        full_url = urljoin(self.website, match)
                        parsed = urlparse(full_url)
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        if clean_url != self.website + self.listing_url:
                            links.add(clean_url)
                
                if len(links) > 0:
                    print(f"      [INFO] Extraidos {len(links)} links do HTML")
                    
        except Exception as e:
            print(f"      [ERRO] Erro ao extrair links: {str(e)[:50]}")
            traceback.print_exc()
        
        return list(links)
    
    async def _extract_links_alternative(self, page) -> List[str]:
        """Extrai links usando estratégias alternativas."""
        
        links = set()
        
        try:
            # Estratégia 1: Buscar todos os links e filtrar
            all_links = await page.query_selector_all("a[href]")
            print(f"      [ALT] Total de links na pagina: {len(all_links)}")
            
            for element in all_links:
                href = await element.get_attribute("href")
                if href:
                    full_url = urljoin(self.website, href)
                    parsed = urlparse(full_url)
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    
                    # Filtrar URLs que parecem ser de imóveis
                    url_lower = clean_url.lower()
                    if any(pattern in url_lower for pattern in ["/imovel", "/leilao", "/lote", "/produto", "/item"]):
                        # Excluir listagens e categorias
                        if not any(exclude in url_lower for exclude in ["/imoveis", "/leiloes", "/categoria", "/busca"]):
                            if clean_url != self.website + self.listing_url:
                                links.add(clean_url)
            
            # Estratégia 2: Extrair do HTML com regex
            if len(links) == 0:
                html = await page.content()
                
                # Padrões mais genéricos
                patterns = [
                    r'href=["\']([^"\']*?/imovel[^"\']*?)["\']',
                    r'href=["\']([^"\']*?/leilao[^"\']*?)["\']',
                    r'href=["\']([^"\']*?/lote[^"\']*?)["\']',
                    r'href=["\']([^"\']*?/produto[^"\']*?)["\']',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, html, re.I)
                    for match in matches:
                        if match and not match.startswith('http'):
                            full_url = urljoin(self.website, match)
                        else:
                            full_url = match
                        
                        parsed = urlparse(full_url)
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        
                        if clean_url != self.website + self.listing_url:
                            links.add(clean_url)
            
            # Estratégia 3: Buscar por IDs ou data-attributes
            if len(links) == 0:
                # Tentar encontrar elementos com data-id ou data-url
                data_elements = await page.query_selector_all("[data-id], [data-url], [data-href]")
                for element in data_elements:
                    data_url = await element.get_attribute("data-url") or await element.get_attribute("data-href")
                    if data_url:
                        full_url = urljoin(self.website, data_url)
                        parsed = urlparse(full_url)
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        links.add(clean_url)
                        
        except Exception as e:
            print(f"      [ERRO] Erro em estrategia alternativa: {str(e)[:50]}")
        
        return list(links)
    
    async def _handle_pagination(self, page):
        """Lida com paginação se configurada."""
        
        pagination_type = self.pagination.get("type", "")
        pagination_param = self.pagination.get("param", "page")
        
        if pagination_type == "none":
            return
        
        max_pages = 50  # Limite de segurança
        current_page = 2  # Começar da página 2
        consecutive_same = 0  # Contador de páginas com mesmos links
        
        while len(self.properties) < self.max_properties and current_page <= max_pages:
            # Construir URL da página
            if pagination_type == "query_param":
                separator = "&" if "?" in (self.website + self.listing_url) else "?"
                page_url = f"{self.website.rstrip('/')}{self.listing_url}{separator}{pagination_param}={current_page}"
            else:
                page_url = f"{self.website.rstrip('/')}{self.listing_url}/page/{current_page}"
            
            print(f"\n   [PAGINA] {current_page}: {page_url[:60]}...")
            
            try:
                # Guardar URLs antes
                urls_before = len(self.property_urls)
                
                # Para sites que podem usar AJAX, tentar networkidle
                wait_until = 'networkidle' if self.id in ['superleiles', 'leilesjudiciais'] else 'domcontentloaded'
                response = await page.goto(page_url, wait_until=wait_until, timeout=60000)
                
                if not response or response.status != 200:
                    print(f"      [WARN] HTTP {response.status if response else 'N/A'}, parando...")
                    break
                
                # Aguardar mais tempo para AJAX/SPA
                await asyncio.sleep(5)
                
                # Scroll para carregar conteúdo lazy
                await self._scroll_page(page)
                await asyncio.sleep(3)
                
                # Verificar se a URL mudou (para AJAX)
                current_url = page.url
                if current_url != page_url:
                    print(f"      [INFO] URL mudou para: {current_url[:60]}...")
                
                # Extrair links
                new_links = await self._extract_links(page)
                new_unique = [l for l in new_links if l not in self.property_urls]
                
                print(f"      Links encontrados: {len(new_links)} (novos: {len(new_unique)})")
                
                # Se não encontrou novos links, verificar se é porque a página não mudou
                if len(new_unique) == 0:
                    consecutive_same += 1
                    if consecutive_same >= 2:
                        print(f"      [INFO] {consecutive_same} paginas consecutivas sem novos links, parando...")
                        break
                    
                    # Tentar clicar em botão "próxima" se existir
                    try:
                        next_btn = await page.query_selector("a[rel='next'], .pagination a:last-child, [class*='next']")
                        if next_btn:
                            is_visible = await next_btn.is_visible()
                            if is_visible:
                                print(f"      [INFO] Tentando clicar em botao 'proxima'...")
                                await next_btn.click()
                                await page.wait_for_load_state('networkidle', timeout=15000)
                                await asyncio.sleep(5)
                                continue
                    except:
                        pass
                    
                    # Se não tem botão, provavelmente acabou
                    print(f"      [INFO] Sem novos links, parando...")
                    break
                else:
                    consecutive_same = 0  # Reset contador
                
                # Adicionar novos links
                for link in new_unique:
                    if len(self.properties) >= self.max_properties:
                        break
                    
                    self.property_urls.add(link)
                    prop = Property(
                        url=link,
                        auctioneer_id=self.id,
                        auctioneer_name=self.name,
                        extracted_at=datetime.now().isoformat(),
                    )
                    self.properties.append(prop)
                
                self.pages_scraped += 1
                
                # Verificar se realmente adicionou novos
                urls_after = len(self.property_urls)
                if urls_after == urls_before:
                    consecutive_same += 1
                    if consecutive_same >= 2:
                        print(f"      [INFO] Nenhum novo link adicionado, parando...")
                        break
                
            except Exception as e:
                print(f"      [ERRO] {str(e)[:50]}")
                self.errors.append(f"Pagina {current_page}: {str(e)}")
                consecutive_same += 1
                if consecutive_same >= 2:
                    break
            
            current_page += 1
            await asyncio.sleep(2)  # Rate limiting
    
    async def _scroll_page(self, page):
        """Faz scroll na página para carregar conteúdo lazy."""
        
        try:
            await page.evaluate("""
                async () => {
                    for (let i = 0; i < 5; i++) {
                        window.scrollBy(0, 500);
                        await new Promise(r => setTimeout(r, 300));
                    }
                }
            """)
            await asyncio.sleep(1)
        except:
            pass
    
    async def _extract_property_details(self, page, url: str) -> Optional[Dict]:
        """Extrai detalhes de uma página de imóvel."""
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await asyncio.sleep(2)
            
            text = await page.evaluate("() => document.body.innerText")
            
            details = {}
            
            # Título
            title_match = await page.query_selector("h1, h2.title, .titulo")
            if title_match:
                details["title"] = (await title_match.inner_text()).strip()[:150]
            
            # Preço
            price_match = re.search(r'R\$\s*([\d.,]+)', text)
            if price_match:
                details["price"] = f"R$ {price_match.group(1)}"
            
            # Localização
            loc_match = re.search(r'([A-Za-zÀ-ÿ\s]{3,30})\s*[-/]\s*([A-Z]{2})\b', text)
            if loc_match:
                details["location"] = f"{loc_match.group(1).strip()}/{loc_match.group(2)}"
            
            # Categoria
            for cat in ["Apartamento", "Casa", "Terreno", "Comercial", "Rural", "Galpão"]:
                if cat.lower() in text.lower():
                    details["category"] = cat
                    break
            
            # Imagem
            img = await page.query_selector("img[src*='imovel'], img[src*='foto'], img.property-image")
            if img:
                src = await img.get_attribute("src")
                if src:
                    details["image_url"] = urljoin(url, src)
            
            return details
            
        except Exception as e:
            return None


async def main():
    """Função principal - executa scraping dos 5 sites Tier 3."""
    
    print("="*70)
    print("TESTE AUTÔNOMO: 5 SITES DO TIER 3")
    print("="*70)
    print(f"\nInício: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sites: {len(TIER3_SITES)}")
    
    all_results = []
    total_properties = 0
    
    for site_config in TIER3_SITES:
        # Carregar config do arquivo
        config_path = site_config["config_file"]
        
        if not os.path.exists(config_path):
            print(f"\n[ERRO] Config não encontrado: {config_path}")
            result = {
                "id": site_config["id"],
                "name": site_config["name"],
                "success": False,
                "total_properties": 0,
                "errors": [f"Config file not found: {config_path}"],
            }
            all_results.append(result)
            continue
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
        except Exception as e:
            print(f"\n[ERRO] Erro ao carregar config {config_path}: {e}")
            result = {
                "id": site_config["id"],
                "name": site_config["name"],
                "success": False,
                "total_properties": 0,
                "errors": [f"Error loading config: {str(e)}"],
            }
            all_results.append(result)
            continue
        
        # Criar scraper e executar
        scraper = Tier3Scraper(site_config, file_config)
        result = await scraper.scrape()
        all_results.append(result)
        total_properties += result["total_properties"]
        
        # Salvar resultado individual
        output_file = f"resultado_{site_config['id']}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"   [SAVED] Salvo: {output_file}")
        
        # Pausa entre sites
        await asyncio.sleep(5)
    
    # Relatório consolidado
    print("\n" + "="*70)
    print("RELATORIO CONSOLIDADO")
    print("="*70)
    
    print(f"\n{'Site':<25} {'Esperado':<10} {'Extraído':<10} {'Status':<10} {'Paginas':<10}")
    print("-"*70)
    
    for r in all_results:
        site_config = next((s for s in TIER3_SITES if s["id"] == r["id"]), None)
        expected = site_config["expected"] if site_config else "?"
        status = "[OK]" if r["success"] else "[FALHA]"
        print(f"{r['name']:<25} {expected:<10} {r['total_properties']:<10} {status:<10} {r.get('pages_scraped', 0):<10}")
    
    print("-"*70)
    print(f"{'TOTAL':<25} {'~1.092':<10} {total_properties:<10}")
    
    # Exemplos de imóveis
    print("\n" + "-"*70)
    print("EXEMPLOS DE IMOVEIS EXTRAIDOS:")
    print("-"*70)
    
    for r in all_results:
        if r["properties"]:
            print(f"\n{r['name']}:")
            for prop in r["properties"][:3]:
                title = prop.get("title", "N/A")[:40]
                price = prop.get("price", "N/A")
                location = prop.get("location", "N/A")
                print(f"   • {title}...")
                print(f"     Preço: {price} | Local: {location}")
                print(f"     URL: {prop['url'][:60]}...")
    
    # Gerar relatório Markdown
    report_content = f"""# RELATÓRIO DE TESTE: 5 SITES DO TIER 3

**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Resumo Executivo

| Site | Esperado | Extraído | Status | Páginas |
|------|----------|-----------|--------|---------|
"""
    
    for r in all_results:
        site_config = next((s for s in TIER3_SITES if s["id"] == r["id"]), None)
        expected = site_config["expected"] if site_config else "?"
        status = "SUCESSO" if r["success"] else "FALHA"
        print(f"| {r['name']} | ~{expected} | {r['total_properties']} | {status} | {r.get('pages_scraped', 0)} |")
        report_content += f"| {r['name']} | ~{expected} | {r['total_properties']} | {status} | {r.get('pages_scraped', 0)} |\n"
    
    report_content += f"""
| **TOTAL** | **~1.092** | **{total_properties}** | | |

## Detalhes por Site

"""
    
    for r in all_results:
        site_config = next((s for s in TIER3_SITES if s["id"] == r["id"]), None)
        expected = site_config["expected"] if site_config else "?"
        
        report_content += f"""### {r['name']}

- **Website:** {r.get('website', 'N/A')}
- **URL de Listagem:** {r.get('listing_url', 'N/A')}
- **Esperado:** ~{expected} imóveis
- **Extraído:** {r['total_properties']} imóveis
- **Páginas:** {r.get('pages_scraped', 0)}
- **Status:** {"SUCESSO" if r["success"] else "FALHA"}
- **Início:** {r.get('started_at', 'N/A')}
- **Fim:** {r.get('finished_at', 'N/A')}

"""
        
        if r["errors"]:
            report_content += "**Erros:**\n"
            for error in r["errors"]:
                report_content += f"- {error}\n"
            report_content += "\n"
        
        if r["properties"]:
            report_content += "**Exemplos de Imóveis:**\n\n"
            for prop in r["properties"][:3]:
                title = prop.get("title", "N/A")
                price = prop.get("price", "N/A")
                location = prop.get("location", "N/A")
                url = prop.get("url", "N/A")
                report_content += f"1. **{title}**\n"
                report_content += f"   - Preço: {price}\n"
                report_content += f"   - Localização: {location}\n"
                report_content += f"   - URL: {url}\n\n"
    
    report_content += f"""
## Arquivos Gerados

- `resultado_superleiles.json`
- `resultado_leilesjudiciais.json`
- `resultado_leilesonline.json`
- `resultado_zukerman.json`
- `resultado_leilomaster.json`

## Conclusão

Total de imóveis extraídos: **{total_properties}** de ~1.092 esperados.

Sites com sucesso: **{sum(1 for r in all_results if r['success'])}/{len(all_results)}**
"""
    
    with open("RELATORIO_TIER3_TESTE.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print(f"\n[REPORT] Relatorio: RELATORIO_TIER3_TESTE.md")
    
    # Atualizar configs com resultados
    print("\n" + "-"*70)
    print("ATUALIZANDO CONFIGS COM RESULTADOS...")
    print("-"*70)
    
    for r in all_results:
        site_config = next((s for s in TIER3_SITES if s["id"] == r["id"]), None)
        if not site_config:
            continue
        
        config_path = site_config["config_file"]
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {"id": r["id"]}
            
            config["enabled"] = r["success"] and r["total_properties"] > 0
            config["last_scrape"] = {
                "date": datetime.now().isoformat(),
                "success": r["success"],
                "properties_found": r["total_properties"],
                "pages_scraped": r.get("pages_scraped", 0),
                "errors_count": len(r["errors"]),
            }
            config["last_count"] = r["total_properties"]
            config["status"] = "success" if r["success"] else "failed"
            
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            status = "[OK]" if config["enabled"] else "[WARN]"
            print(f"   {status} {config_path}")
            
        except Exception as e:
            print(f"   [ERRO] Erro ao atualizar {r['id']}: {e}")
    
    # Resumo final
    print("\n" + "="*70)
    print("[OK] TESTE COMPLETO FINALIZADO")
    print("="*70)
    print(f"\nFim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total de imoveis extraidos: {total_properties}")
    print(f"Sites com sucesso: {sum(1 for r in all_results if r['success'])}/{len(all_results)}")
    
    print("\n[FILES] Arquivos gerados:")
    print("   - RELATORIO_TIER3_TESTE.md (relatorio geral)")
    for r in all_results:
        print(f"   - resultado_{r['id']}.json ({r['total_properties']} imoveis)")


if __name__ == "__main__":
    asyncio.run(main())

