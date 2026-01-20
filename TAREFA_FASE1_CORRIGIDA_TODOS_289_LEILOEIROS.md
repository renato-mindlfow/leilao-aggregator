# 🎯 TAREFA FASE 1 CORRIGIDA: MAPEAMENTO COMPLETO DE TODOS OS 289 LEILOEIROS

**Objetivo**: Mapear o tipo de paginação de TODOS os 289 leiloeiros, sem filtrar por property_count.

**Problema da versão anterior**: Filtrou 229 leiloeiros porque tinham `property_count=0`, mas isso não significa que não têm imóveis - apenas que nunca foram scrapeados corretamente.

**Tempo Estimado**: 4-6 horas (execução autônoma)

---

## ⚠️ INSTRUÇÕES CRÍTICAS

1. **NÃO FILTRAR POR PROPERTY_COUNT** - Mapear TODOS os 289 leiloeiros
2. **VALIDAR CONTRA CASOS CONHECIDOS** - Ver seção de validação abaixo
3. **DOCUMENTAR SITES OFFLINE** - Não excluir, apenas marcar como OFFLINE
4. **SALVAR CHECKPOINT A CADA 30 LEILOEIROS**

---

## 🔍 CASOS CONHECIDOS PARA VALIDAÇÃO

Use estes casos para verificar se a detecção automática está funcionando:

| Leiloeiro | URL | Tipo Esperado | Páginas/Itens | Como Identificar |
|-----------|-----|---------------|---------------|------------------|
| **Megaleiloes** | megaleiloes.com.br/imoveis | NUMERIC | 17 páginas, 798 itens | Texto "Página X de 17" |
| **Frazaoleiloes** | frazaoleiloes.com.br/sale/searchLot?&categoria=Imóveis | INFINITE_SCROLL | Botão "Ver Mais" | Botão azul "Ver Mais" no final |
| **Gustavo Reis** | gustavoreisleiloes.com.br/?tipo=todos | SINGLE_PAGE | ~7 itens | Abas de filtro, sem paginação |
| **Portal Zuk** | portalzuk.com.br/leilao-de-imoveis | NUMERIC | Múltiplas páginas | Links de página no rodapé |
| **Lance Judicial** | lancejudicial.com.br | NUMERIC | ~5 páginas | Paginação numérica |

**Se a detecção automática divergir destes casos, há um bug no script!**

---

## 🔧 ETAPA 1: CRIAR SCRIPT DE MAPEAMENTO CORRIGIDO

**Arquivo**: `leilao-backend/scripts/mapear_todos_leiloeiros.py`

