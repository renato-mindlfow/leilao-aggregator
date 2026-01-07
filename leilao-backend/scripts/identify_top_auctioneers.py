#!/usr/bin/env python3
"""
IDENTIFICA OS MAIORES LEILOEIROS COM ESTRUTURA_MUDOU
Analisa cada site e estima quantidade de imóveis disponíveis.
"""

import os
import json
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Tuple
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# URLs comuns de listagem de imóveis
LISTING_PATHS = [
    '/imoveis',
    '/leiloes',
    '/leilao',
    '/leiloes-de-imoveis',
    '/leilao-de-imoveis',
    '/catalogo',
    '/busca',
    '/oportunidades',
    '/disponiveis',
]

async def find_listing_url(client: httpx.AsyncClient, base_url: str) -> Tuple[str, str]:
    """Encontra URL de listagem de imóveis."""
    # Tentar URL base primeiro
    try:
        response = await client.get(base_url, timeout=15.0)
        if response.status_code == 200:
            html = response.text.lower()
            if any(x in html for x in ['apartamento', 'casa', 'terreno', 'imóvel', 'imovel', 'lote']):
                return base_url, response.text
    except:
        pass
    
    # Tentar paths comuns
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    
    for path in LISTING_PATHS:
        try:
            url = base + path
            response = await client.get(url, timeout=10.0)
            if response.status_code == 200:
                html = response.text.lower()
                if any(x in html for x in ['apartamento', 'casa', 'terreno', 'imóvel', 'imovel']):
                    return url, response.text
        except:
            continue
    
    return base_url, ""

