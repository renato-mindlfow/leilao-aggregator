#!/usr/bin/env python3
"""
EXTRATOR INTELIGENTE COM PAGINAÇÃO
Extrai todos os imóveis baseado no tipo de paginação mapeado.
"""

import asyncio
import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page, Browser
import logging

# Importar o LLMEnhancedScraper existente
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import the scraper
try:
    from app.services.llm_enhanced_scraper import LLMEnhancedScraper
    HAS_LLM_SCRAPER = True
except ImportError:
    HAS_LLM_SCRAPER = False
    logging.warning("LLMEnhancedScraper não disponível - usando extração simplificada")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("logs/extracao_completa")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class SmartExtractor:
    """Extrator inteligente que usa estratégia baseada no tipo de paginação."""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.scraper = LLMEnhancedScraper(headless=True) if HAS_LLM_SCRAPER else None
        self.all_properties: List[Dict] = []
        
    async def setup_browser(self):
        """Configura browser."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
                    if pattern.startswith('?') or pattern.startswith('&'):
                        base_clean = base_url.split('?')[0]
                        page_url = base_clean + pattern.format(page_num)
                    else:
                        page_url = base_url + pattern.format(page_num)
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
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"      ❌ Erro na página {page_num}: {e}")
                continue
        
        return properties
    
    async def extract_infinite_scroll(self, url: str, name: str) -> List[Dict]:
        """Extrai de sites com scroll infinito / botão ver mais."""
        properties = []
        
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
            
            max_clicks = 50  # Limite de segurança
            click_count = 0
            last_count = 0
            no_change_count = 0
            
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
                            await asyncio.sleep(1.5)
                            break
                    except:
                        continue
                
                if not clicked:
                    logger.info(f"   ✅ Botão não encontrado - todos os itens carregados")
                    break
                
                # Verificar se carregou novos itens
                current_count = await self._count_items()
                if current_count == last_count:
                    no_change_count += 1
                    if no_change_count >= 3:
                        logger.info(f"   ✅ Nenhum item novo - fim do scroll")
                        break
                else:
                    no_change_count = 0
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
        """Extrai imóveis de uma única página usando LLMEnhancedScraper ou método simples."""
        try:
            if self.scraper and HAS_LLM_SCRAPER:
                # Usar o scraper existente
                properties = self.scraper.scrape_url_sync(url, name.lower().replace(' ', '_'))
                return properties
            else:
                # Método simplificado: extrair links de imóveis
                await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
                
                # Procurar links de imóveis
                links = await self.page.query_selector_all('a[href*="/imovel"], a[href*="/lote"], a[href*="/item"]')
                
                properties = []
                for link in links[:100]:  # Limite de 100 por página
                    try:
                        href = await link.get_attribute('href')
                        text = await link.text_content()
                        if href:
                            properties.append({
                                'title': text.strip() if text else 'Imóvel',
                                'url': href,
                                'auctioneer': name
                            })
                    except:
                        continue
                
                return properties
        except Exception as e:
            logger.error(f"Erro na extração de {url}: {e}")
            return []
    
    async def _count_items(self) -> int:
        """Conta itens visíveis."""
        selectors = [
            'a[href*="/imovel/"]', 
            'a[href*="/lote/"]', 
            '.property-card', 
            '.imovel-card',
            '.lote-card'
        ]
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
        
        try:
            if ptype == 'NUMERIC':
                return await self.extract_numeric_pagination(url, name, total_pages)
            elif ptype == 'INFINITE_SCROLL':
                return await self.extract_infinite_scroll(url, name)
            else:
                # SINGLE_PAGE, TABS_FILTER, UNKNOWN
                return await self.extract_single_page(url, name)
        except Exception as e:
            logger.error(f"   ❌ Erro ao processar {name}: {e}")
            return []
    
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
            
            await asyncio.sleep(2)
        
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
        
        # Relatório markdown
        md_file = OUTPUT_DIR / f"RELATORIO_EXTRACAO_{timestamp}.md"
        md_content = f"""# 📊 RELATÓRIO DE EXTRAÇÃO COMPLETA

**Data**: {datetime.now().strftime('%d/%m/%Y %H:%M')}
**Total de Leiloeiros**: {results['total_auctioneers']}
**Total de Imóveis**: {results['total_properties']:,}

---

## 📈 EXTRAÇÃO POR LEILOEIRO

| Leiloeiro | Imóveis | Status |
|-----------|---------|--------|
"""
        
        # Ordenar por quantidade de imóveis
        sorted_auctioneers = sorted(
            results['by_auctioneer'].items(), 
            key=lambda x: x[1].get('count', 0), 
            reverse=True
        )
        
        for name, data in sorted_auctioneers:
            count = data.get('count', 0)
            error = data.get('error', '')
            status = '❌ Erro' if error else '✅ Sucesso'
            md_content += f"| {name} | {count:,} | {status} |\n"
        
        md_content += f"""

---

## ✅ RESUMO

- **Total de imóveis extraídos**: {results['total_properties']:,}
- **Leiloeiros processados**: {results['total_auctioneers']}
- **Arquivo de propriedades**: `{props_file.name}`
"""
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"\n✅ Extração concluída!")
        logger.info(f"   Total: {results['total_properties']:,} imóveis")
        logger.info(f"   JSON: {json_file}")
        logger.info(f"   Propriedades: {props_file}")
        logger.info(f"   Relatório: {md_file}")


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
        if data.get('pagination_type') != 'UNKNOWN'  # Pular sites com erro
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
    logger.info(f"   Total: {results['total_properties']:,} imóveis")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())
