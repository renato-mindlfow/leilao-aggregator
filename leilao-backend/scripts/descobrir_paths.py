#!/usr/bin/env python3
"""Script para descobrir paths corretos dos sites com 0 imóveis"""
import asyncio, json, sys, codecs, logging
from pathlib import Path
from playwright.async_api import async_playwright
from urllib.parse import urlparse

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# TOP 15 SITES PARA INVESTIGAR (mais promissores)
SITES_INVESTIGAR = [
    "agenciadeleiloes.com.br",
    "bianchileiloes.com.br",
    "ckleiloes.com.br",
    "duxleiloes.com.br",
    "gtleiloes.com.br",
    "juleiloes.com.br",
    "leffaleiloes.com.br",
    "leiloesfederal.com.br",
    "marceloleiloeiro.com.br",
    "marquesbarretoleiloes.com.br",
    "michellileiloes.com.br",
    "pbcastro.com.br",
    "rangelleiloes.com.br",
    "renovarleiloes.com.br",
    "sold.com.br"
]

# Paths possíveis para testar
PATHS_TESTAR = [
    "/imoveis",
    "/leiloes",
    "/leilao",
    "/produtos",
    "/catalogo",
    "/imoveis-disponiveis",
    "/lotes",
    "/leiloes/imoveis",
    "/produtos/imoveis",
    "/busca",
    "/search",
    ""  # Homepage
]

# Palavras-chave para identificar links de imóveis
KEYWORDS_IMOVEIS = [
    "imovel", "imoveis", "imóvel", "imóveis",
    "leilao", "leilão", "leiloes", "leilões",
    "lote", "lotes", "produto", "produtos",
    "catalogo", "catálogo", "busca", "search"
]

async def descobrir_path_site(dominio: str, browser):
    """Descobre o path correto para um site"""
    url_base = f"https://www.{dominio}"
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🔍 Investigando: {dominio}")
    logger.info(f"{'='*60}")
    
    resultado = {
        "dominio": dominio,
        "url_base": url_base,
        "path_descoberto": None,
        "links_encontrados": 0,
        "metodo": None,
        "sucesso": False
    }
    
    try:
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})
        
        # MÉTODO 1: Testar paths conhecidos
        logger.info(f"📋 Método 1: Testando paths conhecidos...")
        for path in PATHS_TESTAR:
            url_teste = url_base + path
            try:
                response = await page.goto(url_teste, wait_until="domcontentloaded", timeout=10000)
                
                if response and response.status == 200:
                    await page.wait_for_timeout(2000)  # Aguarda JS
                    
                    # Procurar links relacionados a imóveis
                    links = await page.query_selector_all('a[href]')
                    links_imoveis = []
                    
                    for link in links[:200]:  # Limitar a 200 links
                        href = await link.get_attribute('href')
                        texto = await link.inner_text()
                        
                        if href and any(kw in href.lower() for kw in KEYWORDS_IMOVEIS):
                            links_imoveis.append(href)
                        elif texto and any(kw in texto.lower() for kw in KEYWORDS_IMOVEIS):
                            links_imoveis.append(href)
                    
                    if links_imoveis:
                        logger.info(f"   ✅ Path encontrado: {path}")
                        logger.info(f"   📊 Links de imóveis: {len(links_imoveis)}")
                        resultado["path_descoberto"] = path or "/"
                        resultado["links_encontrados"] = len(links_imoveis)
                        resultado["metodo"] = "paths_conhecidos"
                        resultado["sucesso"] = True
                        break
                        
            except Exception as e:
                logger.debug(f"   ❌ {path}: {str(e)[:50]}")
                continue
        
        # MÉTODO 2: Analisar menu de navegação na homepage
        if not resultado["sucesso"]:
            logger.info(f"📋 Método 2: Analisando menu de navegação...")
            try:
                await page.goto(url_base, wait_until="domcontentloaded", timeout=10000)
                await page.wait_for_timeout(2000)
                
                # Procurar links no menu/navegação
                nav_selectors = ['nav a', 'header a', '.menu a', '.navbar a', 'ul.menu a']
                for selector in nav_selectors:
                    try:
                        nav_links = await page.query_selector_all(selector)
                        for link in nav_links:
                            href = await link.get_attribute('href')
                            texto = await link.inner_text()
                            
                            if href and texto:
                                texto_lower = texto.lower()
                                if any(kw in texto_lower for kw in KEYWORDS_IMOVEIS):
                                    # Extrair path do href
                                    if href.startswith('http'):
                                        parsed = urlparse(href)
                                        path_encontrado = parsed.path
                                    else:
                                        path_encontrado = href
                                    
                                    logger.info(f"   ✅ Link no menu: '{texto}' → {path_encontrado}")
                                    resultado["path_descoberto"] = path_encontrado
                                    resultado["metodo"] = "menu_navegacao"
                                    resultado["sucesso"] = True
                                    break
                        
                        if resultado["sucesso"]:
                            break
                    except:
                        continue
                        
            except Exception as e:
                logger.warning(f"   ⚠️ Erro ao analisar menu: {str(e)[:100]}")
        
        # MÉTODO 3: Procurar formulário de busca
        if not resultado["sucesso"]:
            logger.info(f"📋 Método 3: Procurando formulário de busca...")
            try:
                search_selectors = [
                    'input[type="search"]',
                    'input[name*="search"]',
                    'input[placeholder*="busca"]',
                    'input[placeholder*="search"]'
                ]
                
                for selector in search_selectors:
                    try:
                        search_input = await page.query_selector(selector)
                        if search_input:
                            # Tentar obter a action do form
                            form = await page.query_selector(f'{selector}:has-parent(form)')
                            if form:
                                action = await form.get_attribute('action')
                                if action:
                                    logger.info(f"   ✅ Formulário de busca: {action}")
                                    resultado["path_descoberto"] = action
                                    resultado["metodo"] = "formulario_busca"
                                    resultado["sucesso"] = True
                                    break
                    except:
                        continue
                        
            except Exception as e:
                logger.warning(f"   ⚠️ Erro ao procurar busca: {str(e)[:100]}")
        
        await page.close()
        
        if not resultado["sucesso"]:
            logger.warning(f"   ❌ Nenhum path descoberto para {dominio}")
        
    except Exception as e:
        logger.error(f"   ❌ Erro geral: {str(e)[:200]}")
        resultado["erro"] = str(e)[:200]
    
    return resultado

