# Padrão para Scrapers Complexos com Playwright

Este documento descreve o padrão utilizado para criar scrapers complexos que requerem renderização de JavaScript e técnicas de stealth para bypassar detecção de automação.

## Visão Geral

Scrapers complexos são necessários quando:
- O site requer JavaScript para renderizar conteúdo (SPA - Single Page Application)
- O site detecta e bloqueia requisições HTTP simples
- O site exibe mensagens de "Navegador Incompatível" ou similar
- O conteúdo é carregado dinamicamente via AJAX/WebSockets

**Exemplo de implementação:** `app/scrapers/pestana_scraper.py`

## Arquitetura

### Estrutura Base

```python
class ScraperComplexo:
    """Scraper usando Playwright com Stealth."""
    
    BASE_URL = "https://exemplo.com.br"
    IMOVEIS_URL = f"{BASE_URL}/imoveis"
    AUCTIONEER_ID = "exemplo_id"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.properties: List[Dict] = []
        self.incomplete_properties: List[Dict] = []
```

### Componentes Principais

1. **Setup do Browser com Stealth** (`_setup_browser`)
2. **Método Principal de Scraping** (`scrape_properties` / `_scrape_properties_async`)
3. **Extração de Página Individual** (`_scrape_property_page`)
4. **Utilitários de Parsing** (`_parse_price`, `_extract_state_city`, `_determine_category`)
5. **Validação de Completude** (`_is_complete`)

## Configuração de Stealth

### 1. Argumentos do Chromium

```python
browser = await playwright.chromium.launch(
    headless=self.headless,
    args=[
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-blink-features=AutomationControlled',  # Crucial para stealth
        '--disable-features=IsolateOrigins,site-per-process',
        '--window-size=1920,1080',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--disable-infobars',
        '--disable-notifications',
    ]
)
```

### 2. Contexto do Browser

```python
context = await browser.new_context(
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
```

### 3. Scripts de Stealth JavaScript

Os scripts injetados são essenciais para ocultar automação:

```javascript
// Ocultar webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => false
});

// Remover webdriver do navigator
delete navigator.__proto__.webdriver;

// Sobrescrever plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [];
        for (let i = 0; i < 5; i++) {
            plugins.push({
                name: `Plugin ${i}`,
                description: `Description ${i}`,
                filename: `plugin${i}.dll`
            });
        }
        return plugins;
    }
});

// Sobrescrever languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['pt-BR', 'pt', 'en-US', 'en']
});

// Ocultar chrome
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// Sobrescrever getBattery
if (navigator.getBattery) {
    navigator.getBattery = () => Promise.resolve({
        charging: true,
        chargingTime: 0,
        dischargingTime: Infinity,
        level: 1
    });
}

// Propriedades adicionais
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
Object.defineProperty(navigator, 'onLine', { get: () => true });
Object.defineProperty(navigator, 'cookieEnabled', { get: () => true });
```

## Fluxo de Execução

### 1. Método Principal (Síncrono)

```python
def scrape_properties(self, max_properties: Optional[int] = None) -> List[Dict]:
    """
    Método síncrono que chama a versão assíncrona internamente.
    Mantém compatibilidade com código existente.
    """
    return asyncio.run(self._scrape_properties_async(max_properties))
```

### 2. Método Assíncrono Principal

```python
async def _scrape_properties_async(self, max_properties: Optional[int] = None) -> List[Dict]:
    """Scrape properties (versão assíncrona)."""
    try:
        # 1. Setup do browser
        await self._setup_browser()
        
        # 2. Navegar para página de listagem
        await self.page.goto(self.IMOVEIS_URL, wait_until='networkidle', timeout=60000)
        await asyncio.sleep(3)  # Aguardar JavaScript
        
        # 3. Verificar bloqueios
        page_text = await self.page.evaluate("() => document.body.innerText")
        if 'navegador incompatível' in page_text.lower():
            logger.warning("⚠️ Bloqueio detectado, mas continuando...")
            await asyncio.sleep(5)
        
        # 4. Aguardar elementos aparecerem
        await self.page.wait_for_selector("a[href*='/imovel/']", timeout=30000)
        
        # 5. Scroll para carregar conteúdo lazy
        await self._scroll_to_load_content()
        
        # 6. Encontrar links de propriedades
        property_links = await self.page.query_selector_all("a[href*='/imovel/']")
        
        # 7. Filtrar URLs únicas
        unique_links = self._filter_unique_links(property_links)
        
        # 8. Scrape cada propriedade
        for url in unique_links[:max_properties]:
            property_data = await self._scrape_property_page(url)
            if property_data and self._is_complete(property_data):
                self.properties.append(property_data)
            await asyncio.sleep(2)  # Pausa entre requisições
        
        # 9. Atualizar métricas
        structure_validator.update_validation_metrics(
            auctioneer_id=self.AUCTIONEER_ID,
            success=len(self.properties) > 0,
            properties_count=len(self.properties)
        )
        
        return self.properties
        
    except Exception as e:
        logger.error(f"❌ Erro durante scraping: {e}")
        return []
    finally:
        await self._close_browser()
```

