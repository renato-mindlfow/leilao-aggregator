#!/usr/bin/env python3
"""
Descoberta massiva de paths para os 261 leiloeiros
Usa análise inteligente de HTML para encontrar onde estão os imóveis
"""
import asyncio
import json
import sys
import csv
import codecs
import logging
from pathlib import Path
from playwright.async_api import async_playwright
from urllib.parse import urlparse
from datetime import datetime

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent

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
    "/catalogo/imoveis",
    "/categoria/imoveis",
    "/tipo/imoveis",
    ""  # Homepage
]

# Palavras-chave para identificar links de imóveis
KEYWORDS_IMOVEIS = [
    "imovel", "imoveis", "imóvel", "imóveis",
    "leilao", "leilão", "leiloes", "leilões",
    "lote", "lotes", "produto", "produtos",
    "catalogo", "catálogo", "busca", "search",
    "propriedade", "casa", "apartamento"
]

def carregar_sites_csv():
    """Carrega sites do CSV que precisam de descoberta"""
    csv_path = BASE_DIR / "LISTA_MESTRE_LEILOEIROS.csv"
    
    sites_processar = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get('scrape_status', '').strip().lower()
            # Processar: pending, error
            if status in ['pending', 'error']:
                sites_processar.append({
                    'id': row.get('id'),
                    'name': row.get('name'),
                    'website': row.get('website'),
                    'status': status
                })
    
    return sites_processar

def extrair_dominio(url):
    """Extrai domínio de URL"""
    parsed = urlparse(url)
    dominio = parsed.netloc or parsed.path
    dominio = dominio.replace('www.', '')
    return dominio

async def descobrir_path_site(site_info, browser):
    """Descobre o path correto para um site usando 3 métodos"""
    site_id = site_info['id']
    nome = site_info['name']
    url_completa = site_info['website']
    dominio = extrair_dominio(url_completa)
    url_base = f"https://www.{dominio}"
    
    resultado = {
        "id": site_id,
        "nome": nome,
        "dominio": dominio,
        "url_base": url_base,
        "url_original": url_completa,
        "path_descoberto": None,
        "url_completa_descoberta": None,
        "links_encontrados": 0,
        "metodo": None,
        "sucesso": False,
        "erro": None
    }
    
    try:
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # MÉTODO 1: Testar paths conhecidos
        logger.info(f"   📋 Método 1: Testando {len(PATHS_TESTAR)} paths conhecidos...")
        for path in PATHS_TESTAR:
            url_teste = url_base + path
            try:
                response = await page.goto(url_teste, wait_until="domcontentloaded", timeout=15000)
                
                if response and response.status == 200:
                    await page.wait_for_timeout(2000)
                    
                    # Procurar links relacionados a imóveis
                    links = await page.query_selector_all('a[href]')
                    links_imoveis = []
                    
                    for link in links[:150]:
                        try:
                            href = await link.get_attribute('href')
                            texto = (await link.inner_text()).strip() if await link.inner_text() else ""
                            
                            if href:
                                href_lower = href.lower()
                                texto_lower = texto.lower()
                                
                                # Verificar se link é sobre imóveis
                                if any(kw in href_lower for kw in KEYWORDS_IMOVEIS):
                                    links_imoveis.append((href, texto))
                                elif any(kw in texto_lower for kw in KEYWORDS_IMOVEIS):
                                    links_imoveis.append((href, texto))
                        except:
                            continue
                    
                    if len(links_imoveis) >= 3:  # Pelo menos 3 links de imóveis
                        logger.info(f"   ✅ Path encontrado: {path} ({len(links_imoveis)} links)")
                        resultado["path_descoberto"] = path or "/"
                        resultado["url_completa_descoberta"] = url_teste
                        resultado["links_encontrados"] = len(links_imoveis)
                        resultado["metodo"] = "paths_conhecidos"
                        resultado["sucesso"] = True
                        break
                        
            except Exception as e:
                logger.debug(f"   ⚠️ {path}: {str(e)[:50]}")
                continue
        
        # MÉTODO 2: Analisar menu de navegação
        if not resultado["sucesso"]:
            logger.info(f"   📋 Método 2: Analisando menu...")
            try:
                await page.goto(url_base, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)
                
                nav_selectors = [
                    'nav a', 'header a', '.menu a', '.navbar a', 
                    'ul.menu a', '.navigation a', '#menu a'
                ]
                
                for selector in nav_selectors:
                    try:
                        nav_links = await page.query_selector_all(selector)
                        for link in nav_links[:50]:
                            href = await link.get_attribute('href')
                            texto = (await link.inner_text()).strip() if await link.inner_text() else ""
                            
                            if href and texto:
                                texto_lower = texto.lower()
                                if any(kw in texto_lower for kw in KEYWORDS_IMOVEIS):
                                    # Extrair path
                                    if href.startswith('http'):
                                        parsed = urlparse(href)
                                        path_encontrado = parsed.path
                                    else:
                                        path_encontrado = href
                                    
                                    logger.info(f"   ✅ Menu: '{texto}' → {path_encontrado}")
                                    resultado["path_descoberto"] = path_encontrado
                                    resultado["url_completa_descoberta"] = url_base + path_encontrado
                                    resultado["metodo"] = "menu_navegacao"
                                    resultado["sucesso"] = True
                                    break
                        
                        if resultado["sucesso"]:
                            break
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"   ⚠️ Erro menu: {str(e)[:100]}")
        
        # MÉTODO 3: Buscar "Ver todos", "Catálogo", etc
        if not resultado["sucesso"]:
            logger.info(f"   📋 Método 3: Procurando botões de catálogo...")
            try:
                # Procurar botões/links comuns
                botoes_buscar = [
                    'a:has-text("Ver todos")',
                    'a:has-text("Catálogo")',
                    'a:has-text("Imóveis")',
                    'a:has-text("Leilões")',
                    'a:has-text("Produtos")',
                    'button:has-text("Buscar")'
                ]
                
                for seletor in botoes_buscar:
                    try:
                        botao = await page.query_selector(seletor)
                        if botao:
                            href = await botao.get_attribute('href')
                            if href:
                                if href.startswith('http'):
                                    parsed = urlparse(href)
                                    path_encontrado = parsed.path
                                else:
                                    path_encontrado = href
                                
                                logger.info(f"   ✅ Botão encontrado → {path_encontrado}")
                                resultado["path_descoberto"] = path_encontrado
                                resultado["url_completa_descoberta"] = url_base + path_encontrado
                                resultado["metodo"] = "botao_catalogo"
                                resultado["sucesso"] = True
                                break
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"   ⚠️ Erro botões: {str(e)[:100]}")
        
        await context.close()
        
        if not resultado["sucesso"]:
            logger.warning(f"   ❌ Nenhum path descoberto")
            resultado["erro"] = "Nenhum path válido encontrado"
        
    except Exception as e:
        logger.error(f"   ❌ Erro: {str(e)[:150]}")
        resultado["erro"] = str(e)[:200]
    
    return resultado

