# ============================================================
# VALIDAÇÃO VISUAL DOS TOP 10 LEILOEIROS COM WEB BROWSER
# ============================================================
"""
Script para validação visual dos principais leiloeiros.
Acessa cada site, identifica seção de imóveis, conta quantidade real,
e mapeia seletores CSS.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict

# Sites para validar
SITES = [
    {
        "id": "leje",
        "name": "LEJE",
        "url": "https://www.lfranca.lel.br",
        "url_alternativa": "https://lfranca.lel.br",
    },
    {
        "id": "lancetotal",
        "name": "Lancetotal",
        "url": "https://www.lancetotal.com.br",
    },
    {
        "id": "megaleiloes",
        "name": "Mega Leilões",
        "url": "https://www.megaleiloes.com.br",
        "url_imoveis": "https://www.megaleiloes.com.br/imoveis",
    },
    {
        "id": "jacleiloes",
        "name": "JacLeilões",
        "url": "https://www.jacleiloes.com.br",
    },
    {
        "id": "lancenoleilao",
        "name": "Lance no Leilão",
        "url": "https://www.lancenoleilao.com.br",
    },
    {
        "id": "sodresantoro",
        "name": "Sodré Santoro",
        "url": "https://www.sodresantoro.com.br",
        "url_imoveis": "https://www.sodresantoro.com.br/imoveis",
    },
]

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
"""


@dataclass
class ValidacaoResult:
    """Resultado da validação de um site."""
    site_id: str
    site_name: str
    url_base: str
    url_imoveis: Optional[str] = None
    quantidade_real: int = 0
    tem_filtro_categoria: bool = False
    seletores_css: List[str] = None
    paginacao_tipo: Optional[str] = None
    paginacao_param: Optional[str] = None
    cards_encontrados: int = 0
    links_imoveis: List[str] = None
    erro: Optional[str] = None
    screenshot_path: Optional[str] = None
    observacoes: str = ""
    
    def __post_init__(self):
        if self.seletores_css is None:
            self.seletores_css = []
        if self.links_imoveis is None:
            self.links_imoveis = []


