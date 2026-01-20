# TAREFA AUTÔNOMA COMPLETA: Corrigir Fly.io + Portal Zuk + Diagnóstico

**Prioridade:** 🔴 CRÍTICA  
**Tempo estimado:** 90-120 minutos  
**Execução:** AUTÔNOMA (não parar para perguntar)

---

## CONTEXTO

O LeiloHub tem vários problemas críticos:
1. Backend no Fly.io com warning de porta (pode estar inacessível)
2. Portal Zuk (maior leiloeiro) com ZERO imóveis
3. Apenas 10% dos scrapers funcionando
4. Imagens inválidas no banco (SQL precisa ser executado manualmente)

---

## PARTE 1: CORRIGIR PORTA DO FLY.IO (URGENTE)

### 1.1 Diagnosticar o problema

```bash
# Ver configuração atual do fly.toml
cat leilao-backend/fly.toml

# Ver como o app inicia no Dockerfile
cat leilao-backend/Dockerfile

# Procurar configuração de porta
grep -r "8080\|8000\|uvicorn\|gunicorn" leilao-backend/ --include="*.py" --include="*.toml" --include="Dockerfile" --include="*.yaml" --include="*.yml"
```

### 1.2 Corrigir fly.toml

O `fly.toml` deve ter:
```toml
[http_service]
  internal_port = 8080  # DEVE coincidir com a porta do Uvicorn
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1
```

### 1.3 Corrigir Dockerfile

O Dockerfile DEVE ter:
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**IMPORTANTE:** 
- Host DEVE ser `0.0.0.0` (não `127.0.0.1` ou `localhost`)
- Porta DEVE coincidir com `internal_port` do fly.toml

### 1.4 Verificar se há Procfile

```bash
cat leilao-backend/Procfile 2>/dev/null || echo "Procfile não existe"
```

Se existir, deve ter:
```
web: uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### 1.5 Após correções, fazer commit

```bash
cd leilao-backend
git add fly.toml Dockerfile Procfile 2>/dev/null
git commit -m "fix: correct Fly.io port binding to 0.0.0.0:8080" || echo "Nada para commitar"
git push
```

### 1.6 Re-deploy (se houve mudanças)

```bash
cd leilao-backend
flyctl deploy --app leilao-backend-solitary-haze-9882
```

### 1.7 Verificar se funcionou

```bash
# Aguardar deploy
sleep 30

# Testar endpoint
curl -s https://leilao-backend-solitary-haze-9882.fly.dev/healthz || echo "ERRO: Backend não acessível"

# Ver status
flyctl status --app leilao-backend-solitary-haze-9882
```

---

## PARTE 2: CRIAR SCRAPER PORTAL ZUK

### 2.1 Analisar estrutura do site

```bash
# Baixar página inicial para análise
curl -s "https://www.portalzuk.com.br/leilao-de-imoveis" -o /tmp/portalzuk.html
head -500 /tmp/portalzuk.html

# Procurar padrões de links de imóveis
grep -o 'href="[^"]*imovel[^"]*"' /tmp/portalzuk.html | head -20
```

### 2.2 Criar scraper com Playwright

**Arquivo:** `leilao-backend/app/scrapers/portalzuk_scraper_v2.py`

```python
"""
Portal Zuk Scraper V2 - Usando Playwright com Stealth
Baseado no padrão do pestana_scraper.py
"""
import asyncio
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
except ImportError:
    print("Playwright não instalado. Execute: pip install playwright && playwright install chromium")

logger = logging.getLogger(__name__)