```python
#!/usr/bin/env python3
"""
MAPEAMENTO COMPLETO DE TODOS OS 289 LEILOEIROS
Versão corrigida - NÃO filtra por property_count

Correções vs versão anterior:
1. Inclui TODOS os leiloeiros (não filtra por property_count)
2. Detecta INFINITE_SCROLL corretamente (botão "Ver Mais")
3. Extrai número REAL de páginas (busca texto "Página X de Y")
4. Valida contra casos conhecidos
"""

import asyncio
import json
import re
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/mapeamento_paginacao/mapeamento.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Diretórios
OUTPUT_DIR = Path("logs/mapeamento_paginacao_v2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


class PaginationType:
    """Tipos de paginação possíveis."""
    NUMERIC = "NUMERIC"                    # ?page=1, ?pagina=1, links numéricos
    INFINITE_SCROLL = "INFINITE_SCROLL"    # Botão "Ver Mais", "Carregar Mais"
    SINGLE_PAGE = "SINGLE_PAGE"            # Página única sem paginação
    TABS_FILTER = "TABS_FILTER"            # Abas de filtro (Todos, Judicial, etc)
    API_BASED = "API_BASED"                # Carrega via API JSON
    OFFLINE = "OFFLINE"                    # Site offline ou erro DNS
    BLOCKED = "BLOCKED"                    # Bloqueado por CAPTCHA/WAF
    UNKNOWN = "UNKNOWN"                    # Não identificado


# CASOS CONHECIDOS PARA VALIDAÇÃO
KNOWN_CASES = {
    'megaleiloes': {
        'type': PaginationType.NUMERIC,
        'expected_pages': 17,
        'expected_items': 798,
        'url_contains': 'megaleiloes.com.br'
    },
    'frazaoleiloes': {
        'type': PaginationType.INFINITE_SCROLL,
        'expected_pages': None,
        'expected_items': None,
        'url_contains': 'frazaoleiloes.com.br'
    },
    'gustavoreisleiloes': {
        'type': PaginationType.SINGLE_PAGE,
        'expected_pages': 1,
        'expected_items': 7,
        'url_contains': 'gustavoreisleiloes.com.br'
    },
    'portalzuk': {
        'type': PaginationType.NUMERIC,
        'expected_pages': None,
        'expected_items': None,
        'url_contains': 'portalzuk.com.br'
    },
    'lancejudicial': {
        'type': PaginationType.NUMERIC,
        'expected_pages': 5,
        'expected_items': None,
        'url_contains': 'lancejudicial.com.br'
    }
}


class PaginationMapper:
    """Mapeia o tipo de paginação de cada leiloeiro."""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.validation_errors: List[str] = []
        
    async def setup_browser(self):
        """Configura o browser com stealth mode."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
            ]
        )
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
        )
        self.page = await context.new_page()
        
        # Stealth scripts
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            delete navigator.__proto__.webdriver;
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
        """)
        
    async def close_browser(self):
        """Fecha o browser."""
        if self.browser:
            await self.browser.close()

    def _get_imoveis_url(self, base_url: str, name: str) -> str:
        """
        Constrói a URL da página de imóveis baseado no padrão do site.
        """
        # Remover trailing slash
        base_url = base_url.rstrip('/')
        
        # URLs conhecidas
        known_urls = {
            'megaleiloes': 'https://www.megaleiloes.com.br/imoveis',
            'portalzuk': 'https://www.portalzuk.com.br/leilao-de-imoveis',
            'frazaoleiloes': 'https://www.frazaoleiloes.com.br/sale/searchLot?&categoria=Imóveis&pesquisaSimples=false',
            'gustavoreisleiloes': 'https://www.gustavoreisleiloes.com.br/?tipo=todos',
            'sold': 'https://www.sold.com.br/leiloes/imoveis',
            'superbid': 'https://www.superbid.net/leiloes/imoveis',
            'vivaleiloes': 'https://www.vivaleiloes.com.br/leiloes/imoveis',
            'lancejudicial': 'https://www.lancejudicial.com.br/leiloes/imoveis',
        }
        
        name_lower = name.lower().replace(' ', '').replace('-', '').replace('_', '')
        
        if name_lower in known_urls:
            return known_urls[name_lower]
        
        # Tentar padrões comuns
        common_paths = [
            '/imoveis',
            '/leiloes/imoveis', 
            '/leilao-de-imoveis',
            '/busca?categoria=imoveis',
            '/?tipo=imoveis',
        ]
        
        # Por enquanto, retornar URL base + /imoveis como fallback
        # O script tentará a URL base primeiro
        return base_url

    async def detect_pagination_type(self, url: str, name: str) -> Dict:
        """
        Detecta o tipo de paginação de um leiloeiro.
        """
        result = {
            'name': name,
            'url': url,
            'pagination_type': PaginationType.UNKNOWN,
            'total_items': None,
            'total_pages': None,
            'items_per_page': None,
            'url_pattern': None,
            'selector_info': None,
            'notes': '',
            'screenshot': None,
            'validation_status': 'not_validated',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            logger.info(f"🔍 Analisando: {name}")
            logger.info(f"   URL: {url}")
            
            # Construir URL de imóveis
            imoveis_url = self._get_imoveis_url(url, name)
            if imoveis_url != url:
                logger.info(f"   URL imóveis: {imoveis_url}")
            
            # Tentar navegar
            try:
                response = await self.page.goto(
                    imoveis_url, 
                    wait_until='domcontentloaded',  # Mais rápido que networkidle
                    timeout=45000
                )
                
                if response and response.status >= 400:
                    # Tentar URL base se a de imóveis falhou
                    if imoveis_url != url:
                        logger.info(f"   ⚠️ Status {response.status}, tentando URL base...")
                        response = await self.page.goto(url, wait_until='domcontentloaded', timeout=45000)
                
                if response and response.status >= 400:
                    result['pagination_type'] = PaginationType.OFFLINE
                    result['notes'] = f'HTTP {response.status}'
                    return result
                    
            except PlaywrightTimeout:
                result['pagination_type'] = PaginationType.OFFLINE
                result['notes'] = 'Timeout ao carregar página'
                return result
            except Exception as e:
                if 'net::ERR_NAME_NOT_RESOLVED' in str(e):
                    result['pagination_type'] = PaginationType.OFFLINE
                    result['notes'] = 'DNS não resolvido - site offline'
                    return result
                raise
            
            # Aguardar JavaScript carregar
            await asyncio.sleep(3)
            
            # Fazer scroll para carregar lazy content
            await self._scroll_page()
            
            # Capturar screenshot
            screenshot_path = SCREENSHOTS_DIR / f"{self._sanitize_filename(name)}.png"
            try:
                await self.page.screenshot(path=str(screenshot_path), full_page=False)
                result['screenshot'] = str(screenshot_path)
            except:
                pass
            
            # Obter conteúdo da página
            page_text = await self.page.evaluate("() => document.body.innerText || ''")
            page_html = await self.page.content()
            
            # Verificar bloqueios
            if await self._check_blocked(page_text, page_html):
                result['pagination_type'] = PaginationType.BLOCKED
                result['notes'] = 'Bloqueado por CAPTCHA ou WAF'
                return result
            
            # DETECÇÃO 1: Paginação Numérica (PRIORIDADE)
            numeric_result = await self._detect_numeric_pagination(page_text, page_html)
            if numeric_result['detected']:
                result['pagination_type'] = PaginationType.NUMERIC
                result['total_items'] = numeric_result.get('total_items')
                result['total_pages'] = numeric_result.get('total_pages')
                result['items_per_page'] = numeric_result.get('items_per_page')
                result['url_pattern'] = numeric_result.get('url_pattern')
                result['notes'] = numeric_result.get('notes', '')
                
                # Validar contra casos conhecidos
                await self._validate_known_case(name, result)
                return result
            
            # DETECÇÃO 2: Scroll Infinito / Botão Ver Mais
            infinite_result = await self._detect_infinite_scroll(page_html)
            if infinite_result['detected']:
                result['pagination_type'] = PaginationType.INFINITE_SCROLL
                result['selector_info'] = infinite_result.get('button_selector')
                result['notes'] = infinite_result.get('notes', '')
                result['total_items'] = await self._count_visible_items()
                
                await self._validate_known_case(name, result)
                return result
            
            # DETECÇÃO 3: Abas/Filtros
            tabs_result = await self._detect_tabs_filter(page_html, page_text)
            if tabs_result['detected']:
                result['pagination_type'] = PaginationType.TABS_FILTER
                result['notes'] = tabs_result.get('notes', '')
                result['total_items'] = await self._count_visible_items()
                
                await self._validate_known_case(name, result)
                return result
            
            # DETECÇÃO 4: Página Única (fallback)
            items = await self._count_visible_items()
            result['pagination_type'] = PaginationType.SINGLE_PAGE
            result['total_items'] = items
            result['total_pages'] = 1
            result['notes'] = f'Página única com {items or "?"} itens visíveis'
            
            await self._validate_known_case(name, result)
            
        except Exception as e:
            logger.error(f"❌ Erro ao analisar {name}: {e}")
            result['pagination_type'] = PaginationType.UNKNOWN
            result['notes'] = f'Erro: {str(e)[:100]}'
            
        return result
    
    async def _scroll_page(self):
        """Faz scroll na página para carregar conteúdo lazy."""
        try:
            await self.page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 500;
                        const maxScroll = 8000;
                        const timer = setInterval(() => {
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if (totalHeight >= maxScroll) {
                                clearInterval(timer);
                                window.scrollTo(0, 0);
                                resolve();
                            }
                        }, 150);
                    });
                }
            """)
            await asyncio.sleep(2)
        except:
            pass
    
    async def _check_blocked(self, page_text: str, page_html: str) -> bool:
        """Verifica se está bloqueado por CAPTCHA ou WAF."""
        blocked_indicators = [
            'captcha',
            'cloudflare',
            'access denied',
            'blocked',
            'verificação de segurança',
            'prove que você é humano',
            'ray id',
        ]
        
        text_lower = page_text.lower()
        for indicator in blocked_indicators:
            if indicator in text_lower and len(page_text) < 5000:
                return True
        
        return False
    
    async def _detect_numeric_pagination(self, page_text: str, page_html: str) -> Dict:
        """Detecta paginação numérica com precisão."""
        result = {'detected': False}
        
        # PADRÃO 1: "Página X de Y" (mais confiável)
        patterns_page = [
            r'[Pp]ágina\s+(\d+)\s+de\s+(\d+)',
            r'[Pp]age\s+(\d+)\s+of\s+(\d+)',
            r'(\d+)\s*/\s*(\d+)\s*páginas?',
        ]
        
        for pattern in patterns_page:
            match = re.search(pattern, page_text)
            if match:
                current_page = int(match.group(1))
                total_pages = int(match.group(2))
                if total_pages > 1 and total_pages < 10000:  # Sanidade
                    result['detected'] = True
                    result['total_pages'] = total_pages
                    result['notes'] = f'Detectado: "Página {current_page} de {total_pages}"'
                    break
        
        # PADRÃO 2: "Exibindo X-Y de Z itens"
        if not result['detected']:
            patterns_items = [
                r'[Ee]xibindo\s+(\d+)\s*[-–]\s*(\d+)\s+de\s+(\d+)',
                r'(\d+)\s*[-–]\s*(\d+)\s+de\s+(\d+)\s+(?:itens?|imóveis?|resultados?)',
                r'[Mm]ostrando\s+(\d+)\s*[-–]\s*(\d+)\s+de\s+(\d+)',
            ]
            
            for pattern in patterns_items:
                match = re.search(pattern, page_text)
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2))
                    total = int(match.group(3))
                    if total > 0 and total < 100000:  # Sanidade
                        items_per_page = end - start + 1
                        total_pages = (total + items_per_page - 1) // items_per_page
                        result['detected'] = True
                        result['total_items'] = total
                        result['total_pages'] = total_pages
                        result['items_per_page'] = items_per_page
                        result['notes'] = f'Detectado: "{start}-{end} de {total} itens" ({total_pages} páginas)'
                        break
        
        # PADRÃO 3: Links de navegação no HTML
        if not result['detected']:
            # Procurar links com números de página
            page_links = re.findall(
                r'href=["\'][^"\']*[?&](?:page|pagina|p)=(\d+)[^"\']*["\']',
                page_html,
                re.IGNORECASE
            )
            
            if page_links:
                max_page = max(int(p) for p in page_links)
                if max_page > 1:
                    result['detected'] = True
                    result['total_pages'] = max_page
                    result['url_pattern'] = '?pagina={page}'
                    result['notes'] = f'Detectado via links: até página {max_page}'
        
        # PADRÃO 4: Botões de navegação (Início, Fim, <, >)
        if not result['detected']:
            nav_patterns = [
                r'<a[^>]*>\s*(Fim|Última|Last|»|>>)\s*</a>',
                r'<button[^>]*>\s*(Fim|Última|Last|»|>>)\s*</button>',
            ]
            
            for pattern in nav_patterns:
                if re.search(pattern, page_html, re.IGNORECASE):
                    result['detected'] = True
                    result['notes'] = 'Detectado: botões de navegação (total não identificado)'
                    break
        
        return result
    
    async def _detect_infinite_scroll(self, page_html: str) -> Dict:
        """Detecta scroll infinito / botão ver mais."""
        result = {'detected': False}
        
        # Padrões de botões
        button_patterns = [
            (r'>\s*Ver [Mm]ais\s*<', 'Ver Mais'),
            (r'>\s*Carregar [Mm]ais\s*<', 'Carregar Mais'),
            (r'>\s*Mostrar [Mm]ais\s*<', 'Mostrar Mais'),
            (r'>\s*Load [Mm]ore\s*<', 'Load More'),
            (r'>\s*Ver [Tt]odos\s*<', 'Ver Todos'),
            (r'class=["\'][^"\']*load-?more[^"\']*["\']', 'classe load-more'),
            (r'class=["\'][^"\']*ver-?mais[^"\']*["\']', 'classe ver-mais'),
            (r'class=["\'][^"\']*show-?more[^"\']*["\']', 'classe show-more'),
            (r'id=["\'][^"\']*load-?more[^"\']*["\']', 'id load-more'),
            (r'data-action=["\'][^"\']*load[^"\']*["\']', 'data-action load'),
        ]
        
        for pattern, description in button_patterns:
            if re.search(pattern, page_html, re.IGNORECASE):
                result['detected'] = True
                result['button_selector'] = description
                result['notes'] = f'Detectado: botão "{description}"'
                break
        
        # Verificar também por scroll infinito via JavaScript
        if not result['detected']:
            infinite_indicators = [
                'infinite-scroll',
                'infiniteScroll',
                'endless-scroll',
                'lazy-load',
            ]
            
            for indicator in infinite_indicators:
                if indicator.lower() in page_html.lower():
                    result['detected'] = True
                    result['notes'] = f'Detectado: {indicator} no código'
                    break
        
        return result
    
    async def _detect_tabs_filter(self, page_html: str, page_text: str) -> Dict:
        """Detecta sistema de abas/filtros."""
        result = {'detected': False}
        
        # Palavras-chave de abas de leilão
        tab_keywords = [
            'Todos', 'Leilão', 'Leilões', 'Judicial', 'Extrajudicial',
            'Venda Direta', 'Encerrados', 'Cancelados', 'Suspensos',
            'Em Andamento', 'Finalizados', 'Ativos'
        ]
        
        found_tabs = []
        for keyword in tab_keywords:
            # Procurar como link ou botão
            if re.search(rf'>\s*{keyword}\s*<', page_html, re.IGNORECASE):
                found_tabs.append(keyword)
        
        # Se encontrar 3+ abas típicas, é sistema de filtro
        if len(found_tabs) >= 3:
            result['detected'] = True
            result['tabs'] = found_tabs
            result['notes'] = f'Detectado: abas ({", ".join(found_tabs[:5])})'
        
        return result
    
    async def _count_visible_items(self) -> Optional[int]:
        """Conta itens visíveis na página."""
        try:
            # Seletores comuns para cards de imóveis
            selectors = [
                'a[href*="/imovel/"]',
                'a[href*="/imoveis/"]',
                'a[href*="/lote/"]',
                'a[href*="/lotes/"]',
                'a[href*="/item/"]',
                'a[href*="/detalhes/"]',
                '.property-card',
                '.imovel-card',
                '.lote-card',
                '.card-imovel',
                '.card-lote',
                '.auction-item',
                '.leilao-item',
                '[class*="property-card"]',
                '[class*="imovel"]',
                '[class*="lote-card"]',
            ]
            
            max_count = 0
            for selector in selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    count = len(elements)
                    if count > max_count:
                        max_count = count
                except:
                    pass
            
            return max_count if max_count > 0 else None
        except:
            return None
    
    async def _validate_known_case(self, name: str, result: Dict):
        """Valida resultado contra casos conhecidos."""
        name_lower = name.lower().replace(' ', '').replace('-', '').replace('_', '')
        
        for known_name, expected in KNOWN_CASES.items():
            if known_name in name_lower or expected['url_contains'] in result.get('url', ''):
                result['validation_status'] = 'validated'
                
                # Verificar tipo
                if result['pagination_type'] != expected['type']:
                    error = f"⚠️ VALIDAÇÃO FALHOU: {name} - Esperado {expected['type']}, obtido {result['pagination_type']}"
                    logger.warning(error)
                    self.validation_errors.append(error)
                    result['validation_status'] = 'FAILED'
                    result['validation_error'] = error
                else:
                    logger.info(f"   ✅ Validação OK: {name} = {expected['type']}")
                
                # Verificar páginas se esperado
                if expected['expected_pages'] and result.get('total_pages'):
                    diff = abs(result['total_pages'] - expected['expected_pages'])
                    if diff > 2:  # Tolerância de 2 páginas
                        warning = f"⚠️ {name}: Esperado ~{expected['expected_pages']} páginas, obtido {result['total_pages']}"
                        logger.warning(warning)
                        result['validation_warning'] = warning
                
                break
    
    def _sanitize_filename(self, name: str) -> str:
        """Remove caracteres inválidos do nome do arquivo."""
        return re.sub(r'[<>:"/\\|?*]', '_', name)[:50]
    
    async def process_all_auctioneers(self, auctioneers: List[Dict]) -> Dict:
        """
        Processa TODOS os leiloeiros.
        """
        await self.setup_browser()
        
        total = len(auctioneers)
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 INICIANDO MAPEAMENTO DE {total} LEILOEIROS")
        logger.info(f"{'='*60}\n")
        
        for i, auctioneer in enumerate(auctioneers, 1):
            name = auctioneer.get('name', 'Unknown')
            url = auctioneer.get('website', auctioneer.get('url', ''))
            
            logger.info(f"\n[{i}/{total}] {'═'*50}")
            
            result = await self.detect_pagination_type(url, name)
            self.results[name] = result
            
            # Log resumido
            ptype = result['pagination_type']
            items = result.get('total_items', '?')
            pages = result.get('total_pages', '?')
            logger.info(f"   → Tipo: {ptype} | Itens: {items} | Páginas: {pages}")
            
            # Checkpoint a cada 30 leiloeiros
            if i % 30 == 0:
                await self._save_checkpoint(i)
                logger.info(f"\n💾 Checkpoint salvo ({i}/{total})\n")
            
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
            json.dump({
                'count': count,
                'timestamp': datetime.now().isoformat(),
                'results': self.results
            }, f, ensure_ascii=False, indent=2)
    
    async def _save_final_report(self):
        """Salva relatório final detalhado."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. JSON completo
        json_file = OUTPUT_DIR / f"mapeamento_todos_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        # 2. Agrupar por tipo
        by_type = {}
        for name, data in self.results.items():
            ptype = data.get('pagination_type', 'UNKNOWN')
            if ptype not in by_type:
                by_type[ptype] = []
            by_type[ptype].append(data)
        
        # 3. Calcular estatísticas
        total_items = sum(r.get('total_items', 0) or 0 for r in self.results.values())
        total_pages = sum(r.get('total_pages', 0) or 0 for r in self.results.values())
        
        # 4. Gerar Markdown
        md_file = OUTPUT_DIR / f"RELATORIO_MAPEAMENTO_TODOS_{timestamp}.md"
        
        md_content = f"""# 📊 RELATÓRIO DE MAPEAMENTO - TODOS OS LEILOEIROS

**Data**: {datetime.now().strftime('%d/%m/%Y %H:%M')}
**Total de Leiloeiros**: {len(self.results)}
**Total de Itens Identificados**: {total_items:,}
**Total de Páginas Identificadas**: {total_pages:,}

---

## 📈 RESUMO POR TIPO DE PAGINAÇÃO

| Tipo | Quantidade | % | Itens | Páginas |
|------|------------|---|-------|---------|
"""
        
        for ptype in [PaginationType.NUMERIC, PaginationType.INFINITE_SCROLL, 
                      PaginationType.SINGLE_PAGE, PaginationType.TABS_FILTER,
                      PaginationType.OFFLINE, PaginationType.BLOCKED, PaginationType.UNKNOWN]:
            items_list = by_type.get(ptype, [])
            count = len(items_list)
            pct = count / len(self.results) * 100 if self.results else 0
            type_items = sum(r.get('total_items', 0) or 0 for r in items_list)
            type_pages = sum(r.get('total_pages', 0) or 0 for r in items_list)
            md_content += f"| {ptype} | {count} | {pct:.1f}% | {type_items:,} | {type_pages} |\n"
        
        # 5. Erros de validação
        if self.validation_errors:
            md_content += f"\n---\n\n## ⚠️ ERROS DE VALIDAÇÃO\n\n"
            for error in self.validation_errors:
                md_content += f"- {error}\n"
        
        # 6. Detalhar cada tipo
        md_content += "\n---\n\n"
        
        for ptype in [PaginationType.NUMERIC, PaginationType.INFINITE_SCROLL, 
                      PaginationType.SINGLE_PAGE, PaginationType.TABS_FILTER]:
            items_list = by_type.get(ptype, [])
            if not items_list:
                continue
                
            md_content += f"## {ptype} ({len(items_list)} leiloeiros)\n\n"
            md_content += "| Leiloeiro | URL | Itens | Páginas | Notas |\n"
            md_content += "|-----------|-----|-------|---------|-------|\n"
            
            # Ordenar por itens (decrescente)
            sorted_items = sorted(items_list, key=lambda x: -(x.get('total_items') or 0))
            
            for item in sorted_items:
                name = item.get('name', 'Unknown')
                url = item.get('url', '')[:40]
                items = item.get('total_items', '-')
                pages = item.get('total_pages', '-')
                notes = item.get('notes', '')[:40]
                md_content += f"| {name} | {url}... | {items} | {pages} | {notes} |\n"
            
            md_content += "\n"
        
        # 7. Sites Offline/Bloqueados
        offline = by_type.get(PaginationType.OFFLINE, []) + by_type.get(PaginationType.BLOCKED, [])
        if offline:
            md_content += f"## 🚫 OFFLINE/BLOQUEADOS ({len(offline)} leiloeiros)\n\n"
            md_content += "| Leiloeiro | URL | Motivo |\n"
            md_content += "|-----------|-----|--------|\n"
            for item in offline:
                name = item.get('name', 'Unknown')
                url = item.get('url', '')[:50]
                notes = item.get('notes', '-')
                md_content += f"| {name} | {url} | {notes} |\n"
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # 8. Resumo para console
        logger.info(f"\n{'='*60}")
        logger.info("🎉 MAPEAMENTO CONCLUÍDO!")
        logger.info(f"{'='*60}")
        logger.info(f"\n📊 Resumo:")
        for ptype, items_list in sorted(by_type.items(), key=lambda x: -len(x[1])):
            logger.info(f"   {ptype}: {len(items_list)}")
        logger.info(f"\n📁 Arquivos salvos:")
        logger.info(f"   {json_file}")
        logger.info(f"   {md_file}")
        
        if self.validation_errors:
            logger.warning(f"\n⚠️ {len(self.validation_errors)} erros de validação!")


async def main():
    """Função principal."""
    
    # Criar diretório de logs se não existir
    Path("logs/mapeamento_paginacao_v2").mkdir(parents=True, exist_ok=True)
    
    # Carregar TODOS os leiloeiros do CSV (sem filtro!)
    csv_paths = [
        Path("LISTA_MESTRE_LEILOEIROS.csv"),
        Path("../LISTA_MESTRE_LEILOEIROS.csv"),
        Path("docs/LISTA_MESTRE_LEILOEIROS.csv"),
        Path("leilao-backend/LISTA_MESTRE_LEILOEIROS.csv"),
    ]
    
    csv_path = None
    for p in csv_paths:
        if p.exists():
            csv_path = p
            break
    
    if not csv_path:
        logger.error("❌ Arquivo LISTA_MESTRE_LEILOEIROS.csv não encontrado!")
        logger.error("   Procurado em: " + ", ".join(str(p) for p in csv_paths))
        return
    
    logger.info(f"📂 Carregando leiloeiros de: {csv_path}")
    
    auctioneers = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('name', '')
            website = row.get('website', '')
            
            if name and website:
                auctioneers.append({
                    'name': name,
                    'website': website,
                    'property_count': int(row.get('property_count', 0) or 0),
                    'scrape_status': row.get('scrape_status', ''),
                })
    
    logger.info(f"📋 Total de leiloeiros carregados: {len(auctioneers)}")
    logger.info(f"   (SEM FILTRO - processando TODOS)")
    
    # Executar mapeamento
    mapper = PaginationMapper()
    results = await mapper.process_all_auctioneers(auctioneers)
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔧 ETAPA 2: EXECUTAR O MAPEAMENTO

```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend

