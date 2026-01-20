# 🎯 TAREFA FASE 1: MAPEAMENTO COMPLETO DE PAGINAÇÃO E EXTRAÇÃO

**Objetivo**: Mapear o tipo de paginação de TODOS os 128 leiloeiros funcionando e extrair todos os imóveis disponíveis.

**Tempo Estimado**: 4-6 horas (execução autônoma)

**Critério de Sucesso**: Relatório completo com tipo de paginação de cada leiloeiro + extração de 50.000+ imóveis

---

## ⚠️ INSTRUÇÕES CRÍTICAS

1. **EXECUTE DE FORMA AUTÔNOMA** - Não pare para perguntar, siga o fluxo até o final
2. **SALVE PROGRESSO FREQUENTEMENTE** - A cada 20 leiloeiros, salve checkpoint
3. **NÃO CONFIE EM NÚMEROS ALEATÓRIOS** - Visualizações, IDs, etc. NÃO são contagem de páginas
4. **IDENTIFIQUE O PADRÃO REAL** - Use os exemplos abaixo como referência

---

## 📚 TIPOS DE PAGINAÇÃO (REFERÊNCIA)

### Tipo 1: NUMERIC (Paginação Numérica)
**Exemplo**: Mega Leilões
- URL: `https://www.megaleiloes.com.br/imoveis?pagina=17`
- Identificador: Texto "Página X de Y" ou "Exibindo X-Y de Z itens"
- Navegação: Links numéricos (1, 2, 3... ou < > Início Fim)
- **Como extrair total**: Buscar texto regex `Página (\d+) de (\d+)` ou `de (\d+) itens`

### Tipo 2: INFINITE_SCROLL (Scroll Infinito / Botão Ver Mais)
**Exemplo**: Frazão Leilões
- URL: `https://frazaoleiloes.com.br/sale/searchLot?&categoria=Imóveis`
- Identificador: Botão "Ver Mais", "Carregar Mais", "Load More"
- **Como extrair total**: Clicar no botão repetidamente até não aparecer mais itens novos

### Tipo 3: TABS_FILTER (Abas/Filtros sem paginação real)
**Exemplo**: Gustavo Reis Leilões
- URL: `https://gustavoreisleiloes.com.br/?tipo=todos`
- Identificador: Abas como "Todos", "Leilão", "Judicial", "Extrajudicial"
- **ATENÇÃO**: Ignorar abas "Encerrados", "Cancelados", "Suspensos"
- **Como extrair total**: Contar cards/itens visíveis na página (geralmente poucos)

### Tipo 4: SINGLE_PAGE (Página Única)
- Todos os itens em uma única página, sem paginação
- **Como extrair total**: Contar todos os itens visíveis

### Tipo 5: API_JSON (API REST)
- Alguns sites carregam dados via API JSON
- Identificador: Requisições XHR para endpoints `/api/`, `/v1/`, etc.
- **Como extrair total**: Interceptar requisições e usar API diretamente

---

## 🔧 ETAPA 1: CRIAR SCRIPT DE MAPEAMENTO

**Arquivo**: `leilao-backend/scripts/mapear_paginacao_completo.py`