class PortalZukScraperV2:
    """Scraper para Portal Zuk usando Playwright com técnicas de stealth."""
    
    BASE_URL = "https://www.portalzuk.com.br"
    LISTING_URL = f"{BASE_URL}/leilao-de-imoveis"
    AUCTIONEER_ID = "portal_zuk"
    AUCTIONEER_NAME = "Portal Zuk"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.properties: List[Dict] = []
    
    def scrape_properties(self, max_properties: Optional[int] = None) -> List[Dict]:
        """Interface síncrona para compatibilidade com scraper_manager."""
        return asyncio.run(self._scrape_async(max_properties))
    
    async def _setup_browser(self):
        """Configura browser com stealth."""
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
        
        # Scripts de stealth
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)
        
        self.page = await self.context.new_page()
    
    async def _close_browser(self):
        """Fecha browser."""
        if self.browser:
            await self.browser.close()
    
    async def _scrape_async(self, max_properties: Optional[int] = None) -> List[Dict]:
        """Implementação assíncrona do scraping."""
        try:
            await self._setup_browser()
            logger.info(f"🚀 Iniciando scraping do Portal Zuk")
            
            # Navegar para listagem
            await self.page.goto(self.LISTING_URL, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)
            
            # Verificar se carregou
            page_content = await self.page.content()
            if len(page_content) < 1000:
                logger.error("❌ Página não carregou corretamente")
                return []
            
            # Coletar links de imóveis
            property_links = await self._collect_property_links(max_properties)
            logger.info(f"📋 Encontrados {len(property_links)} links de imóveis")
            
            # Extrair dados de cada imóvel
            for i, url in enumerate(property_links):
                if max_properties and i >= max_properties:
                    break
                    
                logger.info(f"🏠 [{i+1}/{len(property_links)}] Extraindo: {url}")
                property_data = await self._extract_property(url)
                
                if property_data and property_data.get('title'):
                    self.properties.append(property_data)
                    logger.info(f"   ✅ {property_data.get('title', 'Sem título')}")
                else:
                    logger.warning(f"   ⚠️ Dados incompletos")
                
                await asyncio.sleep(2)  # Rate limiting
            
            logger.info(f"✅ Scraping concluído: {len(self.properties)} imóveis extraídos")
            return self.properties
            
        except Exception as e:
            logger.error(f"❌ Erro no scraping: {e}")
            return []
        finally:
            await self._close_browser()
    
    async def _collect_property_links(self, max_properties: Optional[int] = None) -> List[str]:
        """Coleta links de imóveis com paginação."""
        all_links = set()
        page_num = 1
        max_pages = 50  # Limite de segurança
        
        while page_num <= max_pages:
            # Tentar diferentes padrões de URL
            if page_num == 1:
                url = self.LISTING_URL
            else:
                # Tentar padrões comuns de paginação
                url = f"{self.LISTING_URL}?page={page_num}"
            
            try:
                await self.page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                # Scroll para carregar lazy content
                await self._scroll_page()
                
                # Buscar links de imóveis
                links = await self.page.query_selector_all('a[href*="/imovel/"], a[href*="/lote/"], a[href*="imoveis/"]')
                
                page_links = set()
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                        # Filtrar apenas links de detalhes de imóveis
                        if '/imovel/' in full_url or '/lote/' in full_url:
                            page_links.add(full_url)
                
                if not page_links:
                    logger.info(f"   Página {page_num}: nenhum link novo, parando paginação")
                    break
                
                new_links = page_links - all_links
                if not new_links:
                    logger.info(f"   Página {page_num}: todos links já coletados, parando")
                    break
                
                all_links.update(new_links)
                logger.info(f"   Página {page_num}: +{len(new_links)} links (total: {len(all_links)})")
                
                if max_properties and len(all_links) >= max_properties:
                    break
                
                page_num += 1
                
            except Exception as e:
                logger.warning(f"   Erro na página {page_num}: {e}")
                break
        
        return list(all_links)[:max_properties] if max_properties else list(all_links)
    
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
                            if (totalHeight >= document.body.scrollHeight) {
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                        setTimeout(() => { clearInterval(timer); resolve(); }, 5000);
                    });
                }
            """)
            await asyncio.sleep(1)
        except:
            pass
    
    async def _extract_property(self, url: str) -> Optional[Dict]:
        """Extrai dados de um imóvel específico."""
        try:
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Dados básicos
            property_data = {
                'source_url': url,
                'url': url,
                'auctioneer_url': self.BASE_URL,
                'auctioneer_name': self.AUCTIONEER_NAME,
                'auctioneer_id': self.AUCTIONEER_ID,
                'created_at': datetime.utcnow().isoformat(),
            }
            
            # Extrair título
            title_selectors = ['h1', '.property-title', '.titulo', '[class*="title"]']
            for selector in title_selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if text and len(text) > 5:
                        property_data['title'] = text.strip()
                        break
            
            # Extrair localização do título ou da página
            page_text = await self.page.inner_text('body')
            
            # Tentar extrair estado e cidade
            state, city = self._extract_location(page_text, property_data.get('title', ''))
            property_data['state'] = state
            property_data['city'] = city
            
            # Extrair categoria
            property_data['category'] = self._extract_category(page_text, property_data.get('title', ''))
            
            # Extrair valores
            property_data.update(self._extract_values(page_text))
            
            # Extrair imagem
            img_selectors = ['img.property-image', '.gallery img', '[class*="foto"] img', '.carousel img', 'img[src*="imovel"]']
            for selector in img_selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    src = await elem.get_attribute('src')
                    if src and not any(x in src.lower() for x in ['logo', 'icon', 'placeholder']):
                        property_data['image_url'] = src if src.startswith('http') else f"{self.BASE_URL}{src}"
                        break
            
            # Extrair área
            area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', page_text)
            if area_match:
                property_data['area_total'] = float(area_match.group(1).replace(',', '.'))
            
            # Extrair tipo de leilão
            if any(x in page_text.lower() for x in ['judicial', 'vara', 'comarca', 'processo']):
                property_data['auction_type'] = 'Judicial'
            elif any(x in page_text.lower() for x in ['extrajudicial', '9.514', '9514']):
                property_data['auction_type'] = 'Extrajudicial'
            else:
                property_data['auction_type'] = 'Extrajudicial'  # Default Portal Zuk
            
            return property_data
            
        except Exception as e:
            logger.error(f"Erro ao extrair {url}: {e}")
            return None
    
    def _extract_location(self, text: str, title: str) -> tuple:
        """Extrai estado e cidade do texto."""
        # Padrão: Cidade - UF ou Cidade/UF
        patterns = [
            r'([A-Za-zÀ-ú\s]+)\s*[-/]\s*([A-Z]{2})\b',
            r'\b([A-Z]{2})\s*[-/]\s*([A-Za-zÀ-ú\s]+)',
        ]
        
        combined = f"{title} {text}"
        
        # Lista de estados brasileiros
        states = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 
                  'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 
                  'SP', 'SE', 'TO']
        
        for pattern in patterns:
            match = re.search(pattern, combined)
            if match:
                g1, g2 = match.groups()
                if g2.upper() in states:
                    return g2.upper(), g1.strip().title()
                elif g1.upper() in states:
                    return g1.upper(), g2.strip().title()
        
        # Buscar estado isolado
        for state in states:
            if re.search(rf'\b{state}\b', combined):
                return state, None
        
        return None, None
    
    def _extract_category(self, text: str, title: str) -> str:
        """Extrai categoria do imóvel."""
        combined = f"{title} {text}".lower()
        
        categories = {
            'Apartamento': ['apartamento', 'apto', 'flat', 'studio', 'kitnet'],
            'Casa': ['casa', 'sobrado', 'residência', 'residencia'],
            'Terreno': ['terreno', 'lote', 'gleba', 'área', 'area'],
            'Comercial': ['comercial', 'loja', 'sala', 'escritório', 'escritorio', 'galpão', 'galpao'],
            'Rural': ['rural', 'fazenda', 'sítio', 'sitio', 'chácara', 'chacara'],
        }
        
        for category, keywords in categories.items():
            if any(kw in combined for kw in keywords):
                return category
        
        return 'Outro'
    
    def _extract_values(self, text: str) -> Dict:
        """Extrai valores monetários do texto."""
        values = {}
        
        # Padrões de valores
        patterns = {
            'evaluation_value': [r'avalia[çc][ãa]o[:\s]*R?\$?\s*([\d.,]+)', r'valor\s+de\s+avalia[çc][ãa]o[:\s]*R?\$?\s*([\d.,]+)'],
            'first_auction_value': [r'1[ºª°]?\s*(?:leil[ãa]o|pra[çc]a)[:\s]*R?\$?\s*([\d.,]+)', r'primeiro\s+leil[ãa]o[:\s]*R?\$?\s*([\d.,]+)'],
            'second_auction_value': [r'2[ºª°]?\s*(?:leil[ãa]o|pra[çc]a)[:\s]*R?\$?\s*([\d.,]+)', r'segundo\s+leil[ãa]o[:\s]*R?\$?\s*([\d.,]+)'],
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value_str = match.group(1).replace('.', '').replace(',', '.')
                    try:
                        values[field] = float(value_str)
                        break
                    except:
                        pass
        
        # Lance mínimo / valor atual
        lance_patterns = [r'lance\s*m[íi]nimo[:\s]*R?\$?\s*([\d.,]+)', r'valor\s*m[íi]nimo[:\s]*R?\$?\s*([\d.,]+)']
        for pattern in lance_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace('.', '').replace(',', '.')
                try:
                    values['minimum_bid'] = float(value_str)
                    break
                except:
                    pass
        
        # Calcular desconto se tiver avaliação e valor de leilão
        if values.get('evaluation_value') and values.get('second_auction_value'):
            discount = ((values['evaluation_value'] - values['second_auction_value']) / values['evaluation_value']) * 100
            values['discount_percentage'] = round(discount, 2)
        
        return values


# Teste standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    scraper = PortalZukScraperV2(headless=False)  # False para debug
    properties = scraper.scrape_properties(max_properties=5)
    
    print(f"\n{'='*60}")
    print(f"RESULTADO: {len(properties)} imóveis extraídos")
    print('='*60)
    
    for p in properties:
        print(f"\n📍 {p.get('title', 'Sem título')}")
        print(f"   Local: {p.get('city')}, {p.get('state')}")
        print(f"   Categoria: {p.get('category')}")
        print(f"   Avaliação: R$ {p.get('evaluation_value', 'N/A')}")
        print(f"   1º Leilão: R$ {p.get('first_auction_value', 'N/A')}")
        print(f"   2º Leilão: R$ {p.get('second_auction_value', 'N/A')}")
        print(f"   URL: {p.get('source_url')}")
```

### 2.3 Testar o scraper

```bash
cd leilao-backend

# Instalar playwright se necessário
pip install playwright
playwright install chromium

# Testar com 5 imóveis
python -m app.scrapers.portalzuk_scraper_v2
```

### 2.4 Registrar scraper no sistema

Verificar se precisa adicionar ao `scraper_manager.py` ou similar:

```bash
grep -r "portalzuk\|PortalZuk" leilao-backend/app/ --include="*.py"
```

---

## PARTE 3: CRIAR SCRIPT DE DIAGNÓSTICO

**Arquivo:** `leilao-backend/scripts/diagnostico_scrapers.py`

```python
#!/usr/bin/env python3
"""
Diagnóstico completo do sistema de scrapers do LeiloHub
"""
import os
import sys
from datetime import datetime, timedelta

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("❌ ERRO: SUPABASE_URL e SUPABASE_KEY não configurados")
        sys.exit(1)
    return create_client(url, key)

def main():
    print("="*60)
    print("DIAGNÓSTICO DO SISTEMA DE SCRAPERS - LEILOHUB")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    supabase = get_supabase()
    
    # 1. Status geral dos leiloeiros
    print("\n📊 STATUS DOS LEILOEIROS")
    print("-"*40)
    
    result = supabase.table("auctioneers").select("scrape_status").execute()
    status_count = {}
    for row in result.data:
        status = row.get('scrape_status', 'unknown')
        status_count[status] = status_count.get(status, 0) + 1
    
    total = sum(status_count.values())
    for status, count in sorted(status_count.items(), key=lambda x: -x[1]):
        pct = (count / total * 100) if total > 0 else 0
        emoji = "✅" if status == "success" else "❌" if status == "error" else "⏳"
        print(f"  {emoji} {status}: {count} ({pct:.1f}%)")
    print(f"  TOTAL: {total}")
    
    # 2. TOP 20 leiloeiros por imóveis
    print("\n🏆 TOP 20 LEILOEIROS POR IMÓVEIS")
    print("-"*40)
    
    result = supabase.table("auctioneers")\
        .select("name, property_count, scrape_status, last_scrape")\
        .order("property_count", desc=True)\
        .limit(20)\
        .execute()
    
    for i, row in enumerate(result.data, 1):
        status_emoji = "✅" if row['scrape_status'] == "success" else "❌"
        last = row.get('last_scrape', 'Nunca')
        if last and last != 'Nunca':
            last = last[:10]  # Só data
        print(f"  {i:2}. {row['name'][:25]:<25} {row['property_count']:>5} imóveis {status_emoji} (último: {last})")
    
    # 3. Imóveis por fonte (do banco properties)
    print("\n📦 IMÓVEIS POR FONTE (tabela properties)")
    print("-"*40)
    
    result = supabase.rpc("get_properties_by_source").execute()
    if result.data:
        for row in result.data[:20]:
            print(f"  {row['auctioneer_name'][:30]:<30} {row['total']:>6} imóveis")
    else:
        # Fallback: query direta
        result = supabase.table("properties")\
            .select("auctioneer_name")\
            .eq("is_active", True)\
            .execute()
        
        source_count = {}
        for row in result.data:
            source = row.get('auctioneer_name', 'Desconhecido')
            source_count[source] = source_count.get(source, 0) + 1
        
        for source, count in sorted(source_count.items(), key=lambda x: -x[1])[:20]:
            print(f"  {source[:30]:<30} {count:>6} imóveis")
    
    # 4. Scrapes recentes (últimos 7 dias)
    print("\n📅 ATIVIDADE DOS ÚLTIMOS 7 DIAS")
    print("-"*40)
    
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    result = supabase.table("auctioneers")\
        .select("name, last_scrape, property_count")\
        .gte("last_scrape", week_ago)\
        .order("last_scrape", desc=True)\
        .limit(20)\
        .execute()
    
    if result.data:
        for row in result.data:
            last = row['last_scrape'][:16] if row.get('last_scrape') else 'N/A'
            print(f"  {last} - {row['name'][:25]:<25} ({row['property_count']} imóveis)")
    else:
        print("  ⚠️ Nenhum scrape nos últimos 7 dias!")
    
    # 5. Leiloeiros com erro
    print("\n❌ LEILOEIROS COM ERRO (amostra)")
    print("-"*40)
    
    result = supabase.table("auctioneers")\
        .select("name, scrape_error, website")\
        .eq("scrape_status", "error")\
        .not_.is_("scrape_error", "null")\
        .limit(10)\
        .execute()
    
    for row in result.data:
        error = row.get('scrape_error', 'N/A')[:50]
        print(f"  {row['name'][:20]:<20} - {error}")
    
    # 6. Resumo final
    print("\n" + "="*60)
    print("📋 RESUMO")
    print("="*60)
    
    success = status_count.get('success', 0)
    error = status_count.get('error', 0)
    pending = status_count.get('pending', 0)
    
    print(f"  ✅ Funcionando: {success} ({success/total*100:.1f}%)")
    print(f"  ❌ Com erro: {error} ({error/total*100:.1f}%)")
    print(f"  ⏳ Pendentes: {pending} ({pending/total*100:.1f}%)")
    
    if success < total * 0.3:
        print("\n  🚨 ALERTA: Menos de 30% dos scrapers funcionando!")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
```

### 3.2 Testar diagnóstico

```bash
cd leilao-backend
python scripts/diagnostico_scrapers.py
```

---

## PARTE 4: CRIAR WORKFLOW PARA TODOS OS SCRAPERS

**Arquivo:** `.github/workflows/scrape-all-leiloeiros.yml`

```yaml
name: Scrape All Leiloeiros

on:
  schedule:
    # Rodar diariamente às 4h BRT (7h UTC)
    - cron: '0 7 * * *'
  workflow_dispatch:
    inputs:
      max_properties:
        description: 'Max imóveis por leiloeiro (0 = todos)'
        required: false
        default: '100'

jobs:
  scrape:
    runs-on: ubuntu-latest
    timeout-minutes: 180

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd leilao-backend
          pip install -r requirements.txt
          pip install playwright
          playwright install chromium

      - name: Run Portal Zuk scraper
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: |
          cd leilao-backend
          python -c "
          from app.scrapers.portalzuk_scraper_v2 import PortalZukScraperV2
          scraper = PortalZukScraperV2(headless=True)
          props = scraper.scrape_properties(max_properties=${{ github.event.inputs.max_properties || '100' }})
          print(f'Portal Zuk: {len(props)} imóveis')
          "

      - name: Run diagnostics
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: |
          cd leilao-backend
          python scripts/diagnostico_scrapers.py
```

---

## PARTE 5: COMMIT E DEPLOY

```bash
# Adicionar todos os arquivos novos/modificados
git add .

# Commit
git commit -m "feat: add Portal Zuk scraper v2, diagnostics, and scraping workflow

- Add PortalZukScraperV2 with Playwright and stealth
- Add diagnostico_scrapers.py for system health check
- Add scrape-all-leiloeiros.yml workflow
- Fix Fly.io port binding if needed"

# Push
git push origin main

# Re-deploy backend se houve mudança no Dockerfile/fly.toml
cd leilao-backend
flyctl deploy --app leilao-backend-solitary-haze-9882
```

---

## CRITÉRIOS DE SUCESSO

- [ ] Backend acessível em https://leilao-backend-solitary-haze-9882.fly.dev/healthz
- [ ] Scraper Portal Zuk criado e funcional
- [ ] Pelo menos 5 imóveis extraídos do Portal Zuk em teste
- [ ] Script de diagnóstico funcionando
- [ ] Workflow scrape-all-leiloeiros.yml criado
- [ ] Commit e push realizados

---

## ARQUIVOS CRIADOS/MODIFICADOS

1. `leilao-backend/fly.toml` - Corrigido se necessário
2. `leilao-backend/Dockerfile` - Corrigido se necessário
3. `leilao-backend/app/scrapers/portalzuk_scraper_v2.py` - NOVO
4. `leilao-backend/scripts/diagnostico_scrapers.py` - NOVO
5. `.github/workflows/scrape-all-leiloeiros.yml` - NOVO

---

## REPORTAR AO FINAL

Informar:
1. Se o backend está acessível
2. Quantos imóveis o Portal Zuk extraiu
3. Resultado do diagnóstico (% funcionando)
4. Erros encontrados (se houver)