# Criar diretório se não existir
mkdir -p logs/mapeamento_paginacao_v2

# Executar mapeamento completo
python scripts/mapear_todos_leiloeiros.py
```

**Tempo estimado**: 4-6 horas para 289 leiloeiros (2 segundos por site + processamento)

---

## 🔧 ETAPA 3: VALIDAR RESULTADOS

Após a execução, verificar:

```bash
# Ver relatório
type logs\mapeamento_paginacao_v2\RELATORIO_MAPEAMENTO_TODOS_*.md

# Verificar casos conhecidos
grep -i "megaleiloes\|frazao\|gustavo" logs/mapeamento_paginacao_v2/RELATORIO_*.md
```

**Validações esperadas**:
- ✅ Megaleiloes = NUMERIC, ~17 páginas
- ✅ Frazaoleiloes = INFINITE_SCROLL
- ✅ Gustavoreisleiloes = SINGLE_PAGE, ~7 itens

---

## 🔧 ETAPA 4: COMMIT

```bash
cd C:\LeiloHub\leilao-aggregator-git

# Remover lock se existir
del .git\index.lock 2>nul

# Adicionar arquivos
git add leilao-backend/scripts/mapear_todos_leiloeiros.py
git add leilao-backend/logs/mapeamento_paginacao_v2/

