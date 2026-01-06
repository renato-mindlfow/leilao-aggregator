#!/usr/bin/env python3
"""
Investigação detalhada do Portal Zukerman para descobrir como carregar mais imóveis.
"""

import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
"""


async def investigar_portal_zuk():
    """Investiga Portal Zukerman em detalhes."""
    
    print("="*70)
    print("INVESTIGACAO: Portal Zukerman - Como carregar mais imoveis")
    print("="*70)
    
    result = {
        "url": "https://www.portalzuk.com.br/leilao-de-imoveis",
        "buttons_found": [],
        "scroll_infinite": False,
        "pagination_urls": {},
        "recommendations": []
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
            
            # 1. Acessar página inicial
            print(f"\n[1] Acessando: {result['url']}")
            await page.goto(result["url"], wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)
            
            # 2. Fazer scroll até o final
            print("\n[2] Fazendo scroll ate o final da pagina...")
            initial_links = len(await page.query_selector_all('a[href*="/imovel/"]'))
            print(f"   Links iniciais: {initial_links}")
            
            # Scroll múltiplas vezes
            for i in range(10):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                # Verificar se novos links apareceram (scroll infinito)
                current_links = len(await page.query_selector_all('a[href*="/imovel/"]'))
                if current_links > initial_links:
                    print(f"   Scroll {i+1}: {current_links} links (novos: {current_links - initial_links})")
                    initial_links = current_links
                else:
                    print(f"   Scroll {i+1}: {current_links} links (sem novos)")
            
            final_links = len(await page.query_selector_all('a[href*="/imovel/"]'))
            print(f"\n   Total de links apos scroll: {final_links}")
            
            if final_links > initial_links:
                result["scroll_infinite"] = True
                result["recommendations"].append("Scroll infinito detectado - carrega automaticamente ao scrollar")
            
            # 3. Procurar TODOS os botões e links possíveis
            print("\n[3] Procurando botoes e links que carregam mais...")
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Procurar por texto
            all_buttons = soup.select('button, a, [role="button"], [onclick*="load"], [onclick*="more"], [onclick*="carregar"]')
            
            keywords = ['carregar', 'load', 'more', 'mais', 'ver mais', 'mostrar', 'próxima', 'next', '+', 'ver todos']
            
            for btn in all_buttons:
                text = btn.get_text(strip=True).lower()
                classes = ' '.join(btn.get('class', []))
                onclick = btn.get('onclick', '')
                href = btn.get('href', '')
                
                # Verificar se contém palavras-chave
                if any(keyword in text for keyword in keywords) or any(keyword in classes.lower() for keyword in keywords):
                    selector = f"button:contains('{btn.get_text(strip=True)[:20]}')" if btn.name == 'button' else f"a:contains('{btn.get_text(strip=True)[:20]}')"
                    
                    result["buttons_found"].append({
                        "tag": btn.name,
                        "text": btn.get_text(strip=True),
                        "classes": classes,
                        "id": btn.get('id', ''),
                        "href": href,
                        "onclick": onclick[:100] if onclick else '',
                        "selector_suggestion": selector,
                        "visible": True
                    })
                    print(f"   [ENCONTRADO] {btn.name}: '{btn.get_text(strip=True)[:50]}'")
                    print(f"      Classes: {classes[:80]}")
            
            # Procurar por classes comuns
            common_selectors = [
                '[class*="load-more"]',
                '[class*="carregar"]',
                '[class*="more"]',
                '[class*="next"]',
                '[class*="pagination"]',
                '[class*="pager"]',
                '[id*="load"]',
                '[id*="more"]',
            ]
            
            print("\n[4] Procurando por seletores comuns...")
            for selector in common_selectors:
                elements = soup.select(selector)
                if elements:
                    for el in elements[:3]:
                        text = el.get_text(strip=True)
                        if text or el.get('href') or el.get('onclick'):
                            result["buttons_found"].append({
                                "tag": el.name,
                                "text": text,
                                "classes": ' '.join(el.get('class', [])),
                                "id": el.get('id', ''),
                                "selector": selector,
                                "visible": True
                            })
                            print(f"   [ENCONTRADO] {selector}: '{text[:50]}'")
            
            # 5. Testar URLs de paginação alternativas
            print("\n[5] Testando URLs de paginacao alternativas...")
            
            test_urls = [
                "https://www.portalzuk.com.br/leilao-de-imoveis?page=2",
                "https://www.portalzuk.com.br/leilao-de-imoveis/2",
                "https://www.portalzuk.com.br/leilao-de-imoveis?pagina=2",
                "https://www.portalzuk.com.br/leilao-de-imoveis?p=2",
            ]
            
            for test_url in test_urls:
                try:
                    print(f"   Testando: {test_url}")
                    await page.goto(test_url, wait_until='domcontentloaded', timeout=20000)
                    await asyncio.sleep(3)
                    
                    final_url = page.url
                    links_count = len(await page.query_selector_all('a[href*="/imovel/"]'))
                    
                    result["pagination_urls"][test_url] = {
                        "final_url": final_url,
                        "links_found": links_count,
                        "works": final_url != result["url"] or links_count > 0,
                        "redirected": final_url != test_url
                    }
                    
                    if final_url != result["url"]:
                        print(f"      [FUNCIONA] Redirecionou para: {final_url}")
                        print(f"      Links encontrados: {links_count}")
                    elif links_count > 0:
                        print(f"      [FUNCIONA] Mesma URL mas tem {links_count} links")
                    else:
                        print(f"      [NAO FUNCIONA] Mesma URL, sem links")
                        
                except Exception as e:
                    result["pagination_urls"][test_url] = {"error": str(e)}
                    print(f"      [ERRO] {e}")
            
            # 6. Verificar se há paginação escondida no HTML
            print("\n[6] Verificando paginacao escondida no HTML...")
            html_text = html.lower()
            
            if 'pagination' in html_text or 'pager' in html_text:
                pagination_elements = soup.select('[class*="pagination"], [class*="pager"], nav')
                if pagination_elements:
                    print(f"   [ENCONTRADO] {len(pagination_elements)} elementos de paginacao")
                    for pag in pagination_elements[:2]:
                        print(f"      HTML: {str(pag)[:200]}")
                        result["recommendations"].append(f"Paginacao encontrada no HTML: {pag.get('class', [])}")
            
            # 7. Verificar eventos de scroll
            print("\n[7] Verificando eventos de scroll...")
            scroll_events = await page.evaluate("""
                () => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    const scrollHandlers = [];
                    scripts.forEach(script => {
                        if (script.textContent) {
                            if (script.textContent.includes('scroll') && 
                                (script.textContent.includes('load') || script.textContent.includes('more'))) {
                                scrollHandlers.push(script.textContent.substring(0, 200));
                            }
                        }
                    });
                    return scrollHandlers;
                }
            """)
            
            if scroll_events:
                print(f"   [ENCONTRADO] {len(scroll_events)} scripts com handlers de scroll")
                result["recommendations"].append("Scroll infinito pode estar implementado via JavaScript")
            
            await browser.close()
            
    except Exception as e:
        result["error"] = str(e)
        print(f"\n[ERRO] {e}")
    
    # Salvar resultados
    with open("investigacao_portal_zuk.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # Relatório final
    print("\n" + "="*70)
    print("RELATORIO FINAL")
    print("="*70)
    
    print(f"\nScroll infinito: {'SIM' if result.get('scroll_infinite') else 'NAO'}")
    print(f"\nBotoes encontrados: {len(result.get('buttons_found', []))}")
    
    if result.get("buttons_found"):
        print("\nBotoes/Links encontrados:")
        for btn in result["buttons_found"][:5]:
            print(f"  - {btn['tag']}: '{btn.get('text', '')[:40]}'")
            print(f"    Classes: {btn.get('classes', '')[:60]}")
            if btn.get('selector'):
                print(f"    Seletor: {btn['selector']}")
    
    print(f"\nURLs de paginacao testadas: {len(result.get('pagination_urls', {}))}")
    working_urls = [url for url, data in result.get("pagination_urls", {}).items() if data.get("works")]
    if working_urls:
        print("URLs que funcionam:")
        for url in working_urls:
            print(f"  - {url}")
    
    if result.get("recommendations"):
        print("\nRecomendacoes:")
        for rec in result["recommendations"]:
            print(f"  - {rec}")
    
    print(f"\n[ARQUIVO] Resultados salvos em: investigacao_portal_zuk.json")
    
    return result


if __name__ == "__main__":
    asyncio.run(investigar_portal_zuk())