### 3. Extração de Página Individual

```python
async def _scrape_property_page(self, url: str) -> Optional[Dict]:
    """Scrape a single property page."""
    try:
        # Navegar para página
        await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        property_data = {
            'source_url': url,
            'url': url,
            'auctioneer_url': url,
            'auctioneer_name': 'Nome do Leiloeiro',
            'auctioneer_id': self.AUCTIONEER_ID,
        }
        
        # Extrair título
        title_elem = await self.page.query_selector("h1, h2.title")
        if title_elem:
            property_data['title'] = await title_elem.inner_text()
        
        # Extrair localização
        if property_data.get('title'):
            state, city = self._extract_state_city(property_data['title'])
            property_data['state'] = state
            property_data['city'] = city
            property_data['category'] = self._determine_category(property_data['title'])
        
        # Extrair preços (HTML + texto visível)
        page_text = await self.page.content()
        page_visible_text = await self.page.evaluate("() => document.body.innerText")
        
        # Procurar preços com regex
        lance_match = re.search(r'Lance\s+(?:mínimo|inicial):?\s*R\$\s*([\d.,]+)', page_visible_text, re.IGNORECASE)
        if lance_match:
            property_data['price'] = self._parse_price(lance_match.group(1))
        
        # Extrair outros campos...
        
        return property_data
        
    except Exception as e:
        logger.error(f"Erro ao fazer scraping: {e}")
        return None
```

## Utilitários Essenciais

### Parsing de Preços

```python
def _parse_price(self, price_str: str) -> Optional[float]:
    """Parse Brazilian currency format to float."""
    if not price_str:
        return None
    try:
        clean = re.sub(r'[R$\s]', '', price_str)
        clean = clean.replace('.', '').replace(',', '.')
        return float(clean)
    except (ValueError, AttributeError):
        return None
```

### Extração de Localização

```python
def _extract_state_city(self, location_str: str) -> tuple:
    """Extract state and city from location string."""
    if not location_str:
        return None, None
    
    # Suportar múltiplos formatos
    parts = location_str.split(' - ')
    if len(parts) >= 2:
        city = parts[0].strip()
        state = parts[-1].strip()
        return state, city
    
    return None, location_str.strip()
```

### Determinação de Categoria

```python
def _determine_category(self, title: str) -> str:
    """Determine property category from title."""
    if not title:
        return 'Outro'
    
    title_lower = title.lower()
    if 'apartamento' in title_lower:
        return 'Apartamento'
    elif 'casa' in title_lower:
        return 'Casa'
    elif 'terreno' in title_lower:
        return 'Terreno'
    # ... mais categorias
    return 'Comercial'
```

### Validação de Completude

```python
def _is_complete(self, property_data: Dict) -> bool:
    """Check if property has all required fields."""
    required_fields = ['title', 'source_url']
    important_fields = ['state', 'city', 'price']
    
    # Verificar campos obrigatórios
    for field in required_fields:
        if not property_data.get(field):
            return False
    
    # Considerar completo se tiver pelo menos 2 campos importantes
    important_count = sum(1 for field in important_fields if property_data.get(field))
    return important_count >= 2
```

## Scroll para Conteúdo Lazy-Loaded

```python
async def _scroll_to_load_content(self):
    """Scroll page to load lazy-loaded content."""
    if not self.page:
        return
    
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
        await asyncio.sleep(2)  # Aguardar conteúdo carregar
    except Exception as e:
        logger.debug(f"Erro ao fazer scroll: {e}")
```

## Integração com Structure Validator

```python
# Atualizar métricas após scraping
try:
    structure_validator.update_validation_metrics(
        auctioneer_id=self.AUCTIONEER_ID,
        success=len(self.properties) > 0,
        properties_count=len(self.properties)
    )
    logger.info("✅ Métricas de validação atualizadas")
except Exception as e:
    logger.warning(f"⚠️ Erro ao atualizar métricas: {e}")
```

## Tratamento de Erros

### Bloqueios Detectados