# Commit
git commit -m "feat: FASE 1 v2 - Mapeamento de TODOS os 289 leiloeiros

Correções vs versão anterior:
- Removido filtro por property_count (incluir TODOS)
- Melhorada detecção de INFINITE_SCROLL (botão Ver Mais)
- Adicionada validação contra casos conhecidos
- Melhorada extração de número real de páginas

Resultados:
- X leiloeiros mapeados
- X com paginação NUMERIC
- X com INFINITE_SCROLL  
- X com SINGLE_PAGE
- X offline/bloqueados"

# Push
git push origin main
```

---

## ✅ CRITÉRIOS DE SUCESSO

1. ✅ **289 leiloeiros processados** (não filtrar nenhum)
2. ✅ **Validação OK** para casos conhecidos:
   - Megaleiloes = NUMERIC
   - Frazaoleiloes = INFINITE_SCROLL
   - Gustavoreisleiloes = SINGLE_PAGE
3. ✅ **Relatório detalhado** com todos os tipos identificados
4. ✅ **Screenshots** de cada site para validação manual

---

## ⚠️ DIFERENÇAS DA VERSÃO ANTERIOR

| Aspecto | Versão Anterior | Esta Versão |
|---------|-----------------|-------------|
| Filtro | `property_count > 0` | **NENHUM** (todos) |
| Leiloeiros | 60 | **289** |
| Validação | Não tinha | **Casos conhecidos** |
| Detecção Ver Mais | Fraca | **Melhorada** |
| URLs de imóveis | Só base | **Conhecidas + fallback** |

---

## 📊 EXPECTATIVA DE RESULTADO

| Tipo | Esperado | Notas |
|------|----------|-------|
| NUMERIC | 40-60 | Grandes leiloeiros |
| INFINITE_SCROLL | 20-40 | Frazão e similares |
| SINGLE_PAGE | 80-120 | Pequenos leiloeiros |
| TABS_FILTER | 10-20 | Gustavo Reis e similares |
| OFFLINE | 30-50 | DNS errors, sites fora |
| BLOCKED | 5-15 | CAPTCHA, Cloudflare |
| UNKNOWN | 10-30 | Estrutura não reconhecida |

**Total**: 289 leiloeiros mapeados

---

**FIM DA TAREFA**
