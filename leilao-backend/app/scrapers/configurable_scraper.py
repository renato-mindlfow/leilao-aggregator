
#!/usr/bin/env python3
"""
Configurable Scraper
Scraper configurável que usa configurações JSON para fazer scraping
de múltiplos sites de leiloeiros.

Execução: python -m app.scrapers.configurable_scraper
"""

import asyncio
import httpx
import json
import csv
import os
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


class ConfigurableScraper:
    """Scraper configurável baseado em configurações JSON."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'pt-BR,pt;q=0.9',
        }
        self.properties: List[Dict] = []
        
    async def scrape_site(self, config: Dict) -> List[Dict]:
        """Scrape um site usando configuração JSON."""
        
        name = config.get('name', 'Unknown')
        website = config.get('website', '')
        selectors = config.get('selectors', {})
        working_url = config.get('working_url', website)
        
        if not website or not selectors:
            logger.warning(f"{name}: Configuracao incompleta")
            return []
        
        logger.info(f"Scraping {name}: {website}")
        
        properties = []
        
        try:
            # Acessar URL
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                verify=False
            ) as client:
                response = await client.get(working_url, headers=self.headers)
                
                if response.status_code != 200:
                    logger.warning(f"{name}: HTTP {response.status_code}")
                    return []
                
                html = response.text
                if not html or len(html) < 1000:
                    logger.warning(f"{name}: HTML muito pequeno")
                    return []
                
                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extrair propriedades
                card_selector = selectors.get('card')
                if not card_selector:
                    logger.warning(f"{name}: Seletor de card nao encontrado")
                    return []
                
                cards = soup.select(card_selector)
                logger.info(f"{name}: Encontrados {len(cards)} cards")
                
                for card in cards[:50]:  # Limitar a 50 cards
                    try:
                        prop = self._extract_property(card, selectors, website, name)
                        if prop:
                            properties.append(prop)
                    except Exception as e:
                        logger.debug(f"Erro ao extrair card: {e}")
                        continue
                
                logger.info(f"{name}: {len(properties)} propriedades extraidas")
                
        except Exception as e:
            logger.error(f"Erro ao fazer scraping de {name}: {e}")
        
        return properties
    
    def _extract_property(self, card, selectors: Dict, base_url: str, source: str) -> Optional[Dict]:
        """Extrai dados de uma propriedade de um card."""
        
        prop = {
            'source': source,
            'extracted_at': datetime.now().isoformat(),
        }
        
        # Título
        title_sel = selectors.get('title')
        if title_sel:
            try:
                title_elem = card.select_one(title_sel) if '.' in title_sel or '#' in title_sel else card.find(title_sel.replace('h', 'h'))
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title and len(title) > 10:
                        prop['title'] = title
            except:
                pass
        
        # Preço
        price_sel = selectors.get('price')
        if price_sel:
            try:
                price_elem = card.select_one(price_sel) if price_sel.startswith('.') or price_sel.startswith('#') else card.find(class_=price_sel.replace('.', ''))
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price_value = self._parse_price(price_text)
                    prop['price_text'] = price_text
                    prop['price'] = price_value
            except:
                pass
        
        # Link
        link_sel = selectors.get('link', 'a[href]')
        try:
            if link_sel == 'a[href]':
                link_elem = card.find('a', href=True)
            else:
                link_elem = card.select_one(link_sel) if link_sel else card.find('a', href=True)
            
            if link_elem:
                href = link_elem.get('href', '')
                if href:
                    prop['link'] = urljoin(base_url, href)
        except:
            pass
        
        # Imagem
        img_sel = selectors.get('image', 'img')
        try:
            if img_sel == 'img' or img_sel == 'img[src]':
                img_elem = card.find('img', src=True)
            else:
                img_elem = card.select_one(img_sel) if img_sel else card.find('img', src=True)
            
            if img_elem:
                src = img_elem.get('src', '')
                if src:
                    prop['image_url'] = urljoin(base_url, src)
        except:
            pass
        
        # Localização
        loc_sel = selectors.get('location')
        if loc_sel:
            try:
                loc_elem = card.select_one(loc_sel) if loc_sel.startswith('.') or loc_sel.startswith('#') else None
                if loc_elem:
                    prop['location'] = loc_elem.get_text(strip=True)[:200]
            except:
                pass
        
        # Validar: precisa ter título ou link
        if prop.get('title') or prop.get('link'):
            return prop
        
        return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parseia preço de texto."""
        if not price_text:
            return None
        
        # Remover R$ e espaços
        price_text = re.sub(r'R\$\s*', '', price_text, flags=re.I)
        price_text = price_text.strip()
        
        # Remover pontos de milhar e substituir vírgula por ponto
        # Padrão brasileiro: 1.234.567,89
        price_text = price_text.replace('.', '').replace(',', '.')
        
        # Extrair número
        match = re.search(r'(\d+\.?\d*)', price_text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        
        return None
    
    async def scrape_batch(self, configs: List[Dict]) -> List[Dict]:
        """Scrape um lote de sites usando configurações."""
        
        all_properties = []
        
        for i, config in enumerate(configs, 1):
            name = config.get('name', 'Unknown')
            logger.info(f"[{i}/{len(configs)}] Processando {name}...")
            
            try:
                properties = await self.scrape_site(config)
                all_properties.extend(properties)
                await asyncio.sleep(2)  # Pausa entre sites
            except Exception as e:
                logger.error(f"Erro ao processar {name}: {e}")
                continue
        
        self.properties = all_properties
        return all_properties
    
    def save_results(self, json_file: str = "extracted_properties.json", csv_file: str = "extracted_properties.csv"):
        """Salva resultados em JSON e CSV."""
        
        # Salvar JSON
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_properties': len(self.properties),
            'properties': self.properties,
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Resultados JSON salvos em {json_file}")
        
        # Salvar CSV
        if self.properties:
            fieldnames = ['source', 'title', 'price_text', 'price', 'location', 'link', 'image_url', 'extracted_at']
            
            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.properties)
            
            logger.info(f"Resultados CSV salvos em {csv_file}")
        
        return {'json_file': json_file, 'csv_file': csv_file}


