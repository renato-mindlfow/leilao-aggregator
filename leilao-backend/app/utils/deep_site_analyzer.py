
#!/usr/bin/env python3
"""
Deep Site Analyzer
Analisa profundamente sites de leiloeiros para identificar seletores CSS
e extrair dados de exemplo.

Execução: python -m app.utils.deep_site_analyzer
"""

import asyncio
import httpx
import json
import os
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class DeepSiteAnalyzer:
    """Analisador profundo de sites de leiloeiros."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'pt-BR,pt;q=0.9',
        }
        
    async def analyze_site(self, site_data: Dict) -> Dict:
        """Analisa um site profundamente."""
        
        name = site_data.get('name', 'Unknown')
        website = site_data.get('website', '')
        
        if not website:
            return {'error': 'Website nao informado', 'success': False}
        
        logger.info(f"Analisando {name}: {website}")
        
        result = {
            'name': name,
            'website': website,
            'success': False,
            'selectors': {},
            'sample_data': [],
            'error': None,
            'analyzed_at': datetime.now().isoformat(),
        }
        
        try:
            # Tentar diferentes paths
            paths = ['/imoveis', '/lotes', '/', '/catalogo']
            
            html = None
            working_url = None
            
            for path in paths:
                url = urljoin(website, path)
                try:
                    async with httpx.AsyncClient(
                        timeout=self.timeout,
                        follow_redirects=True,
                        verify=False
                    ) as client:
                        response = await client.get(url, headers=self.headers)
                        if response.status_code == 200 and len(response.text) > 5000:
                            html = response.text
                            working_url = url
                            break
                except Exception as e:
                    logger.debug(f"Erro ao acessar {url}: {e}")
                    continue
            
            if not html:
                result['error'] = 'Nao foi possivel carregar HTML'
                return result
            
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Identificar seletores
            selectors = self._identify_selectors(soup, html)
            result['selectors'] = selectors
            
            # Extrair dados de exemplo
            sample_data = self._extract_sample_data(soup, selectors, website)
            result['sample_data'] = sample_data
            
            result['success'] = len(selectors) > 0 and len(sample_data) > 0
            result['working_url'] = working_url
            
            logger.info(f"{name}: {len(selectors)} seletores, {len(sample_data)} exemplos")
            
        except Exception as e:
            logger.error(f"Erro ao analisar {name}: {e}")
            result['error'] = str(e)[:200]
        
        return result
    
    def _identify_selectors(self, soup: BeautifulSoup, html: str) -> Dict:
        """Identifica seletores CSS para elementos importantes."""
        
        selectors = {}
        
        # 1. Card/Item selector
        card_candidates = self._find_card_selector(soup)
        if card_candidates:
            selectors['card'] = card_candidates[0]
            selectors['card_alternatives'] = card_candidates[1:3]
        
        # 2. Title selector
        title_selector = self._find_title_selector(soup, card_candidates[0] if card_candidates else None)
        if title_selector:
            selectors['title'] = title_selector
        
        # 3. Price selector
        price_selector = self._find_price_selector(soup, card_candidates[0] if card_candidates else None)
        if price_selector:
            selectors['price'] = price_selector
        
        # 4. Link selector
        link_selector = self._find_link_selector(soup, card_candidates[0] if card_candidates else None)
        if link_selector:
            selectors['link'] = link_selector
        
        # 5. Image selector
        image_selector = self._find_image_selector(soup, card_candidates[0] if card_candidates else None)
        if image_selector:
            selectors['image'] = image_selector
        
        # 6. Location selector
        location_selector = self._find_location_selector(soup, card_candidates[0] if card_candidates else None)
        if location_selector:
            selectors['location'] = location_selector
        
        return selectors
    
    def _find_card_selector(self, soup: BeautifulSoup) -> List[str]:
        """Encontra seletores para cards de propriedades."""
        
        candidates = []
        
        # Procurar por divs com classes relacionadas a cards
        patterns = [
            r'card',
            r'item',
            r'lote',
            r'imovel',
            r'property',
            r'anuncio',
            r'oferta',
        ]
        
        for tag in ['div', 'article', 'li']:
            elements = soup.find_all(tag, class_=re.compile('|'.join(patterns), re.I))
            if elements and len(elements) >= 2:
                # Pegar a classe mais comum
                classes = {}
                for elem in elements[:10]:
                    if elem.get('class'):
                        class_str = ' '.join(elem.get('class', []))
                        classes[class_str] = classes.get(class_str, 0) + 1
                
                if classes:
                    most_common = max(classes.items(), key=lambda x: x[1])
                    selector = f"{tag}.{most_common[0].split()[0]}"
                    if selector not in candidates:
                        candidates.append(selector)
        
        return candidates[:5]
    
    def _find_title_selector(self, soup: BeautifulSoup, card_selector: Optional[str] = None) -> Optional[str]:
        """Encontra seletor para título."""
        
        # Se temos card selector, procurar dentro dos cards
        if card_selector:
            try:
                cards = soup.select(card_selector)[:3]
                for card in cards:
                    # Procurar h2, h3, h4, h1
                    for tag in ['h1', 'h2', 'h3', 'h4']:
                        title = card.find(tag)
                        if title:
                            if title.get('class'):
                                return f"{tag}.{title.get('class')[0]}"
                            return tag
            except:
                pass
        
        # Fallback: procurar em todo o documento
        for tag in ['h2', 'h3', 'h4']:
            titles = soup.find_all(tag, limit=5)
            if titles:
                for title in titles:
                    if title.get('class'):
                        return f"{tag}.{title.get('class')[0]}"
                return tag
        
        return None
    
    def _find_price_selector(self, soup: BeautifulSoup, card_selector: Optional[str] = None) -> Optional[str]:
        """Encontra seletor para preço."""
        
        price_patterns = [r'preco', r'price', r'valor', r'lance', r'custo']
        
        if card_selector:
            try:
                cards = soup.select(card_selector)[:3]
                for card in cards:
                    # Procurar por texto com R$
                    text = card.get_text()
                    if 'R$' in text or 'reais' in text.lower():
                        # Procurar elemento com classe relacionada a preço
                        for pattern in price_patterns:
                            elem = card.find(class_=re.compile(pattern, re.I))
                            if elem:
                                if elem.get('class'):
                                    return f".{elem.get('class')[0]}"
                        # Se não encontrou classe, procurar span/div com R$
                        for tag in ['span', 'div', 'p']:
                            elem = card.find(tag, string=re.compile(r'R\$', re.I))
                            if elem:
                                if elem.get('class'):
                                    return f"{tag}.{elem.get('class')[0]}"
                                return tag
            except:
                pass
        
        # Fallback: procurar em todo documento
        for pattern in price_patterns:
            elem = soup.find(class_=re.compile(pattern, re.I))
            if elem:
                if elem.get('class'):
                    return f".{elem.get('class')[0]}"
        
        return None
    
    def _find_link_selector(self, soup: BeautifulSoup, card_selector: Optional[str] = None) -> Optional[str]:
        """Encontra seletor para links."""
        
        if card_selector:
            try:
                cards = soup.select(card_selector)[:3]
                for card in cards:
                    link = card.find('a', href=True)
                    if link:
                        href = link.get('href', '')
                        if any(p in href.lower() for p in ['/imovel', '/lote', '/item', '/detalhes']):
                            if link.get('class'):
                                return f"a.{link.get('class')[0]}"
                            return 'a'
            except:
                pass
        
        return 'a[href]'
    
    def _find_image_selector(self, soup: BeautifulSoup, card_selector: Optional[str] = None) -> Optional[str]:
        """Encontra seletor para imagens."""
        
        if card_selector:
            try:
                cards = soup.select(card_selector)[:3]
                for card in cards:
                    img = card.find('img', src=True)
                    if img:
                        if img.get('class'):
                            return f"img.{img.get('class')[0]}"
                        return 'img'
            except:
                pass
        
        return 'img[src]'
    
    def _find_location_selector(self, soup: BeautifulSoup, card_selector: Optional[str] = None) -> Optional[str]:
        """Encontra seletor para localização."""
        
        location_patterns = [r'local', r'location', r'endereco', r'cidade', r'cidade']
        
        if card_selector:
            try:
                cards = soup.select(card_selector)[:3]
                for card in cards:
                    for pattern in location_patterns:
                        elem = card.find(class_=re.compile(pattern, re.I))
                        if elem:
                            if elem.get('class'):
                                return f".{elem.get('class')[0]}"
            except:
                pass
        
        return None
    
    def _extract_sample_data(self, soup: BeautifulSoup, selectors: Dict, base_url: str) -> List[Dict]:
        """Extrai dados de exemplo usando os seletores identificados."""
        
        samples = []
        
        card_selector = selectors.get('card')
        if not card_selector:
            return samples
        
        try:
            cards = soup.select(card_selector)[:5]  # Limitar a 5 exemplos
            
            for card in cards:
                sample = {}
                
                # Título
                title_sel = selectors.get('title')
                if title_sel:
                    try:
                        title_elem = card.select_one(title_sel) if title_sel != 'h2' else card.find('h2') or card.find('h3')
                        if title_elem:
                            sample['title'] = title_elem.get_text(strip=True)[:100]
                    except:
                        pass
                
                # Preço
                price_sel = selectors.get('price')
                if price_sel:
                    try:
                        price_elem = card.select_one(price_sel)
                        if price_elem:
                            sample['price'] = price_elem.get_text(strip=True)[:50]
                    except:
                        pass
                
                # Link
                link_sel = selectors.get('link', 'a')
                try:
                    link_elem = card.select_one(link_sel) if link_sel != 'a' else card.find('a', href=True)
                    if link_elem:
                        href = link_elem.get('href', '')
                        sample['link'] = urljoin(base_url, href)
                except:
                    pass
                
                # Imagem
                img_sel = selectors.get('image', 'img')
                try:
                    img_elem = card.select_one(img_sel) if img_sel != 'img' else card.find('img', src=True)
                    if img_elem:
                        src = img_elem.get('src', '')
                        sample['image'] = urljoin(base_url, src)
                except:
                    pass
                
                # Localização
                loc_sel = selectors.get('location')
                if loc_sel:
                    try:
                        loc_elem = card.select_one(loc_sel)
                        if loc_elem:
                            sample['location'] = loc_elem.get_text(strip=True)[:100]
                    except:
                        pass
                
                if sample.get('title') or sample.get('link'):
                    samples.append(sample)
        
        except Exception as e:
            logger.debug(f"Erro ao extrair dados de exemplo: {e}")
        
        return samples
    
    async def analyze_batch(self, sites: List[Dict], max_sites: int = 5) -> List[Dict]:
        """Analisa um lote de sites."""
        
        sites_to_analyze = sites[:max_sites]
        results = []
        
        for i, site in enumerate(sites_to_analyze, 1):
            logger.info(f"[{i}/{len(sites_to_analyze)}] Analisando {site.get('name', 'Unknown')}...")
            result = await self.analyze_site(site)
            results.append(result)
            await asyncio.sleep(2)  # Pausa entre sites
        
        return results
    
    def save_results(self, results: List[Dict], output_dir: str = "site_analysis"):
        """Salva resultados em arquivos."""
        
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Salvar configurações JSON
        configs = []
        for result in results:
            if result.get('success') and result.get('selectors'):
                config = {
                    'name': result['name'],
                    'website': result['website'],
                    'selectors': result['selectors'],
                    'working_url': result.get('working_url'),
                }
                configs.append(config)
                
                # Salvar individual
                config_file = f"{output_dir}/scraper_config_{result['name'].lower().replace(' ', '_')}_{timestamp}.json"
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
        
        # Relatório markdown
        report_file = f"{output_dir}/report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Relatorio de Analise Profunda de Sites\n\n")
            f.write(f"Timestamp: {timestamp}\n\n")
            
            successful = [r for r in results if r.get('success')]
            f.write(f"## Resumo\n\n")
            f.write(f"- Total analisado: {len(results)}\n")
            f.write(f"- Sucesso: {len(successful)}\n")
            f.write(f"- Falhou: {len(results) - len(successful)}\n\n")
            
            f.write("## Sites Analisados\n\n")
            for result in results:
                status = "OK" if result.get('success') else "FALHOU"
                f.write(f"### {result['name']} - {status}\n\n")
                f.write(f"- Website: {result['website']}\n")
                
                if result.get('success'):
                    f.write(f"- Seletores encontrados: {len(result.get('selectors', {}))}\n")
                    f.write(f"- Exemplos extraidos: {len(result.get('sample_data', []))}\n\n")
                    
                    f.write("**Seletores:**\n")
                    for key, value in result.get('selectors', {}).items():
                        f.write(f"- {key}: `{value}`\n")
                    f.write("\n")
                    
                    if result.get('sample_data'):
                        f.write("**Exemplos:**\n")
                        for i, sample in enumerate(result.get('sample_data', [])[:3], 1):
                            f.write(f"{i}. {sample.get('title', 'N/A')[:60]}\n")
                            if sample.get('price'):
                                f.write(f"   Preco: {sample['price']}\n")
                        f.write("\n")
                else:
                    f.write(f"- Erro: {result.get('error', 'N/A')}\n\n")
        
        logger.info(f"Resultados salvos em {output_dir}/")
        return {'configs': configs, 'report_file': report_file}


def load_top_sites_from_discovery(max_sites: int = 5):
    """Carrega top sites do discovery."""
    
    discovery_files = [
        'discovery_results/discovery_20260104_151236.json',
    ]
    
    for file_path in discovery_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Filtrar sites online e simples
                sites = [
                    s for s in data 
                    if s.get('is_online') and 
                    s.get('recommended_method') in ['httpx_simple', 'httpx_stealth']
                ]
                # Ordenar por método (httpx_simple primeiro)
                sites.sort(key=lambda x: (x.get('recommended_method') != 'httpx_simple', x.get('name', '')))
                logger.info(f"Carregados {len(sites)} sites do discovery")
                return sites[:max_sites]
    
    return []


async def main():
    """Função principal."""
    
    print("=" * 60)
    print("DEEP SITE ANALYZER")
    print("=" * 60)
    
    # Carregar sites
    sites = load_top_sites_from_discovery(max_sites=5)
    
    if not sites:
        print("Nenhum site encontrado no discovery!")
        return
    
    print(f"\nSites para analisar: {len(sites)}")
    for i, site in enumerate(sites, 1):
        print(f"  {i}. {site.get('name')} - {site.get('website')}")
    
    # Criar analyzer
    analyzer = DeepSiteAnalyzer(timeout=30.0)
    
    print("\nIniciando analise...")
    print("(Este processo pode levar ~10 minutos)\n")
    
    # Analisar
    results = await analyzer.analyze_batch(sites, max_sites=5)
    
    # Salvar resultados
    files = analyzer.save_results(results)
    
    # Relatório
    print("\n" + "=" * 60)
    print("RELATORIO FINAL")
    print("=" * 60)
    
    successful = [r for r in results if r.get('success')]
    print(f"\nSites com sucesso: {len(successful)}/{len(results)}")
    
    print(f"\nSeletores identificados:")
    for result in successful:
        print(f"\n  {result['name']}:")
        for key, value in result.get('selectors', {}).items():
            print(f"    {key}: {value}")
    
    print(f"\nExemplos de dados extraidos:")
    for result in successful[:3]:
        print(f"\n  {result['name']}:")
        for i, sample in enumerate(result.get('sample_data', [])[:2], 1):
            print(f"    {i}. {sample.get('title', 'N/A')[:60]}")
            if sample.get('price'):
                print(f"       Preco: {sample['price']}")
    
    print(f"\nArquivos gerados em site_analysis/")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
