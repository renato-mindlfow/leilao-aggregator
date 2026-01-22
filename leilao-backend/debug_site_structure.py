#!/usr/bin/env python3
"""Debug - Analisa estrutura HTML de um site"""
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import sys

async def analyze_site(url: str):
    """Analisa a estrutura HTML de um site"""
    print(f"\n{'='*80}")
    print(f"Analisando: {url}")
    print(f"{'='*80}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, timeout=30000, wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Scroll para carregar lazy content
            await page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 100;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if(totalHeight >= scrollHeight){
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            await asyncio.sleep(1)
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Procurar por padrões comuns
            print("🔍 Analisando estrutura...\n")
            
            # Cards/Items
            card_patterns = {
                'div.card': soup.select('div.card'),
                'div[class*="card"]': soup.select('div[class*="card"]'),
                'div[class*="lote"]': soup.select('div[class*="lote"]'),
                'div[class*="item"]': soup.select('div[class*="item"]'),
                'div[class*="property"]': soup.select('div[class*="property"]'),
                'div[class*="imovel"]': soup.select('div[class*="imovel"]'),
                'article': soup.select('article'),
                'div[class*="product"]': soup.select('div[class*="product"]'),
                'div[class*="listing"]': soup.select('div[class*="listing"]'),
            }
            
            print("📦 CARDS ENCONTRADOS:")
            for pattern, cards in card_patterns.items():
                if cards:
                    print(f"  {pattern}: {len(cards)} elementos")
            
            # Verificar se tem imagens
            images = soup.find_all('img', src=True)
            print(f"\n🖼️ IMAGENS: {len(images)} encontradas")
            
            # Links
            links_with_imovel = soup.find_all('a', href=lambda x: x and ('imovel' in x.lower() or 'lote' in x.lower() or 'leilao' in x.lower()))
            print(f"🔗 LINKS (imóvel/lote/leilão): {len(links_with_imovel)}")
            
            # Verificar se tem paginação
            pagination_keywords = ['page', 'pagina', 'next', 'proximo', 'anterior', 'prev']
            pagination = soup.find_all('a', href=lambda x: x and any(kw in x.lower() for kw in pagination_keywords))
            print(f"📄 PAGINAÇÃO: {len(pagination)} links encontrados")
            
            # Analisar primeiro card válido
            print(f"\n📋 ANALISANDO PRIMEIRO CARD...")
            for pattern, cards in card_patterns.items():
                if cards and len(cards) > 0:
                    first_card = cards[0]
                    print(f"\n  Pattern: {pattern}")
                    print(f"  Classes: {first_card.get('class', [])}")
                    
                    # Títulos no card
                    titles = first_card.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    print(f"  Títulos (h1-h6): {len(titles)}")
                    if titles:
                        print(f"    Exemplo: {titles[0].get_text(strip=True)[:100]}")
                    
                    # Links no card
                    links = first_card.find_all('a', href=True)
                    print(f"  Links: {len(links)}")
                    if links:
                        print(f"    Exemplo href: {links[0].get('href')}")
                    
                    # Imagens no card
                    imgs = first_card.find_all('img', src=True)
                    print(f"  Imagens: {len(imgs)}")
                    
                    # Texto do card
                    text = first_card.get_text(strip=True)
                    print(f"  Texto (primeiros 200 chars): {text[:200]}")
                    
                    break
            
            print(f"\n{'='*80}\n")
            
        except Exception as e:
            print(f"❌ Erro: {e}")
        finally:
            await browser.close()

if __name__ == '__main__':
    # Testar 3 sites diferentes
    test_urls = [
        'https://www.ckleiloes.com.br',
        'https://www.grandesleiloes.com.br',
        'https://www.bidgo.com.br'
    ]
    
    for url in test_urls:
        asyncio.run(analyze_site(url))