def load_configs_from_site_analysis():
    """Carrega configurações do diretório site_analysis."""
    
    config_dir = 'site_analysis'
    if not os.path.exists(config_dir):
        logger.warning(f"Diretorio {config_dir} nao encontrado")
        return []
    
    configs = []
    for filename in os.listdir(config_dir):
        if filename.startswith('scraper_config_') and filename.endswith('.json'):
            filepath = os.path.join(config_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get('selectors'):
                        configs.append(config)
            except Exception as e:
                logger.warning(f"Erro ao carregar {filename}: {e}")
                continue
    
    logger.info(f"Carregadas {len(configs)} configuracoes")
    return configs


async def main():
    """Função principal."""
    
    print("=" * 60)
    print("CONFIGURABLE SCRAPER")
    print("=" * 60)
    
    # Carregar configurações
    configs = load_configs_from_site_analysis()
    
    if not configs:
        print("Nenhuma configuracao encontrada em site_analysis/")
        return
    
    print(f"\nConfiguracoes carregadas: {len(configs)}")
    for i, config in enumerate(configs, 1):
        print(f"  {i}. {config.get('name')} - {config.get('website')}")
    
    # Criar scraper
    scraper = ConfigurableScraper(timeout=30.0)
    
    print("\nIniciando scraping...")
    print("(Este processo pode levar ~10 minutos)\n")
    
    # Scrape
    properties = await scraper.scrape_batch(configs)
    
    # Salvar resultados
    files = scraper.save_results()
    
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
        title = prop.get('title', 'N/A')[:70]
        price = prop.get('price_text', prop.get('price', 'N/A'))
        source = prop.get('source', 'N/A')
        print(f"\n  {i}. {title}")
        print(f"     Preco: {price}")
        print(f"     Fonte: {source}")
    
    print(f"\nArquivos gerados:")
    print(f"  - {files['json_file']}")
    print(f"  - {files['csv_file']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
