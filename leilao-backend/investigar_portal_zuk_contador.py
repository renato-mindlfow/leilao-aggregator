#!/usr/bin/env python3
"""
Investigação: Descobrir a matemática do Portal Zukerman
- Total de imóveis no contador
- Quantos aparecem inicialmente
- Quantos aparecem por clique
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
"""


async def investigar_contador():
    """Investiga o contador e a matemática do Portal Zukerman."""
    
    print("="*70)
    print("INVESTIGACAO: Portal Zukerman - Matematica do Contador")
    print("="*70)
    
    result = {
        "total_imoveis": None,
        "imoveis_iniciais": None,
        "imoveis_por_clique": None,
        "cliques_necessarios": None
    }
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='pt-BR',
            )
            await context.add_init_script(STEALTH_SCRIPT)
            
            page = await context.new_page()
            
            print("\n[1] Acessando pagina inicial...")
            await page.goto("https://www.portalzuk.com.br/leilao-de-imoveis", wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)
            
            # Procurar contador de imóveis
            print("\n[2] Procurando contador de imoveis...")
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Procurar por padrões como "949 imóveis", "949 encontrados", etc.
            body_text = await page.evaluate("() => document.body.innerText")
            
            # Padrões para encontrar o total
            patterns = [
                r'(\d+)\s*im[oó]veis?\s*(?:encontrados|dispon[íi]veis?|total)',
                r'(?:total|encontrados?)\s*[:\s]*(\d+)\s*im[oó]veis?',
                r'(\d+)\s*resultados?',
            ]
            
            total_found = None
            for pattern in patterns:
                match = re.search(pattern, body_text, re.I)
                if match:
                    total_found = int(match.group(1))
                    print(f"   [ENCONTRADO] Total: {total_found} imoveis")
                    result["total_imoveis"] = total_found
                    break
            
            if not total_found:
                # Procurar no HTML por elementos com números
                numbers = soup.find_all(string=re.compile(r'\d+\s*im[oó]veis?'))
                for num_text in numbers:
                    match = re.search(r'(\d+)', num_text)
                    if match:
                        total_found = int(match.group(1))
                        if total_found > 10:  # Provavelmente é o total
                            print(f"   [ENCONTRADO] Total: {total_found} imoveis (no HTML)")
                            result["total_imoveis"] = total_found
                            break
            
            # Contar imóveis iniciais
            print("\n[3] Contando imoveis iniciais...")
            initial_links = await page.query_selector_all('a[href*="/imovel/"]')
            initial_count = len(initial_links)
            print(f"   Imoveis iniciais: {initial_count}")
            result["imoveis_iniciais"] = initial_count
            
            # Fechar modal se existir
            print("\n[3.5] Verificando modais...")
            modal = await page.query_selector("#modalVirada, .modal.show")
            if modal:
                print("   [FECHANDO] Modal encontrado, fechando...")
                close_btn = await page.query_selector("#modalVirada .close, .modal .close, [data-dismiss='modal']")
                if close_btn:
                    await close_btn.click()
                    await asyncio.sleep(1)
                else:
                    # Tentar pressionar ESC
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(1)
            
            # Fazer um clique e ver quantos novos aparecem
            print("\n[4] Testando um clique no botao 'Carregar mais'...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            load_more_btn = await page.query_selector("#btn_carregarMais")
            if load_more_btn:
                is_visible = await load_more_btn.is_visible()
                print(f"   Botao encontrado: {is_visible}")
                
                if is_visible:
                    # Usar JavaScript click para evitar interceptação
                    await page.evaluate("document.getElementById('btn_carregarMais').click()")
                    await asyncio.sleep(3)
                    
                    # Contar novamente
                    after_click_links = await page.query_selector_all('a[href*="/imovel/"]')
                    after_click_count = len(after_click_links)
                    new_count = after_click_count - initial_count
                    
                    print(f"   Apos 1 clique: {after_click_count} imoveis")
                    print(f"   Novos imoveis: {new_count}")
                    result["imoveis_por_clique"] = new_count
                    
                    # Calcular cliques necessários
                    if total_found and new_count > 0:
                        remaining = total_found - after_click_count
                        cliques_needed = (remaining // new_count) + (1 if remaining % new_count > 0 else 0)
                        result["cliques_necessarios"] = cliques_needed
                        print(f"\n   [CALCULO]")
                        print(f"   Total: {total_found}")
                        print(f"   Iniciais: {initial_count}")
                        print(f"   Por clique: {new_count}")
                        print(f"   Restantes: {remaining}")
                        print(f"   Cliques necessarios: ~{cliques_needed}")
            else:
                print("   [ERRO] Botao 'Carregar mais' nao encontrado")
            
            await browser.close()
            
    except Exception as e:
        print(f"\n[ERRO] {e}")
        result["error"] = str(e)
    
    return result


if __name__ == "__main__":
    result = asyncio.run(investigar_contador())
    print("\n" + "="*70)
    print("RESULTADO FINAL")
    print("="*70)
    print(f"Total no contador: {result.get('total_imoveis', 'N/A')}")
    print(f"Imoveis iniciais: {result.get('imoveis_iniciais', 'N/A')}")
    print(f"Imoveis por clique: {result.get('imoveis_por_clique', 'N/A')}")
    print(f"Cliques necessarios: {result.get('cliques_necessarios', 'N/A')}")