async def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║      🔍 DESCOBERTA MASSIVA DE PATHS - 261 LEILOEIROS       ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Estratégia inteligente: Análise de HTML real               ║
    ║  3 métodos: Paths conhecidos + Menu + Botões                ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    inicio = datetime.now()
    
    # Carregar sites
    logger.info("📋 Carregando sites do CSV...")
    sites = carregar_sites_csv()
    logger.info(f"✅ {len(sites)} sites para processar\n")
    
    # Criar diretório de output
    output_dir = BASE_DIR / "logs" / "descoberta_paths"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    resultados = []
    descobertos = 0
    falhas = 0
    
    async with async_playwright() as p:
        logger.info("🚀 Iniciando navegador...\n")
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        for i, site in enumerate(sites, 1):
            print(f"\n{'='*70}")
            print(f"[{i}/{len(sites)}] {site['name']}")
            print(f"🌐 {site['website']}")
            print(f"{'='*70}")
            
            resultado = await descobrir_path_site(site, browser)
            resultados.append(resultado)
            
            if resultado["sucesso"]:
                descobertos += 1
                print(f"✅ SUCESSO: {resultado['path_descoberto']}")
                print(f"   Método: {resultado['metodo']}")
                print(f"   Links encontrados: {resultado['links_encontrados']}")
            else:
                falhas += 1
                print(f"❌ FALHA: {resultado.get('erro', 'Desconhecido')}")
            
            # Salvar checkpoint a cada 10 sites
            if i % 10 == 0:
                checkpoint_file = output_dir / f"checkpoint_{i}.json"
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "processados": i,
                        "descobertos": descobertos,
                        "falhas": falhas,
                        "resultados": resultados
                    }, f, ensure_ascii=False, indent=2)
                logger.info(f"💾 Checkpoint salvo: {checkpoint_file.name}")
            
            # Pausa entre sites
            await asyncio.sleep(1)
        
        await browser.close()
    
    fim = datetime.now()
    duracao = (fim - inicio).total_seconds()
    
    # Salvar resultados finais
    output_file = output_dir / f"paths_descobertos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "duracao_segundos": duracao,
            "total_sites": len(sites),
            "descobertos": descobertos,
            "falhas": falhas,
            "taxa_sucesso": f"{descobertos/len(sites)*100:.1f}%",
            "resultados": resultados
        }, f, ensure_ascii=False, indent=2)
    
    # Criar mapeamento de paths para uso no ataque massivo
    mapeamento = {}
    for r in resultados:
        if r["sucesso"] and r["path_descoberto"]:
            mapeamento[r["dominio"]] = {
                "path": r["path_descoberto"],
                "url_completa": r["url_completa_descoberta"],
                "metodo": r["metodo"],
                "links": r["links_encontrados"]
            }
    
    mapping_file = BASE_DIR / "config" / "paths_descobertos_massivo.json"
    mapping_file.parent.mkdir(parents=True, exist_ok=True)
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapeamento, f, ensure_ascii=False, indent=2)
    
    # Relatório final
    print(f"\n{'='*70}")
    print("📊 RELATÓRIO FINAL - DESCOBERTA DE PATHS")
    print(f"{'='*70}")
    print(f"Sites processados:    {len(sites)}")
    print(f"Paths descobertos:    {descobertos} ({descobertos/len(sites)*100:.1f}%)")
    print(f"Falhas:               {falhas} ({falhas/len(sites)*100:.1f}%)")
    print(f"Duração:              {duracao//60:.0f}m {duracao%60:.0f}s")
    print(f"\n📁 Arquivos salvos:")
    print(f"   • {output_file}")
    print(f"   • {mapping_file}")
    
    if descobertos > 0:
        print(f"\n✅ TOP 10 PATHS DESCOBERTOS:")
        for i, (dominio, info) in enumerate(list(mapeamento.items())[:10], 1):
            print(f"   {i}. {dominio}")
            print(f"      → {info['path']} ({info['metodo']})")
    
    print(f"\n{'='*70}\n")
    print("🎯 Próximo passo: Executar ataque massivo com paths descobertos")
    print("   python scripts/executar_ataque_massivo_v2.py")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        sys.exit(1)
