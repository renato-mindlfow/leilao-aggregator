
#!/usr/bin/env python3
"""
Tier1 Config Generator
Gera configurações Tier1 para sites de leiloeiros
e testa extração de dados.

Execução: python -m app.utils.tier1_config_generator
"""

import asyncio
import httpx
import json
import os
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class Tier1ConfigGenerator:
    """Gerador de configurações Tier1 para sites de leiloeiros."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'pt-BR,pt;q=0.9',
        }
        
    async def analyze_and_extract(self, config: Dict) -> Dict:
        """Analisa site e extrai dados de teste."""
        
        name = config.get('name', 'Unknown')
        website = config.get('website', '')
        selectors = config.get('selectors', {})
        working_url = config.get('working_url', website)
        
        result = {
            'name': name,
            'website': website,
            'success': False,
            'properties_found': 0,
            'sample_properties': [],
            'error': None,
            'analyzed_at': datetime.now().isoformat(),
        }
        
        if not website or not selectors:
            result['error'] = 'Configuracao incompleta'
            return result
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                verify=False
            ) as client:
                response = await client.get(working_url, headers=self.headers)
                
                if response.status_code != 200:
                    result['error'] = f'HTTP {response.status_code}'
                    return result
                
                html = response.text
                if not html or len(html) < 1000:
                    result['error'] = 'HTML muito pequeno'
                    return result
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extrair propriedades de teste
                card_selector = selectors.get('card')
                if card_selector:
                    cards = soup.select(card_selector)[:10]  # Limitar a 10 para teste
                    
                    samples = []
                    for card in cards:
                        prop = self._extract_property_test(card, selectors, website, name)
                        if prop:
                            samples.append(prop)
                    
                    result['properties_found'] = len(samples)
                    result['sample_properties'] = samples[:5]  # Top 5 exemplos
                    result['success'] = len(samples) > 0
                else:
                    result['error'] = 'Seletor de card nao encontrado'
        
        except Exception as e:
            result['error'] = str(e)[:200]
        
        return result
    
    def _extract_property_test(self, card, selectors: Dict, base_url: str, source: str) -> Optional[Dict]:
        """Extrai dados de teste de um card."""
        
        prop = {}
        
        # Título
        title_sel = selectors.get('title')
        if title_sel:
            try:
                title_elem = card.select_one(title_sel) if '.' in title_sel or '#' in title_sel else card.find(title_sel.replace('h', 'h'))
                if title_elem:
                    prop['title'] = title_elem.get_text(strip=True)[:150]
            except:
                pass
        
        # Preço
        price_sel = selectors.get('price')
        if price_sel:
            try:
                price_elem = card.select_one(price_sel) if price_sel.startswith('.') or price_sel.startswith('#') else None
                if price_elem:
                    prop['price'] = price_elem.get_text(strip=True)[:100]
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
        
        if prop.get('title') or prop.get('link'):
            return prop
        
        return None
    
    async def process_batch(self, configs: List[Dict]) -> List[Dict]:
        """Processa um lote de configurações."""
        
        results = []
        
        for i, config in enumerate(configs, 1):
            name = config.get('name', 'Unknown')
            logger.info(f"[{i}/{len(configs)}] Analisando {name}...")
            
            result = await self.analyze_and_extract(config)
            results.append(result)
            
            await asyncio.sleep(1)  # Pausa entre sites
        
        return results
    
    def generate_tier1_config(self, original_config: Dict, analysis_result: Dict) -> Dict:
        """Gera configuração Tier1 a partir da config original e resultado da análise."""
        
        tier1_config = {
            'version': '1.0',
            'tier': 'tier1',
            'name': original_config.get('name'),
            'website': original_config.get('website'),
            'working_url': original_config.get('working_url', original_config.get('website')),
            'selectors': original_config.get('selectors', {}),
            'status': 'active' if analysis_result.get('success') else 'inactive',
            'properties_count': analysis_result.get('properties_found', 0),
            'last_tested_at': analysis_result.get('analyzed_at'),
            'created_at': datetime.now().isoformat(),
        }
        
        return tier1_config
    
    def save_configs(self, results: List[Dict], original_configs: List[Dict], output_dir: str = "app/configs/sites"):
        """Salva configurações Tier1."""
        
        os.makedirs(output_dir, exist_ok=True)
        
        saved_configs = []
        
        for i, (result, orig_config) in enumerate(zip(results, original_configs)):
            if result.get('success'):
                tier1_config = self.generate_tier1_config(orig_config, result)
                
                # Nome do arquivo: slug do nome do site
                site_name = orig_config.get('name', 'unknown').lower()
                site_name = re.sub(r'[^a-z0-9]+', '_', site_name)
                site_name = site_name.strip('_')
                
                config_file = os.path.join(output_dir, f"{site_name}.json")
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(tier1_config, f, ensure_ascii=False, indent=2)
                
                saved_configs.append({
                    'name': orig_config.get('name'),
                    'file': config_file,
                    'properties_found': result.get('properties_found', 0),
                })
                
                logger.info(f"Config salva: {config_file}")
        
        return saved_configs
    
    def generate_report(self, results: List[Dict], saved_configs: List[Dict]) -> Dict:
        """Gera relatório de análise."""
        
        successful = [r for r in results if r.get('success')]
        total_properties = sum(r.get('properties_found', 0) for r in results)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_sites_analyzed': len(results),
            'successful_sites': len(successful),
            'failed_sites': len(results) - len(successful),
            'total_properties_found': total_properties,
            'configs_created': len(saved_configs),
            'sites': [],
        }
        
        for result in results:
            site_info = {
                'name': result.get('name'),
                'website': result.get('website'),
                'success': result.get('success'),
                'properties_found': result.get('properties_found', 0),
                'sample_count': len(result.get('sample_properties', [])),
            }
            
            if result.get('error'):
                site_info['error'] = result.get('error')
            
            report['sites'].append(site_info)
        
        return report
    
    def save_report(self, report: Dict, output_file: str = "tier1_analysis_report.json"):
        """Salva relatório."""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Relatorio salvo em {output_file}")
        return output_file


def load_configs_from_site_analysis():
    """Carrega configurações do diretório site_analysis."""
    
    config_dir = 'site_analysis'
    if not os.path.exists(config_dir):
        logger.warning(f"Diretorio {config_dir} nao encontrado")
        return []
    
    configs = []
    for filename in sorted(os.listdir(config_dir)):
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
    print("TIER1 CONFIG GENERATOR")
    print("=" * 60)
    
    # Carregar configurações
    configs = load_configs_from_site_analysis()
    
    if not configs:
        print("Nenhuma configuracao encontrada em site_analysis/")
        return
    
    # Limitar a 5 sites
    configs = configs[:5]
    
    print(f"\nConfiguracoes para processar: {len(configs)}")
    for i, config in enumerate(configs, 1):
        print(f"  {i}. {config.get('name')} - {config.get('website')}")
    
    # Criar gerador
    generator = Tier1ConfigGenerator(timeout=30.0)
    
    print("\nIniciando analise...")
    print("(Este processo pode levar ~5 minutos)\n")
    
    # Processar
    results = await generator.process_batch(configs)
    
    # Salvar configurações
    saved_configs = generator.save_configs(results, configs)
    
    # Gerar relatório
    report = generator.generate_report(results, saved_configs)
    report_file = generator.save_report(report)
    
    # Relatório
    print("\n" + "=" * 60)
    print("RELATORIO FINAL")
    print("=" * 60)
    
    print(f"\nSites analisados: {report['total_sites_analyzed']}")
    print(f"Sites com sucesso: {report['successful_sites']}")
    print(f"Total de imoveis encontrados: {report['total_properties_found']}")
    print(f"Configuracoes criadas: {report['configs_created']}")
    
    print(f"\nImoveis por site:")
    for site in report['sites']:
        status = "OK" if site.get('success') else "FALHOU"
        print(f"  {site.get('name')}: {site.get('properties_found', 0)} imoveis ({status})")
    
    print(f"\nExemplos de dados extraidos:")
    for result in results[:3]:
        if result.get('success') and result.get('sample_properties'):
            print(f"\n  {result.get('name')}:")
            for i, sample in enumerate(result.get('sample_properties', [])[:2], 1):
                title = sample.get('title', 'N/A')[:60]
                price = sample.get('price', 'N/A')
                print(f"    {i}. {title}")
                if price != 'N/A':
                    print(f"       Preco: {price}")
    
    print(f"\nArquivos gerados:")
    print(f"  - {report_file}")
    print(f"  - app/configs/sites/*.json ({report['configs_created']} arquivos)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
