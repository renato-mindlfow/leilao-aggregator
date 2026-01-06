# ============================================================
# TAREFA AUTÔNOMA: Scraping Completo dos 5 Gigantes
# ============================================================
# Para: Cursor Agent
# Modo: AUTÔNOMO COMPLETO
# Tempo estimado: 30-45 minutos
# ============================================================

"""
╔══════════════════════════════════════════════════════════════╗
║  OBJETIVO                                                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Executar scraping COMPLETO dos 5 gigantes usando as         ║
║  URLs RAIZ de imóveis corrigidas.                            ║
║                                                              ║
║  Para cada site:                                             ║
║  1. Acessar URL raiz de imóveis                              ║
║  2. Identificar paginação                                    ║
║  3. Extrair TODOS os imóveis (até limite de segurança)       ║
║  4. Coletar dados: título, preço, localização, URL           ║
║  5. Salvar resultados                                        ║
║                                                              ║
║  Sites (em ordem):                                           ║
║  1. Mega Leilões    - /imoveis          (~743 imóveis)       ║
║  2. Lance Judicial  - /imoveis          (~312 imóveis)       ║
║  3. Portal Zukerman - /leilao-de-imoveis                     ║
║  4. Sold Leilões    - /h/imoveis                             ║
║  5. Sodré Santoro   - /imoveis                               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import re
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from dataclasses import dataclass, asdict
import traceback

# ============================================================
# CONFIGURAÇÃO DOS 5 GIGANTES
# ============================================================

GIGANTES = [
    {
        "id": "megaleiloes",
        "name": "Mega Leilões",
        "website": "https://www.megaleiloes.com.br",
        "listing_url": "/imoveis",
        "method": "playwright",
        "pagination": {
            "type": "query",  # ?pagina=2
            "param": "pagina",
            "start": 1,
        },
        "selectors": {
            "property_link": "a[href*='/leilao/']",
            "property_card": ".card, .item, article, [class*='card']",
            "next_page": "a[rel='next'], .pagination a:last-child, [class*='next']",
            "total_count": "[class*='total'], [class*='count'], [class*='resultado']",
        },
        "link_patterns": [r"/auditorio/[^/]+/\d+", r"/leilao/\d+"],
        "max_pages": 15,
        "items_per_page": 24,
        "wait_time": 15,  # Espera 15s para SPA React carregar
    },
    {
        "id": "lancejudicial",
        "name": "Lance Judicial",
        "website": "https://www.grupolance.com.br",  # Atualizado: site redireciona para grupolance.com.br
        "listing_url": "/imoveis",
        "method": "playwright",
        "pagination": {
            "type": "query",
            "param": "pagina",  # Corrigido: site usa "pagina" não "page"
            "start": 1,
        },
        "selectors": {
            "property_link": ".card a, [class*='card'] a",  # Atualizado: seletor correto dos cards
            "property_card": ".card, [class*='card']",
            "next_page": ".pagination a:last-child, [class*='pagination'] a, a[rel='next']",
        },
        "link_patterns": [
            r"/imoveis/[^/]+/[^/]+/[^/]+/[^/]+-\d+",  # Padrão correto: categoria/estado/cidade/nome-numero
        ],
        "max_pages": 10,  # 308 itens / 32 por página = ~10 páginas
        "items_per_page": 32,
        "max_items": 308,  # Total de imóveis conforme o site
    },
    {
        "id": "portalzuk",
        "name": "Portal Zukerman",
        "website": "https://www.portalzuk.com.br",
        "listing_url": "/leilao-de-imoveis",
        "method": "playwright",
        "pagination": {
            "type": "path",  # /page/2 ou scroll infinito
            "param": "page",
            "start": 1,
        },
        "selectors": {
            "property_link": "a[href*='/imovel/']",
            "property_card": "[class*='card'], [class*='property']",
        },
        "link_patterns": [r"/imovel/[^/]+/[^/]+/[^/]+/[^/]+/[^/]+/\d+-\d+"],
        "max_pages": 50,
        "items_per_page": 20,
    },
    {
        "id": "sold",
        "name": "Sold Leilões",
        "website": "https://www.sold.com.br",
        "listing_url": "/h/imoveis",
        "method": "api",  # Usa API diretamente para melhor performance
        "api_url": "https://offer-query.superbid.net/offers/",
        "api_params": {
            "portalId": "[2,15]",
            "requestOrigin": "store",  # IMPORTANTE: "store" retorna 143, "marketplace" retorna 1156
            "locale": "pt_BR",
            "timeZoneId": "America/Sao_Paulo",
            "searchType": "opened",  # Apenas leilões abertos/ativos
            "filter": "product.productType.description:imoveis;stores.id:[1161,1741]",  # Filtro correto para 143 imóveis ativos
            "geoLocation": "true",
            "pageSize": 50,
            "fieldList": "id;visits;linkURL;price;priceFormatted;hidePrices;commissionPercent;commercialCondition;eventPipeline;isFavorite;endDate;offerStatus;offerStatusHybrid;stores;store;product.shortDesc;product.template;product.productType;product.galleryJson;product.thumbnailUrl;auction;installmentPaymentTerms;offerTypeId;offerDetail;statusId;totalBids;endDateTime;isShopping;quantityUnitType;quantityUnit;systemMetric;quantityInLot;quantityAvailableForProposal;totalInterested",
        },
        "pagination": {
            "type": "api",
            "param": "pageNumber",
            "start": 1,
        },
        "selectors": {
            "property_link": "a[href*='/leilao/'], a[href*='/produto/']",
            "property_card": "[class*='card'], [class*='MuiCard']",
        },
        "link_patterns": [r"/leilao/\d+", r"/produto/\d+"],
        "max_pages": 10,  # ~143 imóveis / 50 por página = ~3 páginas, mas deixamos margem
        "items_per_page": 50,
        "max_items": 150,  # Limite de segurança
    },
    {
        "id": "sodresantoro",
        "name": "Sodré Santoro",
        "website": "https://www.sodresantoro.com.br",
        "listing_url": "/imoveis",
        "method": "playwright",
        "pagination": {
            "type": "query",
            "param": "page",
            "start": 1,
        },
        "selectors": {
            "property_link": "a[href*='/imovel/'], .card a, a[href*='/leilao/'], a[href*='/lote/']",
            "property_card": "[class*='card'], [class*='lote']",
        },
        "link_patterns": [r"/imovel/\d+", r"/lote/\d+", r"/leilao/\d+"],
        "max_pages": 30,
        "items_per_page": 20,
    },
]

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


class GiganteScraper:
    """Scraper para um site gigante."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.id = config["id"]
        self.name = config["name"]
        self.website = config["website"]
        self.listing_url = config["listing_url"]
        self.properties: List[Property] = []
        self.property_urls: Set[str] = set()
        self.property_ids: Set[int] = set()  # IDs únicos (para API)
        self.pages_scraped = 0
        self.errors: List[str] = []
        self.api_total: Optional[int] = None  # Total retornado pela API
        
    async def scrape(self, max_properties: int = 500) -> Dict:
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
        print(f"   Maximo: {max_properties} imoveis")
        print(f"{'='*70}")
        
        # Se usar API, fazer scraping via API
        if self.config.get("method") == "api":
            return await self._scrape_via_api(max_properties)
        
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
                
                # Scrape páginas
                # Lógica especial para Portal Zukerman (botão "Carregar mais")
                if self.id == "portalzuk":
                    await self._scrape_portal_zuk_load_more(page, max_properties)
                # Lógica especial para Lance Judicial (clicar em botões de paginação)
                elif self.id == "lancejudicial":
                    await self._scrape_lance_judicial_pagination(page, max_properties)
                # Lógica especial para Mega Leilões (SPA React - espera 15s)
                elif self.id == "megaleiloes":
                    await self._scrape_mega_leiloes_spa(page, max_properties)
                else:
                    current_page = self.config["pagination"]["start"]
                    consecutive_empty = 0
                    
                    while len(self.properties) < max_properties and current_page <= self.config["max_pages"]:
                        
                        # Construir URL da página
                        page_url = self._build_page_url(current_page)
                        
                        print(f"\n   [PAGINA] {current_page}: {page_url[:60]}...")
                        
                        try:
                            # Acessar página
                            # Para sites com AJAX, usar 'networkidle' em vez de 'domcontentloaded'
                            wait_until = 'networkidle' if self.id == 'lancejudicial' else 'domcontentloaded'
                            response = await page.goto(page_url, wait_until=wait_until, timeout=30000)
                            
                            if not response or response.status != 200:
                                print(f"      [ERRO] HTTP {response.status if response else 'N/A'}")
                                consecutive_empty += 1
                                if consecutive_empty >= 3:
                                    print(f"      [WARN] 3 paginas consecutivas falharam, parando...")
                                    break
                                current_page += 1
                                continue
                            
                            # Aguardar renderização (aumentar tempo para sites com AJAX)
                            wait_time = 5 if self.id == 'lancejudicial' else 3
                            await asyncio.sleep(wait_time)
                            
                            # Para Lance Judicial, aguardar carregamento PJAX/AJAX específico
                            if self.id == 'lancejudicial':
                                # Aguardar até que os cards sejam carregados E que o conteúdo seja diferente
                                try:
                                    # Aguardar carregamento inicial
                                    await page.wait_for_selector('.card', timeout=10000)
                                    
                                    # Aguardar que o PJAX termine (verificar se há indicador de loading)
                                    await page.wait_for_load_state('networkidle', timeout=15000)
                                    
                                    # Aguardar um pouco mais para garantir renderização completa
                                    await asyncio.sleep(3)
                                    
                                    # Verificar se há contador de página (para garantir que mudou)
                                    page_text = await page.inner_text('body')
                                    if f'Página {current_page}' in page_text or f'page={current_page}' in page_url:
                                        # Aguardar mais um pouco para garantir que o conteúdo foi atualizado
                                        await asyncio.sleep(2)
                                except Exception as e:
                                    print(f"      [INFO] Aguardando carregamento: {str(e)[:50]}")
                                    await asyncio.sleep(3)  # Fallback: aguardar fixo
                            
                            # Scroll para carregar conteúdo
                            await self._scroll_page(page)
                            
                            # Extrair links de imóveis
                            # Para Lance Judicial, usar seletor CSS diretamente em vez de regex no HTML
                            if self.id == 'lancejudicial':
                                new_links = await self._extract_links_css(page)
                            else:
                                html = await page.content()
                                new_links = self._extract_property_links(html)
                            
                            # Filtrar links já vistos
                            new_unique = [l for l in new_links if l not in self.property_urls]
                            
                            print(f"      Links encontrados: {len(new_links)} (novos: {len(new_unique)})")
                            
                            if len(new_unique) == 0:
                                consecutive_empty += 1
                                if consecutive_empty >= 2:
                                    print(f"      [WARN] Sem novos links, parando...")
                                    break
                            else:
                                consecutive_empty = 0
                            
                            # Adicionar à lista
                            for link in new_unique:
                                if len(self.properties) >= max_properties:
                                    break
                                
                                self.property_urls.add(link)
                                
                                # Criar propriedade básica (sem acessar página individual)
                                prop = Property(
                                    url=link,
                                    auctioneer_id=self.id,
                                    auctioneer_name=self.name,
                                    extracted_at=datetime.now().isoformat(),
                                )
                                self.properties.append(prop)
                            
                            self.pages_scraped += 1
                            
                        except Exception as e:
                            print(f"      [ERRO] {str(e)[:50]}")
                            self.errors.append(f"Pagina {current_page}: {str(e)}")
                            consecutive_empty += 1
                        
                        current_page += 1
                        await asyncio.sleep(2)  # Rate limiting
                
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
            result["errors"].append(str(e))
            print(f"\n   [ERRO FATAL] {e}")
        
        return result
    
    async def _scrape_via_api(self, max_properties: int = 500) -> Dict:
        """Executa scraping via API (para sites que suportam)."""
        
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
            "api_total": None,  # Total retornado pela API
        }
        
        try:
            import requests
            
            api_url = self.config.get("api_url")
            api_params = self.config.get("api_params", {}).copy()
            max_items = self.config.get("max_items", max_properties)
            items_per_page = self.config.get("items_per_page", 50)
            max_pages = self.config.get("max_pages", 10)
            
            current_page = self.config["pagination"]["start"]
            
            print(f"\n   [API] Usando API: {api_url}")
            print(f"   [API] Filtro: {api_params.get('filter', 'N/A')}")
            print(f"   [API] searchType: {api_params.get('searchType', 'N/A')}")
            
            while len(self.properties) < max_items and current_page <= max_pages:
                api_params["pageNumber"] = current_page
                api_params["pageSize"] = items_per_page
                
                print(f"\n   [PAGINA] {current_page}: Buscando {items_per_page} itens...")
                
                try:
                    response = requests.get(api_url, params=api_params, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    
                    offers = data.get("offers", [])
                    total = data.get("total", 0)
                    
                    # Armazenar total da API (primeira página)
                    if current_page == 1:
                        self.api_total = total
                        print(f"      [INFO] Total disponivel na API: {total}")
                    
                    print(f"      [INFO] Itens recebidos: {len(offers)}")
                    
                    if len(offers) == 0:
                        print(f"      [WARN] Sem itens, parando...")
                        break
                    
                    # Processar cada oferta
                    processed = 0
                    skipped_no_id = 0
                    skipped_duplicate = 0
                    
                    for offer in offers:
                        if len(self.properties) >= max_items:
                            break
                        
                        # Extrair ID da oferta (chave única)
                        offer_id = offer.get("id")
                        
                        # Verificar duplicado por ID (mais confiável que URL)
                        if offer_id and offer_id in self.property_ids:
                            skipped_duplicate += 1
                            continue
                        
                        # Extrair URL do imóvel
                        # Primeiro tenta linkURL, senão constrói a partir do ID
                        link_url = offer.get("linkURL", "")
                        if not link_url:
                            # Construir URL a partir do ID da oferta (único) ou leilão
                            # IMPORTANTE: Usar offer_id primeiro para evitar duplicados
                            # (um leilão pode ter múltiplas ofertas/lotes)
                            auction_id = offer.get("auction", {}).get("id")
                            if offer_id:
                                # Tentar usar offer_id primeiro (mais específico)
                                link_url = f"/produto/{offer_id}"
                            elif auction_id:
                                # Fallback para auction_id se não tiver offer_id
                                link_url = f"/leilao/{auction_id}"
                            else:
                                skipped_no_id += 1
                                continue
                        
                        # Construir URL completa
                        if link_url.startswith("http"):
                            full_url = link_url
                        else:
                            full_url = urljoin(self.website, link_url)
                        
                        # Verificar duplicado por URL apenas se não tiver offer_id
                        # (se tem offer_id, já verificamos acima)
                        if not offer_id and full_url in self.property_urls:
                            skipped_duplicate += 1
                            continue
                        
                        # Adicionar às listas de controle
                        if offer_id:
                            self.property_ids.add(offer_id)
                        self.property_urls.add(full_url)
                        processed += 1
                        
                        # Extrair informações básicas
                        prop = Property(
                            url=full_url,
                            title=offer.get("product", {}).get("shortDesc", "")[:200],
                            price=offer.get("priceFormatted", ""),
                            location="",  # Pode ser extraído de product se disponível
                            category=offer.get("product", {}).get("productType", {}).get("description", ""),
                            image_url=offer.get("product", {}).get("thumbnailUrl", ""),
                            auctioneer_id=self.id,
                            auctioneer_name=self.name,
                            extracted_at=datetime.now().isoformat(),
                        )
                        self.properties.append(prop)
                    
                    print(f"      [INFO] Processados: {processed}, Pulados (sem ID): {skipped_no_id}, Pulados (duplicados): {skipped_duplicate}")
                    if skipped_duplicate > 0:
                        print(f"      [INFO] Duplicados detectados por offer_id (API pode estar retornando itens repetidos)")
                    self.pages_scraped += 1
                    
                    # Se recebeu menos itens que o pageSize, provavelmente é a última página
                    if len(offers) < items_per_page:
                        print(f"      [INFO] Ultima pagina atingida")
                        break
                    
                    await asyncio.sleep(1.5)  # Rate limiting aumentado para evitar 503
                    
                except Exception as e:
                    print(f"      [ERRO] {str(e)[:50]}")
                    self.errors.append(f"Pagina {current_page}: {str(e)}")
                    break
                
                current_page += 1
            
            # Resultado
            result["success"] = len(self.properties) > 0
            result["total_properties"] = len(self.properties)
            result["pages_scraped"] = self.pages_scraped
            result["properties"] = [asdict(p) for p in self.properties]
            result["errors"] = self.errors
            result["finished_at"] = datetime.now().isoformat()
            result["api_total"] = self.api_total  # Total retornado pela API
            
            print(f"\n   [OK] Concluido: {len(self.properties)} imoveis em {self.pages_scraped} paginas")
            
        except Exception as e:
            result["errors"].append(str(e))
            print(f"\n   [ERRO FATAL] {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def _build_page_url(self, page_num: int) -> str:
        """Constrói URL para uma página específica."""
        
        base_url = self.website.rstrip('/') + self.listing_url
        
        pagination = self.config["pagination"]
        
        if page_num == pagination["start"]:
            return base_url
        
        if pagination["type"] == "query":
            separator = "&" if "?" in base_url else "?"
            return f"{base_url}{separator}{pagination['param']}={page_num}"
        
        elif pagination["type"] == "path":
            return f"{base_url}/page/{page_num}"
        
        return base_url
    
    def _extract_property_links(self, html: str) -> List[str]:
        """Extrai links de imóveis do HTML."""
        
        links = set()
        
        # Usar padrões configurados
        for pattern in self.config["link_patterns"]:
            matches = re.findall(f'href=["\']([^"\']*{pattern}[^"\']*)["\']', html, re.I)
            for match in matches:
                full_url = urljoin(self.website, match)
                # Limpar URL (remover fragmentos e query strings desnecessárias)
                parsed = urlparse(full_url)
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                links.add(clean_url)
        
        return list(links)
    
    async def _extract_links_css(self, page) -> List[str]:
        """Extrai links usando seletor CSS diretamente (melhor para AJAX)."""
        
        links = set()
        selector = self.config["selectors"].get("property_link", "a[href*='/imoveis/']")
        
        # Buscar todos os links que correspondem ao seletor
        link_elements = await page.query_selector_all(selector)
        
        for element in link_elements:
            href = await element.get_attribute("href")
            if href:
                full_url = urljoin(self.website, href)
                # Limpar URL
                parsed = urlparse(full_url)
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                
                # Filtrar por padrão regex se configurado
                if self.config.get("link_patterns"):
                    matches_pattern = False
                    for pattern in self.config["link_patterns"]:
                        if re.search(pattern, clean_url):
                            matches_pattern = True
                            break
                    if matches_pattern:
                        links.add(clean_url)
                else:
                    links.add(clean_url)
        
        return list(links)
    
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
    
    async def _scrape_portal_zuk_load_more(self, page, max_properties: int):
        """Scraping especial para Portal Zukerman com botão 'Carregar mais'."""
        
        base_url = self.website.rstrip('/') + self.listing_url
        
        print(f"\n   [PORTAL ZUK] Acessando: {base_url}")
        print(f"   [PORTAL ZUK] Usando botao 'Carregar mais' (#btn_carregarMais)")
        
        try:
            # Acessar página inicial
            response = await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
            
            if not response or response.status != 200:
                print(f"      [ERRO] HTTP {response.status if response else 'N/A'}")
                return
            
            # Aguardar renderização inicial
            await asyncio.sleep(3)
            
            # Scroll inicial
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            # Extrair links iniciais
            initial_links = await page.query_selector_all('a[href*="/imovel/"]')
            all_links = set()
            for link in initial_links:
                href = await link.get_attribute("href")
                if href:
                    full_url = urljoin(self.website, href)
                    all_links.add(full_url)
            
            print(f"      Links iniciais: {len(all_links)}")
            
            # Clicar no botão "Carregar mais" repetidamente
            max_cliques = 50  # Limite de segurança (30+ vezes para ~949 imóveis)
            cliques_realizados = 0
            
            for click_num in range(max_cliques):
                if len(all_links) >= max_properties:
                    break
                
                # Scroll até o final
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
                
                # Procurar botão "Carregar mais"
                load_more_btn = await page.query_selector("#btn_carregarMais")
                
                if not load_more_btn:
                    print(f"      [INFO] Botao nao encontrado apos {cliques_realizados} cliques, parando...")
                    break
                
                is_visible = await load_more_btn.is_visible()
                if not is_visible:
                    print(f"      [INFO] Botao nao visivel apos {cliques_realizados} cliques, parando...")
                    break
                
                # Contar links antes do clique
                links_before = len(all_links)
                
                # Clicar usando JavaScript para evitar interceptação
                try:
                    await page.evaluate("document.getElementById('btn_carregarMais').click()")
                    cliques_realizados += 1
                    await asyncio.sleep(4)  # Aguardar carregar novos itens (aumentado para garantir)
                except Exception as e:
                    print(f"      [ERRO] Erro ao clicar: {e}")
                    break
                
                # Extrair novos links
                new_links = await page.query_selector_all('a[href*="/imovel/"]')
                for link in new_links:
                    href = await link.get_attribute("href")
                    if href:
                        full_url = urljoin(self.website, href)
                        all_links.add(full_url)
                
                links_after = len(all_links)
                novos = links_after - links_before
                
                print(f"      Clique {cliques_realizados}: {links_after} links totais (+{novos} novos)")
                
                # Se não adicionou novos links, parar
                if novos == 0:
                    print(f"      [INFO] Nenhum novo link adicionado, parando...")
                    break
            
            # Adicionar todas as propriedades encontradas
            for link in all_links:
                if len(self.properties) >= max_properties:
                    break
                
                self.property_urls.add(link)
                prop = Property(
                    url=link,
                    auctioneer_id=self.id,
                    auctioneer_name=self.name,
                    extracted_at=datetime.now().isoformat(),
                )
                self.properties.append(prop)
            
            self.pages_scraped = 1  # Conta como 1 página (mesmo com múltiplos cliques)
            
            print(f"      [OK] Total extraido: {len(self.properties)} imoveis")
            
        except Exception as e:
            print(f"      [ERRO] {str(e)}")
    
    async def _scrape_lance_judicial_pagination(self, page, max_properties: int):
        """Scraping especial para Lance Judicial clicando em botões de paginação."""
        
        base_url = self.website.rstrip('/') + self.listing_url
        
        print(f"\n   [LANCE JUDICIAL] Acessando: {base_url}")
        print(f"   [LANCE JUDICIAL] Usando cliques em botoes de paginacao")
        
        try:
            # Acessar página inicial
            await page.goto(base_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(5)
            
            current_page = 1
            max_pages = self.config.get("max_pages", 10)
            
            while len(self.properties) < max_properties and current_page <= max_pages:
                print(f"\n   [PAGINA] {current_page}")
                
                # Aguardar carregamento
                await page.wait_for_selector('.card', timeout=10000)
                await page.wait_for_load_state('networkidle', timeout=15000)
                await asyncio.sleep(3)
                
                # Extrair links desta página
                new_links = await self._extract_links_css(page)
                
                # Filtrar links já vistos
                new_unique = [l for l in new_links if l not in self.property_urls]
                
                print(f"      Links encontrados: {len(new_links)} (novos: {len(new_unique)})")
                
                # Adicionar novos links
                for link in new_unique:
                    if len(self.properties) >= max_properties:
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
                
                # Se não encontrou novos links, parar
                if len(new_unique) == 0:
                    print(f"      [INFO] Nenhum novo link, parando...")
                    break
                
                # Se já coletou o suficiente, parar
                if len(self.properties) >= max_properties:
                    break
                
                # Tentar clicar no botão da próxima página
                next_page_num = current_page + 1
                next_btn = await page.query_selector(f'a[href*="pagina={next_page_num}"]')
                
                if not next_btn:
                    # Tentar encontrar botão "próxima" ou número da página
                    next_btn = await page.query_selector(f'.pagination a:has-text("{next_page_num}")')
                
                if next_btn:
                    # Verificar se está visível e habilitado
                    is_visible = await next_btn.is_visible()
                    if is_visible:
                        print(f"      Clicando no botao da pagina {next_page_num}...")
                        await next_btn.click()
                        await page.wait_for_load_state('networkidle', timeout=15000)
                        await asyncio.sleep(5)  # Aguardar carregamento PJAX
                        current_page = next_page_num
                    else:
                        print(f"      [INFO] Botao da pagina {next_page_num} nao visivel, parando...")
                        break
                else:
                    print(f"      [INFO] Botao da pagina {next_page_num} nao encontrado, parando...")
                    break
                
                await asyncio.sleep(2)  # Rate limiting
            
            print(f"\n   [OK] Total extraido: {len(self.properties)} imoveis")
            
        except Exception as e:
            print(f"      [ERRO] {str(e)}")
            import traceback
            traceback.print_exc()
            self.errors.append(f"Portal Zuk Load More: {str(e)}")
    
    async def _scrape_mega_leiloes_spa(self, page, max_properties: int):
        """Scraping especial para Mega Leilões com SPA React (espera 15s)."""
        
        base_url = self.website.rstrip('/') + self.listing_url
        wait_time = self.config.get("wait_time", 15)
        max_pages = min(self.config.get("max_pages", 15), 15)  # Limitar a 15 páginas
        
        print(f"\n   [MEGA LEILOES] Acessando: {base_url}")
        print(f"   [MEGA LEILOES] Espera SPA: {wait_time}s (primeira página)")
        
        try:
            all_links = set()
            
            for page_num in range(1, max_pages + 1):
                if len(self.properties) >= max_properties:
                    break
                
                # Construir URL da página
                if page_num == 1:
                    page_url = base_url
                else:
                    page_url = f"{base_url}?pagina={page_num}"
                
                print(f"\n   [PAGINA] {page_num}: {page_url[:60]}...")
                
                try:
                    # Acessar página
                    await page.goto(page_url, wait_until='domcontentloaded', timeout=60000)
                    
                    # Espera longa para SPA React (15s primeira página, 5s demais)
                    if page_num == 1:
                        print(f"      [AGUARDANDO] SPA carregar ({wait_time}s)...")
                        await asyncio.sleep(wait_time)
                    else:
                        await asyncio.sleep(5)
                    
                    # Scroll para carregar conteúdo lazy
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                    
                    # Extrair HTML e buscar padrões (/auditorio/ e /leilao/)
                    html = await page.content()
                    
                    # Padrões corretos: /auditorio/ e /leilao/
                    patterns = [
                        r'href=["\']([^"\']*?/auditorio/[^/]+/\d+[^"\']*)["\']',  # /auditorio/{id}/{id}
                        r'href=["\']([^"\']*?/leilao/\d+[^"\']*)["\']',  # /leilao/{id}
                        r'href=["\']([^"\']*?megaleiloes\.com\.br/[^"\']*?/\d+[^"\']*)["\']',
                    ]
                    
                    page_links = set()
                    for pattern in patterns:
                        matches = re.findall(pattern, html, re.I)
                        for match in matches:
                            full_url = urljoin(self.website, match)
                            # Filtrar apenas URLs de imóveis (não /imoveis)
                            if "megaleiloes" in full_url and "/imoveis" not in full_url:
                                page_links.add(full_url)
                    
                    links_before = len(all_links)
                    all_links.update(page_links)
                    links_added = len(all_links) - links_before
                    
                    print(f"      Links encontrados: {len(page_links)} | Novos: {links_added} | Total: {len(all_links)}")
                    
                    # Adicionar propriedades
                    new_unique = [l for l in page_links if l not in self.property_urls]
                    for link in new_unique:
                        if len(self.properties) >= max_properties:
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
                    
                    # Se não encontrou novos links, parar
                    if links_added == 0 and page_num > 1:
                        print(f"      [WARN] Sem novos links, parando...")
                        break
                    
                    await asyncio.sleep(2)  # Rate limiting
                    
                except Exception as e:
                    print(f"      [ERRO] {str(e)[:50]}")
                    self.errors.append(f"Pagina {page_num}: {str(e)}")
                    break
            
            print(f"\n   [OK] Total extraido: {len(self.properties)} imoveis")
            
        except Exception as e:
            print(f"      [ERRO] {str(e)}")
            self.errors.append(f"Mega Leiloes SPA: {str(e)}")
    
    async def _extract_property_details(self, page, url: str) -> Optional[Dict]:
        """Extrai detalhes de uma página de imóvel."""
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await asyncio.sleep(2)
            
            html = await page.content()
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
    """Função principal - executa scraping de todos os gigantes."""
    
    print("="*70)
    print("SCRAPING COMPLETO DOS 5 GIGANTES")
    print("="*70)
    print(f"\nInício: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sites: {len(GIGANTES)}")
    print(f"Limite por site: 500 imóveis")
    
    all_results = []
    total_properties = 0
    
    for config in GIGANTES:
        scraper = GiganteScraper(config)
        result = await scraper.scrape(max_properties=500)
        all_results.append(result)
        total_properties += result["total_properties"]
        
        # Salvar resultado individual
        output_file = f"resultado_{config['id']}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"   [SAVED] Salvo: {output_file}")
        
        # Pausa entre sites
        await asyncio.sleep(5)
    
    # Relatório consolidado
    print("\n" + "="*70)
    print("RELATORIO CONSOLIDADO")
    print("="*70)
    
    print(f"\n{'Site':<25} {'Status':<10} {'Imoveis':<10} {'Paginas':<10} {'Erros'}")
    print("-"*70)
    
    for r in all_results:
        status = "[OK]" if r["success"] else "[FALHA]"
        print(f"{r['name']:<25} {status:<10} {r['total_properties']:<10} {r['pages_scraped']:<10} {len(r['errors'])}")
    
    print("-"*70)
    print(f"{'TOTAL':<25} {'':<10} {total_properties:<10}")
    
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
    
    # Salvar relatório consolidado
    consolidated = {
        "generated_at": datetime.now().isoformat(),
        "total_sites": len(all_results),
        "successful_sites": sum(1 for r in all_results if r["success"]),
        "total_properties": total_properties,
        "results": all_results,
    }
    
    with open("scraping_gigantes_consolidado.json", "w", encoding="utf-8") as f:
        json.dump(consolidated, f, ensure_ascii=False, indent=2)
    
    print(f"\n[REPORT] Relatorio consolidado: scraping_gigantes_consolidado.json")
    
    # Atualizar configs com resultados
    print("\n" + "-"*70)
    print("ATUALIZANDO CONFIGS COM RESULTADOS...")
    print("-"*70)
    
    for r in all_results:
        config_path = f"app/configs/sites/{r['id']}.json"
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
                "pages_scraped": r["pages_scraped"],
                "errors_count": len(r["errors"]),
            }
            
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            status = "[OK]" if config["enabled"] else "[WARN]"
            print(f"   {status} {config_path}")
            
        except Exception as e:
            print(f"   [ERRO] Erro ao atualizar {r['id']}: {e}")
    
    # Resumo final
    print("\n" + "="*70)
    print("[OK] SCRAPING COMPLETO FINALIZADO")
    print("="*70)
    print(f"\nFim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total de imoveis extraidos: {total_properties}")
    print(f"Sites com sucesso: {sum(1 for r in all_results if r['success'])}/{len(all_results)}")
    
    print("\n[FILES] Arquivos gerados:")
    print("   - scraping_gigantes_consolidado.json (relatorio geral)")
    for r in all_results:
        print(f"   - resultado_{r['id']}.json ({r['total_properties']} imoveis)")


if __name__ == "__main__":
    asyncio.run(main())