def estimate_properties(html: str) -> Tuple[int, List[str]]:
    """Estima quantidade de propriedades e identifica seletores."""
    if not html:
        return 0, []
    
    soup = BeautifulSoup(html, 'html.parser')
    found_selectors = []
    max_count = 0
    
    # Seletores comuns para cards de imóveis
    selectors = [
        ('div[class*="imovel"]', 'div.imovel'),
        ('div[class*="property"]', 'div.property'),
        ('div[class*="lote"]', 'div.lote'),
        ('div[class*="card"]', 'div.card'),
        ('article', 'article'),
        ('div[class*="item"]', 'div.item'),
        ('li[class*="item"]', 'li.item'),
        ('div[class*="auction"]', 'div.auction'),
        ('div[class*="produto"]', 'div.produto'),
    ]
    
    for selector, name in selectors:
        try:
            items = soup.select(selector)
            count = len(items)
            if count > 0:
                # Verificar se parecem ser imóveis
                text = ' '.join([i.get_text()[:200] for i in items[:3]])
                if any(x in text.lower() for x in ['r$', 'apartamento', 'casa', 'terreno', 'lote', 'imóvel']):
                    if count > max_count:
                        max_count = count
                    found_selectors.append(f"{name}: {count}")
        except:
            continue
    
    # Procurar indicadores textuais de quantidade
    text = soup.get_text()
    patterns = [
        r'(\d+)\s*(?:imóve[il]s?|lotes?|resultados?|encontrados?)',
        r'(?:total|mostrando)[\s:]+(\d+)',
        r'página\s+\d+\s+de\s+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            num = int(match.group(1))
            if num > max_count:
                max_count = num
    
    return max_count, found_selectors

async def analyze_auctioneer(client: httpx.AsyncClient, auctioneer: Dict) -> Dict:
    """Analisa um leiloeiro e retorna informações detalhadas."""
    
    result = {
        "id": auctioneer.get("id"),
        "name": auctioneer.get("name"),
        "website": auctioneer.get("website"),
        "listing_url": None,
        "estimated_properties": 0,
        "found_selectors": [],
        "status": "unknown",
        "has_pagination": False,
        "technology": "unknown",
    }
    
    website = auctioneer.get("website", "")
    if not website:
        result["status"] = "no_website"
        return result
    
    if not website.startswith("http"):
        website = "https://" + website
    
    try:
        # Encontrar URL de listagem
        listing_url, html = await find_listing_url(client, website)
        result["listing_url"] = listing_url
        
        if not html:
            result["status"] = "no_content"
            return result
        
        # Estimar propriedades
        count, selectors = estimate_properties(html)
        result["estimated_properties"] = count
        result["found_selectors"] = selectors
        
        # Detectar tecnologia
        html_lower = html.lower()
        if 'react' in html_lower or '__next' in html_lower:
            result["technology"] = "React/Next.js"
        elif 'vue' in html_lower or '__vue__' in html_lower:
            result["technology"] = "Vue.js"
        elif 'angular' in html_lower:
            result["technology"] = "Angular"
        elif 'wordpress' in html_lower or 'wp-content' in html_lower:
            result["technology"] = "WordPress"
        else:
            result["technology"] = "Traditional"
        
        # Detectar paginação
        soup = BeautifulSoup(html, 'html.parser')
        pagination_indicators = soup.select('nav.pagination, .pagination, [class*="paging"], a[href*="page="], a[href*="pagina"]')
        result["has_pagination"] = len(pagination_indicators) > 0
        
        result["status"] = "success" if count > 0 else "no_properties"
        
    except Exception as e:
        result["status"] = f"error: {str(e)[:50]}"
    
    return result

async def main():
    """Analisa todos os leiloeiros com ESTRUTURA_MUDOU."""
    
    logger.info("=" * 70)
    logger.info("IDENTIFICAÇÃO DOS MAIORES LEILOEIROS")
    logger.info("=" * 70)
    
    # Carregar análise anterior
    script_dir = os.path.dirname(os.path.abspath(__file__))
    analysis_files = [f for f in os.listdir(script_dir) if f.startswith('analise_leiloeiros_') and f.endswith('.json')]
    
    if not analysis_files:
        logger.error("Arquivo de análise não encontrado. Execute deep_auctioneer_analysis.py primeiro.")
        return
    
    latest = max(analysis_files)
    logger.info(f"Usando análise: {latest}")
    
    with open(os.path.join(script_dir, latest), 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    # Filtrar ESTRUTURA_MUDOU
    estrutura_mudou = [a for a in analysis if a.get('diagnosis') == 'ESTRUTURA_MUDOU']
    logger.info(f"Total com ESTRUTURA_MUDOU: {len(estrutura_mudou)}")
    
    # Analisar cada um
    results = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9',
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20.0) as client:
        for i, auc in enumerate(estrutura_mudou):
            name = auc.get('name', 'N/A')
            logger.info(f"[{i+1}/{len(estrutura_mudou)}] Analisando: {name}")
            
            result = await analyze_auctioneer(client, auc)
            results.append(result)
            
            if result["estimated_properties"] > 0:
                logger.info(f"  ✅ ~{result['estimated_properties']} imóveis | {result['technology']} | Seletores: {len(result['found_selectors'])}")
            else:
                logger.info(f"  ⚠️ Nenhum imóvel detectado | Status: {result['status']}")
            
            await asyncio.sleep(0.5)  # Rate limiting
    
    # Ordenar por quantidade estimada
    results.sort(key=lambda x: x['estimated_properties'], reverse=True)
    
    # Salvar resultado completo
    output_file = os.path.join(script_dir, f"top_auctioneers_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\nResultados salvos em: {output_file}")
    
    # Mostrar TOP 20
    logger.info("\n" + "=" * 70)
    logger.info("TOP 20 LEILOEIROS PARA CRIAR SCRAPERS ESPECÍFICOS")
    logger.info("=" * 70)
    
    top20 = [r for r in results if r['estimated_properties'] > 0][:20]
    
    for i, r in enumerate(top20):
        logger.info(f"\n{i+1}. {r['name']}")
        logger.info(f"   URL: {r['listing_url']}")
        logger.info(f"   Imóveis: ~{r['estimated_properties']}")
        logger.info(f"   Tecnologia: {r['technology']}")
        logger.info(f"   Seletores: {', '.join(r['found_selectors'][:3])}")
        logger.info(f"   Paginação: {'Sim' if r['has_pagination'] else 'Não'}")
    
    # Estatísticas
    with_properties = len([r for r in results if r['estimated_properties'] > 0])
    total_estimated = sum(r['estimated_properties'] for r in results)
    
    logger.info("\n" + "=" * 70)
    logger.info("ESTATÍSTICAS")
    logger.info("=" * 70)
    logger.info(f"Leiloeiros analisados: {len(results)}")
    logger.info(f"Com imóveis detectados: {with_properties}")
    logger.info(f"Total estimado de imóveis: {total_estimated}")
    
    # Tecnologia mais comum
    tech_counts = {}
    for r in results:
        tech = r['technology']
        tech_counts[tech] = tech_counts.get(tech, 0) + 1
    most_common_tech = max(tech_counts.items(), key=lambda x: x[1])[0] if tech_counts else "N/A"
    logger.info(f"Tecnologia mais comum: {most_common_tech}")
    
    # Gerar relatório markdown
    report = f"""# TOP LEILOEIROS PARA SCRAPERS ESPECÍFICOS

**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Total Analisado:** {len(results)}
**Com Imóveis:** {with_properties}

## TOP 20 Priorizados

| # | Leiloeiro | Imóveis | Tecnologia | Paginação |
|---|-----------|---------|------------|-----------|
"""
    
    for i, r in enumerate(top20):
        pag = "✅" if r['has_pagination'] else "❌"
        report += f"| {i+1} | {r['name']} | ~{r['estimated_properties']} | {r['technology']} | {pag} |\n"
    
    report += f"""
## Próximos Passos

1. Criar scrapers específicos para os TOP 5-10
2. Usar seletores identificados como base
3. Implementar paginação quando disponível
4. Para sites React/Vue, considerar usar Playwright

## Seletores Mais Comuns

"""
    
    # Contar seletores
    from collections import Counter
    all_selectors = []
    for r in results:
        all_selectors.extend(r['found_selectors'])
    
    selector_counts = Counter(all_selectors)
    for sel, count in selector_counts.most_common(10):
        report += f"- `{sel}`: {count} sites\n"
    
    report_file = os.path.join(script_dir, f"RELATORIO_TOP_LEILOEIROS_{datetime.now().strftime('%Y%m%d')}.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"\nRelatório salvo em: {report_file}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())

