
#!/usr/bin/env python3
"""
Universal Scraper V2
Scraper universal que usa os resultados do discovery para fazer scraping
de múltiplos sites de leiloeiros.

Execução: python -m app.scrapers.universal_scraper_v2
"""

import asyncio
import httpx
import json
import os
import sys
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class UniversalScraperV2:
    """Scraper universal V2 que usa resultados do discovery."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'pt-BR,pt;q=0.9',
        }
        self.results: List[Dict] = []
        
    async def scrape_site(self, site_data: Dict) -> List[Dict]:
        """Scrape um site usando os dados do discovery."""
        
        name = site_data.get('name', 'Unknown')
        website = site_data.get('website', '')
        selectors = site_data.get('selectors', {})
        
        if not website:
            logger.warning(f"{name}: Website nao informado")
            return []
        
        logger.info(f"Iniciando scraping de {name}: {website}")
        
        properties = []
        
        try:
            # Tentar diferentes paths
            possible_paths = [
                '/imoveis',
                '/lotes',
                '/imoveis/todos',
                '/leiloes/imoveis',
                '/catalogo/imoveis',
                '/',
            ]
            
            for path in possible_paths:
                url = urljoin(website, path)
                
                try:
                    async with httpx.AsyncClient(
                        timeout=self.timeout,
                        follow_redirects=True,
                        verify=False
                    ) as client:
                        
                        response = await client.get(url, headers=self.headers)
                        
                        if response.status_code != 200:
                            continue
                        
                        html = response.text
                        if not html or len(html) < 1000:
                            continue
                        
                        # Parsear HTML
                        soup = BeautifulSoup(html, 'lxml')
                        
                        # Tentar extrair propriedades
                        site_properties = self._extract_properties(
                            soup, name, website, selectors
                        )
                        
                        if site_properties:
                            properties.extend(site_properties)
                            logger.info(f"{name}: {len(site_properties)} imoveis encontrados em {url}")
                            break
                        
                except Exception as e:
                    logger.debug(f"{name}: Erro ao tentar {url}: {e}")
                    continue
            
            logger.info(f"{name}: Total de {len(properties)} imoveis extraidos")
            
        except Exception as e:
            logger.error(f"{name}: Erro no scraping: {e}")
        
        return properties
    
    def _extract_properties(self, soup: BeautifulSoup, source: str, base_url: str, selectors: Dict) -> List[Dict]:
        """Extrai propriedades do HTML usando seletores."""
        
        properties = []
        
        # Seletores para encontrar cards
        card_selectors = [
            selectors.get('property_card', ''),
            'div[class*="card"]',
            'div[class*="item"]',
            'div[class*="lote"]',
            'article',
            'div[class*="imovel"]',
        ]
        
        cards = []
        for selector in card_selectors:
            if selector:
                cards = soup.select(selector)
                if cards:
                    break
        
        if not cards:
            # Fallback: procurar por links que parecem ser de imóveis
            links = soup.find_all('a', href=re.compile(r'/imovel|/lote|/item|/detalhes', re.I))
            if links:
                # Criar cards falsos a partir dos links
                for link in links[:20]:  # Limitar a 20
                    prop = self._extract_from_link(link, source, base_url)
                    if prop:
                        properties.append(prop)
                return properties
            return []
        
        # Extrair propriedades dos cards
        for card in cards[:50]:  # Limitar a 50 cards
            try:
                prop = self._extract_from_card(card, source, base_url, selectors)
                if prop:
                    properties.append(prop)
            except Exception as e:
                logger.debug(f"Erro ao extrair card: {e}")
                continue
        
        return properties
    
    def _extract_from_card(self, card, source: str, base_url: str, selectors: Dict) -> Optional[Dict]:
        """Extrai dados de um card de propriedade."""
        
        # Título
        title_elem = (
            card.select_one(selectors.get('title', 'h2, h3, h4, [class*="title"]')) or
            card.find(['h2', 'h3', 'h4']) or
            card.find(class_=re.compile(r'title|titulo', re.I))
        )
        title = title_elem.get_text(strip=True) if title_elem else ''
        
        if not title or len(title) < 10:
            return None
        
        # Link
        link_elem = card.find('a', href=True)
        link = ''
        if link_elem:
            href = link_elem.get('href', '')
            link = urljoin(base_url, href) if href else ''
        
        # Preço
        price_elem = (
            card.select_one(selectors.get('price', '[class*="price"], [class*="valor"]')) or
            card.find(class_=re.compile(r'price|valor|lance|preco', re.I))
        )
        price_text = price_elem.get_text(strip=True) if price_elem else ''
        price = self._parse_price(price_text)
        
        # Localização
        location_elem = (
            card.select_one(selectors.get('location', '[class*="location"], [class*="cidade"]')) or
            card.find(class_=re.compile(r'location|local|cidade|endereco', re.I))
        )
        location = location_elem.get_text(strip=True) if location_elem else ''
        
        # Imagem
        img_elem = card.find('img', src=True)
        image_url = ''
        if img_elem:
            src = img_elem.get('src', '')
            image_url = urljoin(base_url, src) if src else ''
        
        prop = {
            'title': title,
            'source': source,
            'source_url': link or base_url,
            'image_url': image_url,
            'price': price,
            'location': location,
            'extracted_at': datetime.now().isoformat(),
        }
        
        return prop
    
    def _extract_from_link(self, link, source: str, base_url: str) -> Optional[Dict]:
        """Extrai dados básicos de um link."""
        
        href = link.get('href', '')
        if not href:
            return None
        
        full_url = urljoin(base_url, href)
        text = link.get_text(strip=True)
        
        if not text or len(text) < 10:
            return None
        
        return {
            'title': text,
            'source': source,
            'source_url': full_url,
            'image_url': '',
            'price': None,
            'location': '',
            'extracted_at': datetime.now().isoformat(),
        }
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parseia preço de texto."""
        if not price_text:
            return None
        
        # Remover R$ e espaços (escapar $ para regex)
        price_text = re.sub(r'R\$\s*', '', price_text, flags=re.I)
        price_text = price_text.strip()
        
        # Remover pontos e substituir vírgula por ponto
        price_text = price_text.replace('.', '').replace(',', '.')
        
        # Extrair número
        match = re.search(r'(\d+\.?\d*)', price_text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        
        return None
    
    async def scrape_batch(self, sites: List[Dict], max_sites: int = 10) -> List[Dict]:
        """Scrape um lote de sites."""
        
        # Limitar número de sites
        sites_to_scrape = sites[:max_sites]
        
        logger.info(f"Scraping {len(sites_to_scrape)} sites...")
        
        all_properties = []
        
        for i, site in enumerate(sites_to_scrape, 1):
            logger.info(f"[{i}/{len(sites_to_scrape)}] Processando {site.get('name', 'Unknown')}...")
            
            try:
                properties = await self.scrape_site(site)
                all_properties.extend(properties)
                
                # Pequena pausa entre sites
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Erro ao processar {site.get('name', 'Unknown')}: {e}")
                continue
        
        self.results = all_properties
        return all_properties
    
    def save_results(self, output_file: str = "scraping_results.json"):
        """Salva resultados em arquivo JSON."""
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_properties': len(self.results),
            'properties': self.results,
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Resultados salvos em {output_file}")
        return output_file


def load_discovery_results():
    """Carrega resultados do discovery."""
    
    discovery_files = [
        'discovery_results/discovery_20260104_151236.json',
        'discovery_results/discovery_20260104_151610.json',
    ]
    
    for file_path in discovery_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Filtrar apenas sites online e simples
                sites = [
                    s for s in data 
                    if s.get('is_online') and 
                    s.get('recommended_method') in ['httpx_simple', 'httpx_stealth']
                ]
                # Ordenar por método (httpx_simple primeiro)
                sites.sort(key=lambda x: (x.get('recommended_method') != 'httpx_simple', x.get('name', '')))
                logger.info(f"Carregados {len(sites)} sites do discovery de {file_path}")
                return sites
    
    logger.warning("Nenhum arquivo de discovery encontrado")
    return []


async def main():
    """Função principal."""
    
    print("=" * 60)
    print("UNIVERSAL SCRAPER V2")
    print("=" * 60)
    
    # Carregar sites do discovery
    sites = load_discovery_results()
    
    if not sites:
        print("Nenhum site encontrado no discovery!")
        return
    
    print(f"\nSites para processar: {len(sites)}")
    print("\nTop 10 sites:")
    for i, site in enumerate(sites[:10], 1):
        print(f"  {i}. {site.get('name')} - {site.get('website')}")
    
    # Criar scraper
    scraper = UniversalScraperV2(timeout=30.0)
    
    print("\nIniciando scraping...")
    print("(Este processo pode levar 10-15 minutos)\n")
    
    # Scrape
    properties = await scraper.scrape_batch(sites, max_sites=10)
    
    # Salvar resultados
    output_file = scraper.save_results()
    
    # Relatório
    print("\n" + "=" * 60)
    print("RELATORIO FINAL")
    print("=" * 60)
    
    print(f"\nTotal de imoveis extraidos: {len(properties)}")
    
    # Agrupar por site
    by_site = {}
    for prop in properties:
        source = prop.get('source', 'Unknown')
        by_site[source] = by_site.get(source, 0) + 1
    
    print(f"\nImoveis por site:")
    for site, count in sorted(by_site.items(), key=lambda x: -x[1]):
        print(f"  {site}: {count}")
    
    # Exemplos
    print(f"\nExemplos de imoveis extraidos:")
    for i, prop in enumerate(properties[:5], 1):
        title = prop.get('title', 'N/A')[:60]
        price = prop.get('price', 'N/A')
        print(f"  {i}. {title}")
        print(f"     Preco: {price}")
        print(f"     Fonte: {prop.get('source', 'N/A')}")
    
    print(f"\nArquivo gerado: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