```python
# Verificar se há mensagem de bloqueio
page_text = await self.page.evaluate("() => document.body.innerText")
if 'navegador incompatível' in page_text.lower():
    logger.warning("⚠️ Bloqueio detectado, mas continuando...")
    await asyncio.sleep(5)
    # Verificar novamente se conteúdo carregou
    page_text = await self.page.evaluate("() => document.body.innerText")
    if len(page_text) < 500:
        logger.error("❌ Bloqueio persistente")
```

### Timeouts

```python
try:
    await self.page.wait_for_selector("a[href*='/imovel/']", timeout=30000)
    logger.info("✅ Elementos detectados")
except PlaywrightTimeoutError:
    logger.warning("⚠️ Timeout aguardando elementos")
    # Continuar mesmo assim, pode ter carregado
    await asyncio.sleep(2)
```

## Formato de Dados Retornado

Cada propriedade deve retornar um dicionário com:

```python
{
    'source_url': str,              # URL da página da propriedade
    'url': str,                     # Alias para source_url
    'auctioneer_url': str,          # URL do leiloeiro
    'auctioneer_name': str,         # Nome do leiloeiro
    'auctioneer_id': str,           # ID do leiloeiro
    'title': str,                   # Título da propriedade
    'state': str,                   # Estado (UF)
    'city': str,                    # Cidade
    'category': str,                # Categoria (Apartamento, Casa, etc.)
    'price': float,                 # Preço (lance inicial)
    'second_auction_value': float,  # Valor do 2º leilão
    'evaluation_value': float,      # Valor de avaliação
    'first_auction_value': float,   # Valor do 1º leilão
    'discount_percentage': float,   # Percentual de desconto
    'auction_type': str,            # 'Judicial' ou 'Extrajudicial'
    'area_total': float,            # Área total em m²
    'image_url': str,               # URL da imagem principal
    'auction_date': str,            # Data do leilão (YYYY-MM-DD)
    'first_auction_date': str,      # Data do 1º leilão
}
```

## Checklist para Criar Novo Scraper

- [ ] Copiar estrutura base do `pestana_scraper.py`
- [ ] Ajustar `BASE_URL` e `IMOVEIS_URL` para o site alvo
- [ ] Definir `AUCTIONEER_ID` único
- [ ] Adaptar seletores CSS para encontrar links de propriedades
- [ ] Adaptar seletores para extrair título, preço, imagem
- [ ] Ajustar `_extract_state_city` para formato de localização do site
- [ ] Testar com `headless=False` primeiro para debug
- [ ] Verificar se stealth bypassa bloqueios
- [ ] Integrar com `structure_validator`
- [ ] Adicionar tratamento de erros específicos do site
- [ ] Documentar seletores e padrões específicos

## Exemplo de Uso

```python
from app.scrapers.pestana_scraper import PestanaScraper

# Criar instância
scraper = PestanaScraper(headless=True)

# Executar scraping
properties = scraper.scrape_properties(max_properties=10)

# Processar resultados
for prop in properties:
    print(f"{prop['title']} - {prop['city']}, {prop['state']}")
    print(f"Preço: R$ {prop['price']:,.2f}")
```

## Boas Práticas

1. **Sempre usar try/except** em operações de scraping
2. **Aguardar JavaScript carregar** antes de extrair dados
3. **Usar múltiplos seletores** como fallback
4. **Fazer scroll** para carregar conteúdo lazy-loaded
5. **Pausar entre requisições** para não sobrecarregar servidor
6. **Logar adequadamente** para debug
7. **Atualizar métricas** mesmo em caso de falha
8. **Fechar browser** no finally para evitar vazamentos

## Troubleshooting

### Problema: "Navegador Incompatível" ainda aparece

**Solução:**
- Verificar se scripts de stealth estão sendo injetados
- Aumentar tempo de espera após navegação
- Tentar `headless=False` para debug
- Verificar se User-Agent está correto

### Problema: Timeout aguardando elementos

**Solução:**
- Aumentar timeout do `wait_for_selector`
- Verificar se seletores CSS estão corretos
- Adicionar fallback para continuar mesmo sem wait
- Verificar se JavaScript carregou completamente

### Problema: Preços não são extraídos

**Solução:**
- Usar tanto `page.content()` quanto `page.evaluate("() => document.body.innerText")`
- Testar regex patterns manualmente
- Verificar se valores estão em formato diferente
- Adicionar múltiplos padrões de busca

## Referências

- **Playwright Documentation:** https://playwright.dev/python/
- **Stealth Techniques:** Baseado em práticas de bypass de detecção
- **Exemplo Completo:** `app/scrapers/pestana_scraper.py`
- **Exemplo Adaptado:** `app/scrapers/portalzuk_scraper_playwright.py`

