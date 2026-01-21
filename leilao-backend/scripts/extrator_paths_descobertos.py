#!/usr/bin/env python3
"""
EXTRATOR INTELIGENTE: Usa paths descobertos pela análise de HTML
Processa sites em lotes conforme paths são descobertos
"""

import asyncio
import json
import sys
import codecs
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "logs" / "extracao_paths_descobertos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def carregar_paths_descobertos():
    """Carrega paths já descobertos dos checkpoints"""
    descoberta_dir = BASE_DIR / "logs" / "descoberta_paths"
    
    if not descoberta_dir.exists():
        return []
    
    # Pegar o checkpoint mais recente
    checkpoints = sorted(descoberta_dir.glob("checkpoint_*.json"), 
                        key=lambda x: int(x.stem.split('_')[1]), 
                        reverse=True)
    
    if not checkpoints:
        return []
    
    checkpoint_file = checkpoints[0]
    logger.info(f"📋 Carregando checkpoint: {checkpoint_file.name}")
    
    with open(checkpoint_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filtrar apenas sites com sucesso
    sites_com_paths = [
        r for r in data.get('resultados', [])
        if r.get('sucesso') and r.get('path_descoberto')
    ]
    
    logger.info(f"✅ {len(sites_com_paths)} sites com paths descobertos")
    return sites_com_paths


async def extrair_com_http(site_info: Dict) -> Dict:
    """Tenta extração com HTTP simples"""
    url = site_info['url_completa_descoberta']
    nome = site_info['nome']
    
    logger.info(f"   🔄 HTTP: {url}")
    
    resultado = {
        'site_id': site_info['id'],
        'nome': nome,
        'url': url,
        'metodo': 'http',
        'sucesso': False,
        'imoveis': [],
        'total_imoveis': 0,
        'erro': None
    }
    
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Procurar cards/links de imóveis
                seletores = [
                    'a[href*="/imovel"]',
                    'a[href*="/lote"]',
                    'a[href*="/produto"]',
                    '.card a[href]',
                    '.property a[href]',
                    'article a[href]'
                ]
                
                links_encontrados = set()
                for seletor in seletores:
                    cards = soup.select(seletor)
                    for card in cards[:200]:
                        href = card.get('href')
                        if href and not any(x in href.lower() for x in ['javascript:', 'mailto:', '#']):
                            links_encontrados.add(href)
                
                if links_encontrados:
                    resultado['imoveis'] = list(links_encontrados)
                    resultado['total_imoveis'] = len(links_encontrados)
                    resultado['sucesso'] = True
                    logger.info(f"   ✅ HTTP: {len(links_encontrados)} imóveis encontrados")
                else:
                    resultado['erro'] = "Nenhum imóvel encontrado no HTML"
            else:
                resultado['erro'] = f"HTTP {response.status_code}"
                
    except Exception as e:
        resultado['erro'] = str(e)[:200]
        logger.warning(f"   ⚠️ HTTP falhou: {str(e)[:100]}")
    
    return resultado


async def extrair_com_playwright(site_info: Dict, browser) -> Dict:
    """Extração com Playwright (para sites com JS)"""
    url = site_info['url_completa_descoberta']
    nome = site_info['nome']
    
    logger.info(f"   🔄 Playwright: {url}")
    
    resultado = {
        'site_id': site_info['id'],
        'nome': nome,
        'url': url,
        'metodo': 'playwright',
        'sucesso': False,
        'imoveis': [],
        'total_imoveis': 0,
        'erro': None
    }
    
    try:
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Scroll para carregar conteúdo
        for _ in range(3):
            await page.evaluate('window.scrollBy(0, window.innerHeight)')
            await page.wait_for_timeout(500)
        
        # Extrair links
        links = await page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            return links
                .map(a => a.href)
                .filter(href => 
                    href && 
                    !href.includes('javascript:') && 
                    !href.includes('mailto:') &&
                    !href.includes('#') &&
                    (href.includes('/imovel') || 
                     href.includes('/lote') || 
                     href.includes('/produto') ||
                     href.includes('/item'))
                );
        }''')
        
        links_unicos = list(set(links))
        
        await context.close()
        
        if links_unicos:
            resultado['imoveis'] = links_unicos
            resultado['total_imoveis'] = len(links_unicos)
            resultado['sucesso'] = True
            logger.info(f"   ✅ Playwright: {len(links_unicos)} imóveis encontrados")
        else:
            resultado['erro'] = "Nenhum imóvel encontrado"
            
    except Exception as e:
        resultado['erro'] = str(e)[:200]
        logger.warning(f"   ⚠️ Playwright falhou: {str(e)[:100]}")
    
    return resultado


async def processar_site(site_info: Dict, browser) -> Dict:
    """Processa um site: tenta HTTP primeiro, depois Playwright"""
    nome = site_info['nome']
    url = site_info['url_completa_descoberta']
    
    logger.info(f"\n{'='*70}")
    logger.info(f"🎯 {nome}")
    logger.info(f"🌐 {url}")
    logger.info(f"{'='*70}")
    
    # TIER 1: HTTP simples (mais rápido)
    resultado_http = await extrair_com_http(site_info)
    
    if resultado_http['sucesso'] and resultado_http['total_imoveis'] > 0:
        return resultado_http
    
    # TIER 2: Playwright (se HTTP falhou)
    logger.info(f"   ℹ️ HTTP não encontrou imóveis, tentando Playwright...")
    resultado_playwright = await extrair_com_playwright(site_info, browser)
    
    if resultado_playwright['sucesso'] and resultado_playwright['total_imoveis'] > 0:
        return resultado_playwright
    
    # Retornar o resultado HTTP mesmo se falhou (para registrar)
    return resultado_http


async def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     🚀 EXTRAÇÃO COM PATHS DESCOBERTOS (INTELIGENTE)        ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Usa paths reais encontrados pela análise de HTML           ║
    ║  Processa em lotes conforme descoberta avança               ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    inicio = datetime.now()
    
    # Carregar sites com paths descobertos
    sites_processar = carregar_paths_descobertos()
    
    if not sites_processar:
        logger.warning("❌ Nenhum path descoberto ainda. Aguarde a descoberta processar alguns sites.")
        return
    
    logger.info(f"\n🎯 Processando {len(sites_processar)} sites com paths descobertos\n")
    
    resultados = []
    sucessos = 0
    falhas = 0
    total_imoveis = 0
    
    # Iniciar Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for i, site in enumerate(sites_processar, 1):
            print(f"\n[{i}/{len(sites_processar)}]")
            
            resultado = await processar_site(site, browser)
            resultados.append(resultado)
            
            if resultado['sucesso']:
                sucessos += 1
                total_imoveis += resultado['total_imoveis']
                print(f"✅ SUCESSO: {resultado['total_imoveis']} imóveis")
            else:
                falhas += 1
                print(f"❌ FALHA: {resultado.get('erro', 'Desconhecido')}")
            
            # Pausa entre sites
            await asyncio.sleep(2)
        
        await browser.close()
    
    fim = datetime.now()
    duracao = (fim - inicio).total_seconds()
    
    # Salvar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = OUTPUT_DIR / f"extracao_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'duracao_segundos': duracao,
            'total_sites': len(sites_processar),
            'sucessos': sucessos,
            'falhas': falhas,
            'total_imoveis': total_imoveis,
            'taxa_sucesso': f"{sucessos/len(sites_processar)*100:.1f}%",
            'resultados': resultados
        }, f, ensure_ascii=False, indent=2)
    
    # Relatório final
    print(f"\n{'='*70}")
    print("📊 RELATÓRIO FINAL - EXTRAÇÃO COM PATHS DESCOBERTOS")
    print(f"{'='*70}")
    print(f"Sites processados:    {len(sites_processar)}")
    print(f"Sucessos:             {sucessos} ({sucessos/len(sites_processar)*100:.1f}%)")
    print(f"Falhas:               {falhas}")
    print(f"Total de imóveis:     {total_imoveis:,}")
    print(f"Média por sucesso:    {total_imoveis/sucessos:.1f}" if sucessos > 0 else "N/A")
    print(f"Duração:              {duracao//60:.0f}m {duracao%60:.0f}s")
    print(f"\n📁 Resultados salvos: {output_file}")
    print(f"{'='*70}\n")
    
    # Mostrar top sites
    if sucessos > 0:
        print("🏆 TOP SITES POR IMÓVEIS:")
        top_sites = sorted(
            [r for r in resultados if r['sucesso']], 
            key=lambda x: x['total_imoveis'], 
            reverse=True
        )[:5]
        
        for i, site in enumerate(top_sites, 1):
            print(f"  {i}. {site['nome']}: {site['total_imoveis']} imóveis")
        print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        sys.exit(1)