```python
#!/usr/bin/env python3
"""
MAPEAMENTO COMPLETO DE PAGINAÇÃO - 128 LEILOEIROS
Identifica o tipo de paginação de cada leiloeiro funcionando.
"""

import asyncio
import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Diretório de saída
OUTPUT_DIR = Path("logs/mapeamento_paginacao")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Tipos de paginação
class PaginationType:
    NUMERIC = "NUMERIC"              # ?page=1, ?pagina=1, links numéricos
    INFINITE_SCROLL = "INFINITE_SCROLL"  # Botão "Ver Mais"
    TABS_FILTER = "TABS_FILTER"      # Abas de filtro
    SINGLE_PAGE = "SINGLE_PAGE"      # Página única
    API_JSON = "API_JSON"            # Dados via API
    UNKNOWN = "UNKNOWN"              # Não identificado


class PaginationMapper:
    """Mapeia o tipo de paginação de cada leiloeiro."""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def setup_browser(self):
        """Configura o browser com stealth."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
        )
        self.page = await context.new_page()
        
        # Stealth scripts
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            window.chrome = { runtime: {} };
        """)
        
    async def close_browser(self):
        """Fecha o browser."""
        if self.browser:
            await self.browser.close()
            
    async def detect_pagination_type(self, url: str, name: str) -> Dict:
        """
        Detecta o tipo de paginação de um leiloeiro.
        
        Returns:
            {
                'name': str,
                'url': str,
                'pagination_type': str,
                'total_items': int or None,
                'total_pages': int or None,
                'url_pattern': str or None,
                'notes': str,
                'screenshot': str
            }
        """
        result = {
            'name': name,
            'url': url,
            'pagination_type': PaginationType.UNKNOWN,
            'total_items': None,
            'total_pages': None,
            'url_pattern': None,
            'notes': '',
            'screenshot': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            logger.info(f"🔍 Analisando: {name} - {url}")
            
            # Navegar para a página
            await self.page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)  # Aguardar JavaScript
            
            # Fazer scroll para carregar lazy content
            await self._scroll_page()
            
            # Capturar screenshot
            screenshot_path = SCREENSHOTS_DIR / f"{self._sanitize_filename(name)}.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=False)
            result['screenshot'] = str(screenshot_path)
            
            # Obter conteúdo da página
            page_text = await self.page.evaluate("() => document.body.innerText")
            page_html = await self.page.content()
            current_url = self.page.url
            
            # DETECÇÃO 1: Paginação Numérica
            numeric_result = await self._detect_numeric_pagination(page_text, page_html, current_url)
            if numeric_result['detected']:
                result['pagination_type'] = PaginationType.NUMERIC
                result['total_items'] = numeric_result.get('total_items')
                result['total_pages'] = numeric_result.get('total_pages')
                result['url_pattern'] = numeric_result.get('url_pattern')
                result['notes'] = numeric_result.get('notes', '')
                return result
            
            # DETECÇÃO 2: Scroll Infinito / Botão Ver Mais
            infinite_result = await self._detect_infinite_scroll(page_html)
            if infinite_result['detected']:
                result['pagination_type'] = PaginationType.INFINITE_SCROLL
                result['notes'] = infinite_result.get('notes', '')
                result['total_items'] = await self._count_visible_items()
                return result
            
            # DETECÇÃO 3: Abas/Filtros
            tabs_result = await self._detect_tabs_filter(page_html, page_text)
            if tabs_result['detected']:
                result['pagination_type'] = PaginationType.TABS_FILTER
                result['notes'] = tabs_result.get('notes', '')
                result['total_items'] = await self._count_visible_items()
                return result
            
            # DETECÇÃO 4: Página Única (fallback)
            result['pagination_type'] = PaginationType.SINGLE_PAGE
            result['total_items'] = await self._count_visible_items()
            result['total_pages'] = 1
            result['notes'] = 'Nenhuma paginação detectada - página única'
            
        except Exception as e:
            logger.error(f"❌ Erro ao analisar {name}: {e}")
            result['notes'] = f"Erro: {str(e)}"
            
        return result
    
    async def _scroll_page(self):
        """Faz scroll na página para carregar conteúdo lazy."""
        try:
            await self.page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 300;
                        const maxScroll = 5000;
                        const timer = setInterval(() => {
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if (totalHeight >= maxScroll) {
                                clearInterval(timer);
                                window.scrollTo(0, 0);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            await asyncio.sleep(1)
        except:
            pass
    
    async def _detect_numeric_pagination(self, page_text: str, page_html: str, current_url: str) -> Dict:
        """Detecta paginação numérica."""
        result = {'detected': False}
        
        # Padrão 1: "Página X de Y"
        match = re.search(r'[Pp]ágina\s+(\d+)\s+de\s+(\d+)', page_text)
        if match:
            result['detected'] = True
            result['total_pages'] = int(match.group(2))
            result['notes'] = f'Detectado: "Página {match.group(1)} de {match.group(2)}"'
        
        # Padrão 2: "Exibindo X-Y de Z itens"
        if not result['detected']:
            match = re.search(r'[Ee]xibindo\s+\d+\s*[-–]\s*\d+\s+de\s+(\d+)\s+itens?', page_text)
            if match:
                result['detected'] = True
                result['total_items'] = int(match.group(1))
                result['notes'] = f'Detectado: total de {match.group(1)} itens'
        
        # Padrão 3: "X de Y itens"
        if not result['detected']:
            match = re.search(r'(\d+)\s+de\s+(\d+)\s+(?:itens?|imóveis?|resultados?)', page_text, re.IGNORECASE)
            if match:
                result['detected'] = True
                result['total_items'] = int(match.group(2))
                result['notes'] = f'Detectado: {match.group(1)} de {match.group(2)} itens'
        
        # Padrão 4: Links de paginação no HTML
        if not result['detected']:
            # Procurar por links de paginação
            pagination_patterns = [
                r'[?&]page=(\d+)',
                r'[?&]pagina=(\d+)',
                r'[?&]p=(\d+)',
                r'/page/(\d+)',
                r'/pagina/(\d+)',
            ]
            
            for pattern in pagination_patterns:
                matches = re.findall(pattern, page_html, re.IGNORECASE)
                if matches:
                    max_page = max(int(m) for m in matches)
                    if max_page > 1:
                        result['detected'] = True
                        result['total_pages'] = max_page
                        result['url_pattern'] = pattern.replace(r'(\d+)', '{page}')
                        result['notes'] = f'Detectado via URL: máx página {max_page}'
                        break
        
        # Padrão 5: Botões Início/Fim ou < >
        if not result['detected']:
            if re.search(r'>\s*(Fim|Última|Last|»)\s*<', page_html, re.IGNORECASE):
                # Tem paginação mas não conseguimos o total
                result['detected'] = True
                result['notes'] = 'Paginação detectada (botões), total não identificado'
        
        return result
    
    async def _detect_infinite_scroll(self, page_html: str) -> Dict:
        """Detecta scroll infinito / botão ver mais."""
        result = {'detected': False}
        
        # Procurar botões de "Ver Mais", "Carregar Mais", etc.
        patterns = [
            r'>\s*(Ver [Mm]ais|Carregar [Mm]ais|Load [Mm]ore|Mostrar [Mm]ais)\s*<',
            r'class="[^"]*load-more[^"]*"',
            r'class="[^"]*ver-mais[^"]*"',
            r'class="[^"]*show-more[^"]*"',
            r'id="[^"]*load-more[^"]*"',
            r'data-action="[^"]*load-more[^"]*"',
        ]
        
        for pattern in patterns:
            if re.search(pattern, page_html, re.IGNORECASE):
                result['detected'] = True
                result['notes'] = 'Detectado: botão "Ver Mais" ou similar'
                break
        
        return result
    
    async def _detect_tabs_filter(self, page_html: str, page_text: str) -> Dict:
        """Detecta sistema de abas/filtros."""
        result = {'detected': False}
        
        # Procurar por abas comuns de leilão
        tab_keywords = [
            'Todos', 'Leilão', 'Leilões', 'Judicial', 'Extrajudicial',
            'Venda Direta', 'Encerrados', 'Cancelados', 'Suspensos'
        ]
        
        found_tabs = []
        for keyword in tab_keywords:
            if keyword in page_text:
                found_tabs.append(keyword)
        
        # Se encontrar múltiplas "abas" típicas, é sistema de filtro
        if len(found_tabs) >= 3:
            result['detected'] = True
            result['notes'] = f'Detectado: abas de filtro ({", ".join(found_tabs[:5])})'
        
        return result
    
    async def _count_visible_items(self) -> int:
        """Conta itens visíveis na página."""
        try:
            # Seletores comuns para cards de imóveis
            selectors = [
                'a[href*="/imovel/"]',
                'a[href*="/lote/"]',
                'a[href*="/item/"]',
                '.property-card',
                '.imovel-card',
                '.lote-card',
                '.card-imovel',
                '[class*="property"]',
                '[class*="imovel"]',
                '[class*="lote"]',
            ]
            
            max_count = 0
            for selector in selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if len(elements) > max_count:
                        max_count = len(elements)
                except:
                    pass
            
            return max_count if max_count > 0 else None
        except:
            return None
    
    def _sanitize_filename(self, name: str) -> str:
        """Remove caracteres inválidos do nome do arquivo."""
        return re.sub(r'[<>:"/\\|?*]', '_', name)
    
    async def process_all_auctioneers(self, auctioneers: List[Dict]) -> Dict:
        """
        Processa todos os leiloeiros.
        
        Args:
            auctioneers: Lista de dicts com 'name' e 'url'
        """
        await self.setup_browser()
        
        total = len(auctioneers)
        logger.info(f"📊 Iniciando mapeamento de {total} leiloeiros...")
        
        for i, auctioneer in enumerate(auctioneers, 1):
            name = auctioneer.get('name', 'Unknown')
            url = auctioneer.get('url', '')
            
            logger.info(f"\n[{i}/{total}] ═══════════════════════════════════")
            
            result = await self.detect_pagination_type(url, name)
            self.results[name] = result
            
            # Log do resultado
            ptype = result['pagination_type']
            items = result.get('total_items', '?')
            pages = result.get('total_pages', '?')
            logger.info(f"   Tipo: {ptype} | Itens: {items} | Páginas: {pages}")
            
            # Salvar checkpoint a cada 20 leiloeiros
            if i % 20 == 0:
                await self._save_checkpoint(i)
            
            # Pausa entre requisições
            await asyncio.sleep(2)
        
        await self.close_browser()
        
        # Salvar resultado final
        await self._save_final_report()
        
        return self.results
    
    async def _save_checkpoint(self, count: int):
        """Salva checkpoint do progresso."""
        checkpoint_file = OUTPUT_DIR / f"checkpoint_{count}.json"
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Checkpoint salvo: {checkpoint_file}")
    
    async def _save_final_report(self):
        """Salva relatório final."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Salvar JSON completo
        json_file = OUTPUT_DIR / f"mapeamento_completo_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        # Gerar relatório Markdown
        md_file = OUTPUT_DIR / f"RELATORIO_MAPEAMENTO_{timestamp}.md"
        
        # Agrupar por tipo
        by_type = {}
        for name, data in self.results.items():
            ptype = data.get('pagination_type', 'UNKNOWN')
            if ptype not in by_type:
                by_type[ptype] = []
            by_type[ptype].append(data)
        
        # Calcular estatísticas
        total_items = sum(
            r.get('total_items', 0) or 0 
            for r in self.results.values()
        )
        
        md_content = f"""# 📊 RELATÓRIO DE MAPEAMENTO DE PAGINAÇÃO

**Data**: {datetime.now().strftime('%d/%m/%Y %H:%M')}
**Total de Leiloeiros**: {len(self.results)}
**Total de Itens Identificados**: {total_items:,}

---

## 📈 RESUMO POR TIPO

| Tipo | Quantidade | % |
|------|------------|---|
"""
        
        for ptype, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
            pct = len(items) / len(self.results) * 100
            md_content += f"| {ptype} | {len(items)} | {pct:.1f}% |\n"
        
        md_content += "\n---\n\n"
        
        # Detalhar cada tipo
        for ptype, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
            md_content += f"## {ptype} ({len(items)} leiloeiros)\n\n"
            md_content += "| Leiloeiro | Itens | Páginas | URL | Notas |\n"
            md_content += "|-----------|-------|---------|-----|-------|\n"
            
            # Ordenar por número de itens (decrescente)
            sorted_items = sorted(items, key=lambda x: -(x.get('total_items') or 0))
            
            for item in sorted_items:
                name = item.get('name', 'Unknown')
                total_items = item.get('total_items', '-')
                total_pages = item.get('total_pages', '-')
                url = item.get('url', '')
                notes = item.get('notes', '')[:50]
                md_content += f"| {name} | {total_items} | {total_pages} | {url} | {notes} |\n"
            
            md_content += "\n"
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"\n✅ Relatório final salvo:")
        logger.info(f"   JSON: {json_file}")
        logger.info(f"   Markdown: {md_file}")


async def main():
    """Função principal."""
    
    # Carregar lista de leiloeiros funcionando
    # TODO: Carregar do banco de dados ou arquivo
    
    # Por enquanto, carregar do CSV
    import csv
    
    csv_path = Path("../LISTA_MESTRE_LEILOEIROS.csv")
    if not csv_path.exists():
        csv_path = Path("LISTA_MESTRE_LEILOEIROS.csv")
    if not csv_path.exists():
        csv_path = Path("docs/LISTA_MESTRE_LEILOEIROS.csv")
    
    auctioneers = []
    
    # Se não encontrar CSV, usar lista hardcoded dos funcionando
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Filtrar apenas os com scrape_status = success ou property_count > 0
                status = row.get('scrape_status', '')
                count = int(row.get('property_count', 0) or 0)
                if status == 'success' or count > 0:
                    auctioneers.append({
                        'name': row.get('name', ''),
                        'url': row.get('website', '')
                    })
    
    if not auctioneers:
        logger.error("❌ Nenhum leiloeiro encontrado! Verifique o arquivo CSV.")
        return
    
    logger.info(f"📋 Carregados {len(auctioneers)} leiloeiros para mapear")
    
    # Executar mapeamento
    mapper = PaginationMapper()
    results = await mapper.process_all_auctioneers(auctioneers)
    
    # Resumo final
    logger.info("\n" + "="*60)
    logger.info("🎉 MAPEAMENTO CONCLUÍDO!")
    logger.info("="*60)
    
    by_type = {}
    for name, data in results.items():
        ptype = data.get('pagination_type', 'UNKNOWN')
        if ptype not in by_type:
            by_type[ptype] = 0
        by_type[ptype] += 1
    
    for ptype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        logger.info(f"   {ptype}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔧 ETAPA 2: EXECUTAR MAPEAMENTO

```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
python scripts/mapear_paginacao_completo.py
```

**Tempo estimado**: 2-3 horas para 128 leiloeiros

**Arquivos gerados**:
- `logs/mapeamento_paginacao/mapeamento_completo_*.json` - Dados completos
- `logs/mapeamento_paginacao/RELATORIO_MAPEAMENTO_*.md` - Relatório visual
- `logs/mapeamento_paginacao/screenshots/` - Screenshots de cada site

---

## 🔧 ETAPA 3: CRIAR EXTRATOR INTELIGENTE

Após o mapeamento, criar script que extrai baseado no tipo detectado.

**Arquivo**: `leilao-backend/scripts/extrair_com_paginacao.py`

```python
#!/usr/bin/env python3
"""
EXTRATOR INTELIGENTE COM PAGINAÇÃO
Extrai todos os imóveis baseado no tipo de paginação mapeado.
"""