async def main():
    logger.info(f"\n{'='*80}")
    logger.info(f"🔍 DESCOBERTA AUTOMÁTICA DE PATHS")
    logger.info(f"{'='*80}")
    logger.info(f"Sites a investigar: {len(SITES_INVESTIGAR)}")
    logger.info(f"Paths a testar: {len(PATHS_TESTAR)}")
    logger.info(f"Tempo estimado: ~{len(SITES_INVESTIGAR) * 1} minuto(s)\n")
    
    resultados = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for i, dominio in enumerate(SITES_INVESTIGAR, 1):
            logger.info(f"\n[{i}/{len(SITES_INVESTIGAR)}]")
            resultado = await descobrir_path_site(dominio, browser)
            resultados.append(resultado)
            
            # Pausa entre sites
            await asyncio.sleep(1)
        
        await browser.close()
    
    # Salvar resultados
    output_file = Path("logs/extracao_fase2/tier2/paths_descobertos.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": "2026-01-20",
            "total_sites": len(SITES_INVESTIGAR),
            "descobertos": sum(1 for r in resultados if r["sucesso"]),
            "resultados": resultados
        }, f, ensure_ascii=False, indent=2)
    
    # Criar mapeamento de paths
    mapeamento = {}
    for r in resultados:
        if r["sucesso"] and r["path_descoberto"]:
            mapeamento[r["dominio"]] = r["path_descoberto"]
    
    # Salvar mapeamento
    mapping_file = Path("config/paths_especificos.json")
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapeamento, f, ensure_ascii=False, indent=2)
    
    # Relatório final
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 RELATÓRIO FINAL")
    logger.info(f"{'='*80}")
    logger.info(f"Sites investigados: {len(SITES_INVESTIGAR)}")
    logger.info(f"Paths descobertos: {len(mapeamento)}")
    logger.info(f"Taxa de sucesso: {len(mapeamento)/len(SITES_INVESTIGAR)*100:.1f}%\n")
    
    if mapeamento:
        logger.info(f"✅ PATHS DESCOBERTOS:")
        for dominio, path in mapeamento.items():
            logger.info(f"   {dominio}: {path}")
    
    logger.info(f"\n📁 Arquivos salvos:")
    logger.info(f"   - {output_file}")
    logger.info(f"   - {mapping_file}")
    logger.info(f"\n{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())