async def validar_site(site: Dict) -> ValidacaoResult:
    """Valida um site visualmente."""
    
    result = ValidacaoResult(
        site_id=site["id"],
        site_name=site["name"],
        url_base=site["url"],
    )
    
    print(f"\n{'='*70}")
    print(f"VALIDANDO: {site['name']}")
    print(f"URL: {site['url']}")
    print(f"{'='*70}")
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Modo visível para validação visual
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
            )
            
            await context.add_init_script(STEALTH_SCRIPT)
            page = await context.new_page()
            
            # Tentar acessar URL base
            try:
                print(f"   [1] Acessando URL base...")
                response = await page.goto(site["url"], wait_until='domcontentloaded', timeout=30000)
                
                if not response or response.status != 200:
                    # Tentar URL alternativa se disponível
                    if "url_alternativa" in site:
                        print(f"   [1] Tentando URL alternativa...")
                        response = await page.goto(site["url_alternativa"], wait_until='domcontentloaded', timeout=30000)
                    
                    if not response or response.status != 200:
                        result.erro = f"HTTP {response.status if response else 'N/A'}"
                        await browser.close()
                        return result
            except Exception as e:
                result.erro = f"Erro ao acessar: {str(e)[:100]}"
                await browser.close()
                return result
            
            # Aguardar carregamento
            await asyncio.sleep(3)
            
            # Tirar screenshot da página inicial
            screenshot_dir = Path("validacao_screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            screenshot_path = screenshot_dir / f"{site['id']}_homepage.png"
            try:
                await page.screenshot(path=str(screenshot_path), full_page=True, timeout=15000)
                result.screenshot_path = str(screenshot_path)
                print(f"   [2] Screenshot salvo: {screenshot_path}")
            except Exception as e:
                print(f"   [2] Erro ao tirar screenshot: {str(e)[:50]}")
                try:
                    await page.screenshot(path=str(screenshot_path), timeout=5000)
                    result.screenshot_path = str(screenshot_path)
                except:
                    pass
            
            # Analisar estrutura da página
            html = await page.content()
            text = await page.evaluate("() => document.body.innerText")
            
            # Procurar por links/menus de "Imóveis"
            print(f"   [3] Procurando seção de imóveis...")
            
            # Padrões comuns para links de imóveis
            imoveis_patterns = [
                r'href=["\']([^"\']*imove[il][^"\']*)["\']',
                r'href=["\']([^"\']*imovel[^"\']*)["\']',
                r'href=["\']([^"\']*propriedade[^"\']*)["\']',
            ]
            
            imoveis_links = set()
            for pattern in imoveis_patterns:
                matches = re.findall(pattern, html, re.I)
                for match in matches:
                    full_url = urljoin(site["url"], match)
                    imoveis_links.add(full_url)
            
            # Procurar no texto por "Imóveis"
            if "imóveis" in text.lower() or "imoveis" in text.lower():
                print(f"      [OK] Encontrado texto 'imoveis' na pagina")
            
            # Verificar se há URL de imóveis pré-configurada
            url_imoveis = site.get("url_imoveis")
            
            # Se não encontrou link específico, tentar padrões comuns
            if not url_imoveis and imoveis_links:
                # Priorizar URLs que contenham "imovel" ou "imoveis"
                for link in imoveis_links:
                    if "imovel" in link.lower() or "imoveis" in link.lower():
                        url_imoveis = link
                        break
                
                if not url_imoveis:
                    url_imoveis = list(imoveis_links)[0] if imoveis_links else None
            
            # Tentar acessar URLs comuns de imóveis diretamente
            urls_comuns_imoveis = [
                "/imoveis",
                "/imovel",
                "/leiloes/imoveis",
                "/categoria/imoveis",
                "/busca?categoria=imoveis",
                "/produtos?tipo=imovel",
            ]
            
            # Se não encontrou URL específica, tentar URLs comuns
            if not url_imoveis:
                for url_comum in urls_comuns_imoveis:
                    test_url = urljoin(site["url"], url_comum)
                    try:
                        # Testar se a URL existe (fazer requisição HEAD)
                        test_response = await page.goto(test_url, wait_until='domcontentloaded', timeout=10000)
                        if test_response and test_response.status == 200:
                            # Verificar se a página tem conteúdo de imóveis
                            test_text = await page.evaluate("() => document.body.innerText")
                            if "imóvel" in test_text.lower() or "imovel" in test_text.lower() or \
                               any(word in test_text.lower() for word in ["casa", "apartamento", "terreno", "r$"]):
                                url_imoveis = test_url
                                print(f"      [OK] URL de imoveis encontrada: {url_imoveis}")
                                break
                        # Voltar para página inicial
                        await page.goto(site["url"], wait_until='domcontentloaded', timeout=10000)
                        await asyncio.sleep(1)
                    except:
                        continue
            
            # Verificar se há URL de imóveis pré-configurada
            url_imoveis = site.get("url_imoveis")
            
            # Se não encontrou link específico, tentar padrões comuns
            if not url_imoveis and imoveis_links:
                # Priorizar URLs que contenham "imovel" ou "imoveis"
                for link in imoveis_links:
                    if "imovel" in link.lower() or "imoveis" in link.lower():
                        url_imoveis = link
                        break
                
                if not url_imoveis:
                    url_imoveis = list(imoveis_links)[0] if imoveis_links else None
            
            # Se ainda não encontrou, usar URL pré-configurada ou tentar padrões conhecidos
            if not url_imoveis:
                # Para Mega Leilões e Sodré Santoro, usar URLs conhecidas
                if site["id"] == "megaleiloes":
                    url_imoveis = "https://www.megaleiloes.com.br/imoveis"
                elif site["id"] == "sodresantoro":
                    url_imoveis = "https://www.sodresantoro.com.br/imoveis"
                else:
                    # Tentar padrão comum /imoveis como último recurso
                    url_imoveis = urljoin(site["url"], "/imoveis")
            
            # Tentar acessar página de imóveis
            if url_imoveis:
                result.url_imoveis = url_imoveis
                print(f"   [4] Acessando pagina de imoveis: {url_imoveis}")
                
                try:
                    await page.goto(url_imoveis, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(5)  # Aguardar carregamento
                    
                    # Screenshot da página de imóveis
                    screenshot_imoveis = screenshot_dir / f"{site['id']}_imoveis.png"
                    await page.screenshot(path=str(screenshot_imoveis), full_page=True)
                    print(f"      Screenshot salvo: {screenshot_imoveis}")
                    
                    # Analisar página de imóveis
                    html_imoveis = await page.content()
                    
                    # Procurar por filtros de categoria
                    filtro_patterns = [
                        r'<select[^>]*categoria[^>]*>',
                        r'<select[^>]*tipo[^>]*>',
                        r'<button[^>]*imovel[^>]*>',
                        r'<a[^>]*filtro[^>]*>',
                    ]
                    
                    tem_filtro = False
                    for pattern in filtro_patterns:
                        if re.search(pattern, html_imoveis, re.I):
                            tem_filtro = True
                            break
                    
                    result.tem_filtro_categoria = tem_filtro
                    print(f"      Filtro de categoria: {'SIM' if tem_filtro else 'NÃO'}")
                    
                    # Procurar por cards/seletores CSS comuns
                    seletores_comuns = [
                        ".card",
                        ".item",
                        "article",
                        "[class*='card']",
                        "[class*='item']",
                        "[class*='property']",
                        "[class*='imovel']",
                        "[class*='lote']",
                        "a[href*='/imovel']",
                        "a[href*='/leilao']",
                        "a[href*='/lote']",
                    ]
                    
                    seletores_encontrados = []
                    cards_count = 0
                    
                    for seletor in seletores_comuns:
                        try:
                            elements = await page.query_selector_all(seletor)
                            if elements:
                                count = len(elements)
                                # Filtrar apenas elementos que parecem ser cards de imóveis
                                # (têm link, imagem, ou texto relevante)
                                valid_count = 0
                                for elem in elements[:10]:  # Verificar amostra
                                    text_elem = await elem.inner_text()
                                    href = await elem.get_attribute("href") if await elem.get_attribute("href") else ""
                                    
                                    # Verificar se parece ser um card de imóvel
                                    if any(word in text_elem.lower() for word in ["r$", "imóvel", "casa", "apto", "terreno"]) or \
                                       any(word in href.lower() for word in ["imovel", "leilao", "lote"]):
                                        valid_count += 1
                                
                                if valid_count > 0 or count > 5:  # Se tem muitos elementos, provavelmente é relevante
                                    seletores_encontrados.append(f"{seletor} ({count} elementos)")
                                    if seletor in [".card", "[class*='card']", "article"]:
                                        cards_count = max(cards_count, count)
                        except:
                            pass
                    
                    result.seletores_css = seletores_encontrados
                    result.cards_encontrados = cards_count
                    print(f"      Seletores encontrados: {len(seletores_encontrados)}")
                    print(f"      Cards encontrados: {cards_count}")
                    
                    # Extrair links de imóveis
                    print(f"   [5] Extraindo links de imóveis...")
                    
                    # Padrões de URLs de imóveis
                    link_patterns = [
                        r'href=["\']([^"\']*/(?:imovel|leilao|lote|produto)/[^"\']*)["\']',
                        r'href=["\']([^"\']*/\d+[^"\']*)["\']',  # URLs com números
                    ]
                    
                    links_encontrados = set()
                    for pattern in link_patterns:
                        matches = re.findall(pattern, html_imoveis, re.I)
                        for match in matches:
                            full_url = urljoin(site["url"], match)
                            # Filtrar apenas URLs que parecem ser de imóveis
                            if any(word in full_url.lower() for word in ["imovel", "leilao", "lote", "produto"]) or \
                               (re.search(r'/\d+', full_url) and "imoveis" not in full_url.lower()):
                                links_encontrados.add(full_url)
                    
                    # Limitar a 50 links para análise
                    result.links_imoveis = list(links_encontrados)[:50]
                    result.quantidade_real = len(links_encontrados)
                    
                    print(f"      Links de imóveis encontrados: {len(links_encontrados)}")
                    
                    # Verificar paginação
                    print(f"   [6] Verificando paginação...")
                    
                    paginacao_selectors = [
                        ".pagination",
                        "[class*='pagination']",
                        "[class*='page']",
                        "a[rel='next']",
                        "a[href*='pagina']",
                        "a[href*='page']",
                    ]
                    
                    paginacao_encontrada = False
                    for selector in paginacao_selectors:
                        try:
                            elements = await page.query_selector_all(selector)
                            if elements:
                                paginacao_encontrada = True
                                
                                # Tentar identificar tipo de paginação
                                html_pag = await page.content()
                                if "?pagina=" in html_pag or "&pagina=" in html_pag:
                                    result.paginacao_tipo = "query"
                                    result.paginacao_param = "pagina"
                                elif "?page=" in html_pag or "&page=" in html_pag:
                                    result.paginacao_tipo = "query"
                                    result.paginacao_param = "page"
                                elif "/page/" in html_pag:
                                    result.paginacao_tipo = "path"
                                    result.paginacao_param = "page"
                                
                                break
                        except:
                            pass
                    
                    if paginacao_encontrada:
                        print(f"      Paginação: {result.paginacao_tipo} (param: {result.paginacao_param})")
                    else:
                        print(f"      Paginação: Não encontrada ou scroll infinito")
                        result.observacoes += "Possível scroll infinito ou carregamento dinâmico. "
                    
                    # Se quantidade_real parece baixa, verificar se há mais páginas
                    if result.quantidade_real < 20 and paginacao_encontrada:
                        result.observacoes += f"Apenas primeira página analisada. Total pode ser maior. "
                    
                except Exception as e:
                    result.erro = f"Erro ao acessar página de imóveis: {str(e)[:100]}"
                    print(f"      [ERRO] {result.erro}")
            else:
                result.observacoes = "Não foi possível identificar URL específica de imóveis. "
                print(f"   [4] URL de imóveis não encontrada")
            
            await browser.close()
            
    except ImportError:
        result.erro = "Playwright não instalado. Execute: pip install playwright && playwright install chromium"
    except Exception as e:
        result.erro = f"Erro geral: {str(e)[:200]}"
        print(f"   [ERRO] {result.erro}")
    
    return result


async def main():
    """Função principal."""
    
    print("="*70)
    print("VALIDAÇÃO VISUAL DOS TOP LEILOEIROS")
    print("="*70)
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sites: {len(SITES)}")
    print("="*70)
    
    resultados = []
    
    for site in SITES:
        resultado = await validar_site(site)
        resultados.append(resultado)
        
        # Pausa entre sites
        await asyncio.sleep(2)
    
    # Salvar resultados
    output_file = "validacao_visual_resultados.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([asdict(r) for r in resultados], f, ensure_ascii=False, indent=2)
    
    # Também salvar em formato mais legível
    output_txt = "validacao_visual_resultados.txt"
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("VALIDACAO VISUAL DOS TOP LEILOEIROS\n")
        f.write("="*70 + "\n\n")
        
        for r in resultados:
            f.write(f"\n{'='*70}\n")
            f.write(f"SITE: {r.site_name}\n")
            f.write(f"{'='*70}\n")
            f.write(f"URL Base: {r.url_base}\n")
            f.write(f"URL Imoveis: {r.url_imoveis or 'NAO ENCONTRADA'}\n")
            f.write(f"Quantidade Real: {r.quantidade_real}\n")
            f.write(f"Tem Filtro de Categoria: {'SIM' if r.tem_filtro_categoria else 'NAO'}\n")
            f.write(f"Cards Encontrados: {r.cards_encontrados}\n")
            f.write(f"Paginacao: {r.paginacao_tipo or 'NAO IDENTIFICADA'} ({r.paginacao_param or 'N/A'})\n")
            
            if r.seletores_css:
                f.write(f"\nSeletores CSS encontrados:\n")
                for seletor in r.seletores_css:
                    f.write(f"  - {seletor}\n")
            
            if r.links_imoveis:
                f.write(f"\nExemplos de Links (primeiros 10):\n")
                for link in r.links_imoveis[:10]:
                    f.write(f"  - {link}\n")
            
            if r.erro:
                f.write(f"\nERRO: {r.erro}\n")
            
            if r.observacoes:
                f.write(f"\nObservacoes: {r.observacoes}\n")
            
            if r.screenshot_path:
                f.write(f"\nScreenshot: {r.screenshot_path}\n")
            
            f.write("\n")
    
    # Relatório
    print("\n" + "="*70)
    print("RELATÓRIO DE VALIDAÇÃO")
    print("="*70)
    
    print(f"\n{'Site':<25} {'URL Imóveis':<40} {'Qtd':<8} {'Filtro':<8} {'Cards':<8}")
    print("-"*100)
    
    for r in resultados:
        url_imoveis = r.url_imoveis[:37] + "..." if r.url_imoveis and len(r.url_imoveis) > 40 else (r.url_imoveis or "N/A")
        filtro = "SIM" if r.tem_filtro_categoria else "NÃO"
        print(f"{r.site_name:<25} {url_imoveis:<40} {r.quantidade_real:<8} {filtro:<8} {r.cards_encontrados:<8}")
        
        if r.erro:
            print(f"   [ERRO] {r.erro}")
        if r.observacoes:
            print(f"   [OBS] {r.observacoes}")
    
    print("\n" + "-"*100)
    print(f"\n[OK] Validação concluída!")
    print(f"Resultados salvos em: {output_file}")
    print(f"Screenshots salvos em: validacao_screenshots/")
    
    # Documentação detalhada
    doc_file = "VALIDACAO_VISUAL_DOCUMENTACAO.md"
    with open(doc_file, 'w', encoding='utf-8') as f:
        f.write("# VALIDAÇÃO VISUAL DOS TOP LEILOEIROS\n\n")
        f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for r in resultados:
            f.write(f"## {r.site_name}\n\n")
            f.write(f"- **URL Base:** {r.url_base}\n")
            f.write(f"- **URL Imóveis:** {r.url_imoveis or 'NÃO ENCONTRADA'}\n")
            f.write(f"- **Quantidade Real:** {r.quantidade_real}\n")
            f.write(f"- **Tem Filtro de Categoria:** {'SIM' if r.tem_filtro_categoria else 'NÃO'}\n")
            f.write(f"- **Cards Encontrados:** {r.cards_encontrados}\n")
            f.write(f"- **Paginação:** {r.paginacao_tipo or 'NÃO IDENTIFICADA'} ({r.paginacao_param or 'N/A'})\n")
            f.write(f"- **Screenshot:** {r.screenshot_path or 'N/A'}\n")
            
            if r.seletores_css:
                f.write(f"- **Seletores CSS:**\n")
                for seletor in r.seletores_css:
                    f.write(f"  - {seletor}\n")
            
            if r.links_imoveis:
                f.write(f"- **Exemplos de Links (primeiros 5):**\n")
                for link in r.links_imoveis[:5]:
                    f.write(f"  - {link}\n")
            
            if r.erro:
                f.write(f"- **ERRO:** {r.erro}\n")
            
            if r.observacoes:
                f.write(f"- **Observações:** {r.observacoes}\n")
            
            f.write("\n")
    
    print(f"Documentação salva em: {doc_file}")


if __name__ == "__main__":
    asyncio.run(main())