import asyncio
import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page, Browser
import logging

# Importar o LLMEnhancedScraper existente
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.services.llm_enhanced_scraper import LLMEnhancedScraper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("logs/extracao_completa")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class SmartExtractor:
    """Extrator inteligente que usa estratégia baseada no tipo de paginação."""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.scraper = LLMEnhancedScraper(headless=True)
        self.all_properties: List[Dict] = []
        
    async def setup_browser(self):
        """Configura browser."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='pt-BR',
        )
        self.page = await context.new_page()
        
    async def close_browser(self):
        if self.browser:
            await self.browser.close()
    
    async def extract_numeric_pagination(self, base_url: str, name: str, total_pages: int) -> List[Dict]:
        """Extrai de sites com paginação numérica."""
        properties = []
        
        # Detectar padrão de URL
        url_patterns = [
            ('?pagina=', '?pagina={}'),
            ('?page=', '?page={}'),
            ('&pagina=', '&pagina={}'),
            ('&page=', '&page={}'),
            ('/pagina/', '/pagina/{}'),
            ('/page/', '/page/{}'),
        ]
        
        pattern = None
        for check, fmt in url_patterns:
            if check in base_url.lower():
                pattern = fmt
                break
        
        if not pattern:
            # Tentar adicionar ?pagina=
            if '?' in base_url:
                pattern = '&pagina={}'
            else:
                pattern = '?pagina={}'
        
        # Extrair cada página
        max_pages = min(total_pages or 50, 100)  # Limite de segurança
        
        for page_num in range(1, max_pages + 1):
            try:
                # Construir URL da página
                if '{}' in pattern:
                    page_url = base_url.split('?')[0] + pattern.format(page_num)
                else:
                    page_url = base_url + pattern.format(page_num)
                
                logger.info(f"   📄 Página {page_num}/{max_pages}: {page_url}")
                
                # Usar LLMEnhancedScraper para extrair
                page_props = await self._extract_page(page_url, name)
                
                if page_props:
                    properties.extend(page_props)
                    logger.info(f"      ✅ {len(page_props)} imóveis extraídos")
                else:
                    logger.info(f"      ⚠️ Nenhum imóvel - pode ser última página")
                    # Se duas páginas consecutivas sem resultados, parar
                    if page_num > 1:
                        break
                
                await asyncio.sleep(2)  # Rate limiting
                
            except Exception as e:
                logger.error(f"      ❌ Erro na página {page_num}: {e}")
                continue
        
        return properties
    
    async def extract_infinite_scroll(self, url: str, name: str) -> List[Dict]:
        """Extrai de sites com scroll infinito / botão ver mais."""
        properties = []
        
        try:
            await self.page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)
            
            max_clicks = 50  # Limite de segurança
            click_count = 0
            last_count = 0
            
            while click_count < max_clicks:
                # Procurar botão "Ver Mais"
                button_selectors = [
                    'button:has-text("Ver Mais")',
                    'button:has-text("Carregar Mais")',
                    'button:has-text("Mostrar Mais")',
                    'a:has-text("Ver Mais")',
                    '.load-more',
                    '.ver-mais',
                    '[data-action="load-more"]',
                ]
                
                clicked = False
                for selector in button_selectors:
                    try:
                        button = await self.page.query_selector(selector)
                        if button and await button.is_visible():
                            await button.click()
                            clicked = True
                            click_count += 1
                            logger.info(f"   🔄 Clicou 'Ver Mais' ({click_count}x)")
                            await asyncio.sleep(2)
                            break
                    except:
                        continue
                
                if not clicked:
                    logger.info(f"   ✅ Botão não encontrado - todos os itens carregados")
                    break
                
                # Verificar se carregou novos itens
                current_count = await self._count_items()
                if current_count == last_count:
                    logger.info(f"   ✅ Nenhum item novo - fim do scroll")
                    break
                last_count = current_count
            
            # Extrair todos os itens carregados
            page_props = await self._extract_page(url, name)
            if page_props:
                properties.extend(page_props)
            
        except Exception as e:
            logger.error(f"   ❌ Erro no scroll infinito: {e}")
        
        return properties
    
    async def extract_single_page(self, url: str, name: str) -> List[Dict]:
        """Extrai de página única."""
        return await self._extract_page(url, name) or []
    
    async def _extract_page(self, url: str, name: str) -> List[Dict]:
        """Extrai imóveis de uma única página usando LLMEnhancedScraper."""
        try:
            # Usar o scraper existente
            properties = self.scraper.scrape_url_sync(url, name.lower().replace(' ', '_'))
            return properties
        except Exception as e:
            logger.error(f"Erro na extração: {e}")
            return []
    
    async def _count_items(self) -> int:
        """Conta itens visíveis."""
        selectors = ['a[href*="/imovel/"]', 'a[href*="/lote/"]', '.property-card', '.imovel-card']
        max_count = 0
        for selector in selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                max_count = max(max_count, len(elements))
            except:
                pass
        return max_count
    
    async def process_auctioneer(self, mapping: Dict) -> List[Dict]:
        """Processa um leiloeiro baseado no mapeamento."""
        name = mapping.get('name', '')
        url = mapping.get('url', '')
        ptype = mapping.get('pagination_type', 'SINGLE_PAGE')
        total_pages = mapping.get('total_pages')
        
        logger.info(f"\n🏢 {name} ({ptype})")
        
        if ptype == 'NUMERIC':
            return await self.extract_numeric_pagination(url, name, total_pages)
        elif ptype == 'INFINITE_SCROLL':
            return await self.extract_infinite_scroll(url, name)
        else:
            return await self.extract_single_page(url, name)
    
    async def process_all(self, mappings: List[Dict]) -> Dict:
        """Processa todos os leiloeiros."""
        await self.setup_browser()
        
        results = {
            'total_auctioneers': len(mappings),
            'total_properties': 0,
            'by_auctioneer': {},
            'timestamp': datetime.now().isoformat()
        }
        
        for i, mapping in enumerate(mappings, 1):
            name = mapping.get('name', '')
            logger.info(f"\n[{i}/{len(mappings)}] ═══════════════════════════════════")
            
            try:
                properties = await self.process_auctioneer(mapping)
                results['by_auctioneer'][name] = {
                    'count': len(properties),
                    'properties': properties
                }
                results['total_properties'] += len(properties)
                self.all_properties.extend(properties)
                
                logger.info(f"   📊 Total parcial: {results['total_properties']} imóveis")
                
            except Exception as e:
                logger.error(f"   ❌ Erro: {e}")
                results['by_auctioneer'][name] = {'count': 0, 'error': str(e)}
            
            # Checkpoint a cada 10 leiloeiros
            if i % 10 == 0:
                self._save_checkpoint(results, i)
            
            await asyncio.sleep(3)
        
        await self.close_browser()
        self._save_final(results)
        
        return results
    
    def _save_checkpoint(self, results: Dict, count: int):
        """Salva checkpoint."""
        file = OUTPUT_DIR / f"checkpoint_{count}.json"
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Checkpoint salvo: {file}")
    
    def _save_final(self, results: Dict):
        """Salva resultado final."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON completo
        json_file = OUTPUT_DIR / f"extracao_completa_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Apenas propriedades
        props_file = OUTPUT_DIR / f"propriedades_{timestamp}.json"
        with open(props_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_properties, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n✅ Extração concluída!")
        logger.info(f"   Total: {results['total_properties']} imóveis")
        logger.info(f"   Arquivo: {json_file}")


async def main():
    """Função principal."""
    
    # Carregar mapeamento
    mapping_dir = Path("logs/mapeamento_paginacao")
    mapping_files = list(mapping_dir.glob("mapeamento_completo_*.json"))
    
    if not mapping_files:
        logger.error("❌ Nenhum arquivo de mapeamento encontrado!")
        logger.error("   Execute primeiro: python scripts/mapear_paginacao_completo.py")
        return
    
    # Usar o mais recente
    mapping_file = max(mapping_files, key=lambda x: x.stat().st_mtime)
    logger.info(f"📂 Usando mapeamento: {mapping_file}")
    
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mappings = json.load(f)
    
    # Converter para lista
    mapping_list = [
        {**data, 'name': name}
        for name, data in mappings.items()
    ]
    
    # Priorizar por tipo (NUMERIC primeiro, depois INFINITE_SCROLL)
    priority = {'NUMERIC': 0, 'INFINITE_SCROLL': 1, 'SINGLE_PAGE': 2, 'TABS_FILTER': 3, 'UNKNOWN': 4}
    mapping_list.sort(key=lambda x: priority.get(x.get('pagination_type', 'UNKNOWN'), 5))
    
    logger.info(f"📊 Total de leiloeiros para extrair: {len(mapping_list)}")
    
    # Executar extração
    extractor = SmartExtractor()
    results = await extractor.process_all(mapping_list)
    
    # Resumo final
    logger.info("\n" + "="*60)
    logger.info("🎉 EXTRAÇÃO COMPLETA!")
    logger.info(f"   Total: {results['total_properties']} imóveis")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔧 ETAPA 4: EXECUTAR EXTRAÇÃO COMPLETA

```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
python scripts/extrair_com_paginacao.py
```

**Tempo estimado**: 3-4 horas

---

## 🔧 ETAPA 5: SALVAR NO BANCO DE DADOS

```bash
# Após extração, importar para o Supabase
python scripts/importar_propriedades.py logs/extracao_completa/propriedades_*.json
```

---

## 🔧 ETAPA 6: COMMIT E RELATÓRIO FINAL

```bash
cd C:\LeiloHub\leilao-aggregator-git

# Adicionar arquivos
git add leilao-backend/scripts/mapear_paginacao_completo.py
git add leilao-backend/scripts/extrair_com_paginacao.py
git add leilao-backend/logs/

# Commit
git commit -m "feat: FASE 1 - Mapeamento completo de paginação e extração inteligente

- Mapeado tipo de paginação de 128 leiloeiros
- Implementado extrator com suporte a:
  - Paginação numérica
  - Scroll infinito
  - Página única
- Extraídos X imóveis de Y leiloeiros"

# Push
git push origin main
```

---

## ✅ CRITÉRIOS DE SUCESSO

1. ✅ **Mapeamento completo**: 128 leiloeiros classificados por tipo de paginação
2. ✅ **Relatório preciso**: Números reais de itens/páginas (não estimativas falsas)
3. ✅ **Extração funcional**: Pelo menos 50.000 imóveis extraídos
4. ✅ **Documentação**: Relatórios salvos em `logs/`

---

## ⚠️ TROUBLESHOOTING

### Problema: Timeout em sites lentos
**Solução**: Aumentar `timeout=90000` e `wait_until='domcontentloaded'`

### Problema: Bot detectado
**Solução**: Adicionar mais headers e delays entre requisições

### Problema: Número errado de páginas
**Solução**: Sempre buscar texto "Página X de Y" ou "X de Y itens" - não confiar em números aleatórios na página

### Problema: Scroll infinito não carrega
**Solução**: Verificar se o botão tem outro texto (ex: "Carregar mais", "Load more")

---

## 📊 EXPECTATIVA DE RESULTADO

| Tipo | Leiloeiros | Imóveis Estimados |
|------|------------|-------------------|
| NUMERIC | ~40-50 | 30.000-40.000 |
| INFINITE_SCROLL | ~20-30 | 5.000-10.000 |
| SINGLE_PAGE | ~40-50 | 2.000-5.000 |
| TABS_FILTER | ~10-20 | 500-1.000 |
| **TOTAL** | **128** | **40.000-60.000** |

---

**FIM DA TAREFA**
