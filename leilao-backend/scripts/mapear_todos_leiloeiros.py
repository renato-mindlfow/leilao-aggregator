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
import sys
import codecs
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
import logging

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configuração de logging
log_dir = Path("logs/mapeamento_paginacao_v2")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'mapeamento.log', encoding='utf-8')
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

    def _get_imoveis_url(self, base_url: str, name: str) -> str:
        """
        Constrói a URL da página de imóveis baseado no padrão do site.
        """
        base_url = base_url.rstrip('/')
        
        # URLs conhecidas específicas
        known_urls = {
            'megaleiloes': 'https://www.megaleiloes.com.br/imoveis',
            'portalzuk': 'https://www.portalzuk.com.br/leilao-de-imoveis',
            'frazaoleiloes': 'https://www.frazaoleiloes.com.br/sale/searchLot?&categoria=Im%C3%B3veis&pesquisaSimples=false',
            'gustavoreisleiloes': 'https://www.gustavoreisleiloes.com.br/?tipo=todos',
        }
        
        name_lower = name.lower().replace(' ', '').replace('-', '').replace('_', '')
        
        if name_lower in known_urls:
            return known_urls[name_lower]
        
        # Fallback: tentar /imoveis
        return f"{base_url}/imoveis"

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
            'notes': '',
            'screenshot': None,
            'validation_status': 'not_validated',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            logger.info(f"Analisando: {name}")
            
            # Construir URL de imóveis
            imoveis_url = self._get_imoveis_url(url, name)
            
            # Tentar navegar
            try:
                response = await self.page.goto(
                    imoveis_url, 
                    wait_until='domcontentloaded',
                    timeout=30000
                )
                
                if response and response.status >= 400:
                    result['pagination_type'] = PaginationType.OFFLINE
                    result['notes'] = f'HTTP {response.status}'
                    return result
                    
            except PlaywrightTimeout:
                result['pagination_type'] = PaginationType.OFFLINE
                result['notes'] = 'Timeout ao carregar página'
                return result
            except Exception as e:
                if 'ERR_NAME_NOT_RESOLVED' in str(e) or 'ERR_CONNECTION' in str(e):
                    result['pagination_type'] = PaginationType.OFFLINE
                    result['notes'] = 'Site offline'
                    return result
                raise
            
            # Aguardar JavaScript
            await asyncio.sleep(2)
            
            # Scroll
            await self._scroll_page()
            
            # Screenshot
            screenshot_path = SCREENSHOTS_DIR / f"{self._sanitize_filename(name)}.png"
            try:
                await self.page.screenshot(path=str(screenshot_path), full_page=False)
                result['screenshot'] = str(screenshot_path)
            except:
                pass
            
            # Obter conteúdo
            page_text = await self.page.evaluate("() => document.body.innerText || ''")
            page_html = await self.page.content()
            
            # Verificar bloqueios
            if await self._check_blocked(page_text, page_html):
                result['pagination_type'] = PaginationType.BLOCKED
                result['notes'] = 'Bloqueado por CAPTCHA/WAF'
                return result
            
            # DETECÇÃO 1: Paginação Numérica
            numeric_result = await self._detect_numeric_pagination(page_text, page_html)
            if numeric_result['detected']:
                result['pagination_type'] = PaginationType.NUMERIC
                result['total_items'] = numeric_result.get('total_items')
                result['total_pages'] = numeric_result.get('total_pages')
                result['notes'] = numeric_result.get('notes', '')
                await self._validate_known_case(name, result)
                return result
            
            # DETECÇÃO 2: Scroll Infinito
            infinite_result = await self._detect_infinite_scroll(page_html)
            if infinite_result['detected']:
                result['pagination_type'] = PaginationType.INFINITE_SCROLL
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
            
            # DETECÇÃO 4: Página Única
            items = await self._count_visible_items()
            result['pagination_type'] = PaginationType.SINGLE_PAGE
            result['total_items'] = items
            result['total_pages'] = 1
            result['notes'] = f'Página única com {items or "?"} itens'
            await self._validate_known_case(name, result)
            
        except Exception as e:
            logger.error(f"Erro ao analisar {name}: {e}")
            result['pagination_type'] = PaginationType.UNKNOWN
            result['notes'] = f'Erro: {str(e)[:100]}'
            
        return result
    
    async def _scroll_page(self):
        """Faz scroll na página."""
        try:
            await self.page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 500;
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
    
    async def _check_blocked(self, page_text: str, page_html: str) -> bool:
        """Verifica se está bloqueado."""
        blocked_indicators = [
            'captcha', 'cloudflare', 'access denied', 'blocked',
            'verificação de segurança', 'prove que você é humano',
        ]
        
        text_lower = page_text.lower()
        for indicator in blocked_indicators:
            if indicator in text_lower and len(page_text) < 5000:
                return True
        return False
    
    async def _detect_numeric_pagination(self, page_text: str, page_html: str) -> Dict:
        """Detecta paginação numérica."""
        result = {'detected': False}
        
        # Padrão 1: "Página X de Y"
        match = re.search(r'[Pp]ágina\s+(\d+)\s+de\s+(\d+)', page_text)
        if match:
            total_pages = int(match.group(2))
            if total_pages > 1:
                result['detected'] = True
                result['total_pages'] = total_pages
                result['notes'] = f'Detectado: "Página {match.group(1)} de {total_pages}"'
                return result
        
        # Padrão 2: "Exibindo X-Y de Z itens"
        match = re.search(r'[Ee]xibindo\s+(\d+)\s*[-–]\s*(\d+)\s+de\s+(\d+)', page_text)
        if match:
            total = int(match.group(3))
            items_per_page = int(match.group(2)) - int(match.group(1)) + 1
            if total > 0:
                result['detected'] = True
                result['total_items'] = total
                result['total_pages'] = (total + items_per_page - 1) // items_per_page
                result['notes'] = f'Detectado: "{match.group(1)}-{match.group(2)} de {total} itens"'
                return result
        
        # Padrão 3: Links de paginação
        page_links = re.findall(r'[?&](?:page|pagina)=(\d+)', page_html, re.IGNORECASE)
        if page_links:
            max_page = max(int(p) for p in page_links)
            if max_page > 1:
                result['detected'] = True
                result['total_pages'] = max_page
                result['notes'] = f'Detectado via links: até página {max_page}'
                return result
        
        return result
    
    async def _detect_infinite_scroll(self, page_html: str) -> Dict:
        """Detecta scroll infinito."""
        result = {'detected': False}
        
        button_patterns = [
            (r'>\s*Ver [Mm]ais\s*<', 'Ver Mais'),
            (r'>\s*Carregar [Mm]ais\s*<', 'Carregar Mais'),
            (r'>\s*Mostrar [Mm]ais\s*<', 'Mostrar Mais'),
            (r'class=["\'][^"\']*load-?more[^"\']*["\']', 'load-more'),
            (r'class=["\'][^"\']*ver-?mais[^"\']*["\']', 'ver-mais'),
        ]
        
        for pattern, description in button_patterns:
            if re.search(pattern, page_html, re.IGNORECASE):
                result['detected'] = True
                result['notes'] = f'Detectado: botão "{description}"'
                return result
        
        return result
    
    async def _detect_tabs_filter(self, page_html: str, page_text: str) -> Dict:
        """Detecta sistema de abas."""
        result = {'detected': False}
        
        tab_keywords = [
            'Todos', 'Leilão', 'Leilões', 'Judicial', 'Extrajudicial',
            'Venda Direta', 'Encerrados', 'Cancelados', 'Suspensos',
        ]
        
        found_tabs = []
        for keyword in tab_keywords:
            if keyword in page_text:
                found_tabs.append(keyword)
        
        if len(found_tabs) >= 3:
            result['detected'] = True
            result['notes'] = f'Detectado: abas ({", ".join(found_tabs[:5])})'
        
        return result
    
    async def _count_visible_items(self) -> Optional[int]:
        """Conta itens visíveis."""
        try:
            selectors = [
                'a[href*="/imovel"]',
                'a[href*="/lote"]',
                '.property-card',
                '.imovel-card',
                '.lote-card',
            ]
            
            max_count = 0
            for selector in selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    max_count = max(max_count, len(elements))
                except:
                    pass
            
            return max_count if max_count > 0 else None
        except:
            return None
    
    async def _validate_known_case(self, name: str, result: Dict):
        """Valida contra casos conhecidos."""
        name_lower = name.lower().replace(' ', '').replace('-', '')
        
        for known_name, expected in KNOWN_CASES.items():
            if known_name in name_lower:
                result['validation_status'] = 'validated'
                
                if result['pagination_type'] != expected['type']:
                    error = f"VALIDACAO FALHOU: {name} - Esperado {expected['type']}, obtido {result['pagination_type']}"
                    logger.warning(error)
                    self.validation_errors.append(error)
                    result['validation_status'] = 'FAILED'
                else:
                    logger.info(f"   Validacao OK: {name} = {expected['type']}")
                
                break
    
    def _sanitize_filename(self, name: str) -> str:
        """Remove caracteres inválidos."""
        return re.sub(r'[<>:"/\\|?*]', '_', name)[:50]
    
    async def process_all_auctioneers(self, auctioneers: List[Dict]) -> Dict:
        """Processa TODOS os leiloeiros."""
        await self.setup_browser()
        
        total = len(auctioneers)
        logger.info(f"INICIANDO MAPEAMENTO DE {total} LEILOEIROS")
        
        for i, auctioneer in enumerate(auctioneers, 1):
            name = auctioneer.get('name', 'Unknown')
            url = auctioneer.get('website', '')
            
            logger.info(f"\n[{i}/{total}] ========================================")
            
            result = await self.detect_pagination_type(url, name)
            self.results[name] = result
            
            ptype = result['pagination_type']
            items = result.get('total_items', '?')
            pages = result.get('total_pages', '?')
            logger.info(f"   Tipo: {ptype} | Itens: {items} | Paginas: {pages}")
            
            # Checkpoint a cada 30
            if i % 30 == 0:
                await self._save_checkpoint(i)
            
            await asyncio.sleep(1.5)
        
        await self.close_browser()
        await self._save_final_report()
        
        return self.results
    
    async def _save_checkpoint(self, count: int):
        """Salva checkpoint."""
        checkpoint_file = OUTPUT_DIR / f"checkpoint_{count}.json"
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        logger.info(f"Checkpoint salvo: {checkpoint_file}")
    
    async def _save_final_report(self):
        """Salva relatório final."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON completo
        json_file = OUTPUT_DIR / f"mapeamento_todos_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        # Agrupar por tipo
        by_type = {}
        for name, data in self.results.items():
            ptype = data.get('pagination_type', 'UNKNOWN')
            if ptype not in by_type:
                by_type[ptype] = []
            by_type[ptype].append(data)
        
        # Markdown
        md_file = OUTPUT_DIR / f"RELATORIO_MAPEAMENTO_TODOS_{timestamp}.md"
        
        md_content = f"""# RELATORIO DE MAPEAMENTO - TODOS OS LEILOEIROS

