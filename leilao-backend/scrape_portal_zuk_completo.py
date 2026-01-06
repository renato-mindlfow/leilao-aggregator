#!/usr/bin/env python3
"""
Scraper completo do Portal Zukerman com cliques no botão "Carregar mais".
"""

import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright
from urllib.parse import urljoin

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
"""


async def scrape_portal_zuk_completo(max_items: int = 1000) -> dict:
    """
    Portal Zukerman - Scraper completo com cliques no botão "Carregar mais".
    """
    
    result = {
        "id": "portalzuk",
        "name": "Portal Zukerman",
        "method": "playwright",
        "success": False,
        "total_imoveis_contador": None,
        "imoveis_iniciais": None,
        "cliques_realizados": 0,
        "total_extracted": 0,
        "properties": [],
        "errors": [],
    }
    
    print("="*70)
    print("PORTAL ZUKERMAN - Scraping Completo com 'Carregar mais'")
    print("="*70)
    
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
            
            url = "https://www.portalzuk.com.br/leilao-de-imoveis"
            print(f"\n[1] Acessando: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)
            
            # Fechar modal se existir
            print("\n[2] Verificando modais...")
            modal = await page.query_selector("#modalVirada, .modal.show")
            if modal:
                print("   [FECHANDO] Modal encontrado, fechando...")
                close_btn = await page.query_selector("#modalVirada .close, .modal .close, [data-dismiss='modal']")
                if close_btn:
                    await close_btn.click()
                    await asyncio.sleep(1)
                else:
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(1)
            
            # Ler contador total de imóveis
            print("\n[3] Lendo contador de imoveis...")
            body_text = await page.evaluate("() => document.body.innerText")
            
            patterns = [
                r'(\d+)\s*im[oó]veis?\s*(?:encontrados|dispon[íi]veis?|total)',
                r'(?:total|encontrados?)\s*[:\s]*(\d+)\s*im[oó]veis?',
                r'(\d+)\s*resultados?',
            ]
            
            total_contador = None
            for pattern in patterns:
                match = re.search(pattern, body_text, re.I)
                if match:
                    total_contador = int(match.group(1))
                    print(f"   [ENCONTRADO] Total no contador: {total_contador} imoveis")
                    result["total_imoveis_contador"] = total_contador
                    break
            
            # Contar imóveis iniciais
            print("\n[4] Contando imoveis iniciais...")
            initial_links = await page.query_selector_all('a[href*="/imovel/"]')
            initial_count = len(initial_links)
            print(f"   Imoveis iniciais: {initial_count}")
            result["imoveis_iniciais"] = initial_count
            
            all_links = set()
            for link in initial_links:
                href = await link.get_attribute("href")
                if href:
                    full_url = urljoin("https://www.portalzuk.com.br", href)
                    all_links.add(full_url)
            
            # Loop de cliques no botão "Carregar mais"
            print("\n[5] Iniciando loop de cliques no botao 'Carregar mais'...")
            max_cliques = 100  # Limite de segurança
            cliques_realizados = 0
            
            for click_num in range(max_cliques):
                # Scroll até o final
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
                
                # Procurar botão "Carregar mais"
                load_more_btn = await page.query_selector("#btn_carregarMais")
                
                if not load_more_btn:
                    print(f"   [INFO] Botao nao encontrado apos {click_num} cliques, parando...")
                    break
                
                is_visible = await load_more_btn.is_visible()
                if not is_visible:
                    print(f"   [INFO] Botao nao visivel apos {click_num} cliques, parando...")
                    break
                
                # Contar links antes do clique
                links_before = len(all_links)
                
                # Clicar usando JavaScript para evitar interceptação
                try:
                    await page.evaluate("document.getElementById('btn_carregarMais').click()")
                    cliques_realizados += 1
                    await asyncio.sleep(3)  # Aguardar carregar novos itens
                except Exception as e:
                    print(f"   [ERRO] Erro ao clicar: {e}")
                    break
                
                # Extrair novos links
                new_links = await page.query_selector_all('a[href*="/imovel/"]')
                for link in new_links:
                    href = await link.get_attribute("href")
                    if href:
                        full_url = urljoin("https://www.portalzuk.com.br", href)
                        all_links.add(full_url)
                
                links_after = len(all_links)
                novos = links_after - links_before
                
                print(f"   Clique {cliques_realizados}: {links_after} links totais (+{novos} novos)")
                
                # Se não adicionou novos links, parar
                if novos == 0:
                    print(f"   [INFO] Sem novos links, parando...")
                    break
                
                # Se atingiu o limite desejado
                if len(all_links) >= max_items:
                    print(f"   [INFO] Limite atingido ({max_items}), parando...")
                    break
                
                # Se já tem todos os imóveis do contador
                if total_contador and len(all_links) >= total_contador:
                    print(f"   [INFO] Todos os imoveis do contador extraidos, parando...")
                    break
            
            result["cliques_realizados"] = cliques_realizados
            
            # Converter para propriedades
            print(f"\n[6] Convertendo {len(all_links)} links em propriedades...")
            for url in list(all_links)[:max_items]:
                # Extrair info da URL: /imovel/{estado}/{cidade}/{bairro}/{rua}/{id}
                parts = url.split('/')
                state = parts[4] if len(parts) > 4 else ""
                city = parts[5] if len(parts) > 5 else ""
                
                result["properties"].append({
                    "url": url,
                    "title": "",
                    "price": "",
                    "state": state.upper() if state else "",
                    "city": city.replace("-", " ").title() if city else "",
                    "location": f"{city.replace('-', ' ').title()}/{state.upper()}" if city and state else "",
                    "auctioneer_id": "portalzuk",
                    "auctioneer_name": "Portal Zukerman",
                })
            
            result["success"] = len(all_links) > 0
            result["total_extracted"] = len(result["properties"])
            
            await browser.close()
            
            print(f"\n[OK] Extraidos: {result['total_extracted']} imoveis")
            print(f"     Cliques realizados: {cliques_realizados}")
            
    except Exception as e:
        result["errors"].append(str(e))
        print(f"\n[ERRO] {e}")
    
    return result


async def main():
    """Função principal."""
    result = await scrape_portal_zuk_completo(max_items=1000)
    
    # Salvar resultado
    with open("resultado_portal_zuk_completo.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # Relatório
    print("\n" + "="*70)
    print("RELATORIO FINAL")
    print("="*70)
    print(f"Total no contador: {result.get('total_imoveis_contador', 'N/A')}")
    print(f"Imoveis iniciais: {result.get('imoveis_iniciais', 'N/A')}")
    print(f"Cliques realizados: {result.get('cliques_realizados', 'N/A')}")
    print(f"Imoveis extraidos: {result.get('total_extracted', 'N/A')}")
    print(f"\n[ARQUIVO] Resultado salvo em: resultado_portal_zuk_completo.json")


if __name__ == "__main__":
    asyncio.run(main())