**Data**: {datetime.now().strftime('%d/%m/%Y %H:%M')}
**Total de Leiloeiros**: {len(self.results)}

## RESUMO POR TIPO

| Tipo | Quantidade | % |
|------|------------|---|
"""
        
        for ptype in [PaginationType.NUMERIC, PaginationType.INFINITE_SCROLL, 
                      PaginationType.SINGLE_PAGE, PaginationType.TABS_FILTER,
                      PaginationType.OFFLINE, PaginationType.BLOCKED, PaginationType.UNKNOWN]:
            items = by_type.get(ptype, [])
            pct = len(items) / len(self.results) * 100 if self.results else 0
            md_content += f"| {ptype} | {len(items)} | {pct:.1f}% |\n"
        
        # Erros de validação
        if self.validation_errors:
            md_content += f"\n## ERROS DE VALIDACAO\n\n"
            for error in self.validation_errors:
                md_content += f"- {error}\n"
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"\nMAPEAMENTO CONCLUIDO!")
        logger.info(f"JSON: {json_file}")
        logger.info(f"Markdown: {md_file}")
        
        if self.validation_errors:
            logger.warning(f"ATENCAO: {len(self.validation_errors)} erros de validacao!")


async def main():
    """Função principal."""
    
    # Carregar TODOS os leiloeiros (sem filtro!)
    csv_path = Path("LISTA_MESTRE_LEILOEIROS.csv")
    
    if not csv_path.exists():
        logger.error("Arquivo CSV nao encontrado!")
        return
    
    logger.info(f"Carregando leiloeiros de: {csv_path}")
    
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
                })
    
    logger.info(f"Total de leiloeiros carregados: {len(auctioneers)}")
    logger.info(f"(SEM FILTRO - processando TODOS)")
    
    # Executar mapeamento
    mapper = PaginationMapper()
    results = await mapper.process_all_auctioneers(auctioneers)
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
