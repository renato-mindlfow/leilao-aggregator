"""
Analisar estrutura dos 8 sites com imóveis
PARTE 3.3 - FASE 2
"""

import asyncio
import httpx
from bs4 import BeautifulSoup
import json

# 8 sites identificados com imóveis
sites = [
    {"id": "11", "name": "Biasileiloes", "website": "https://www.biasileiloes.com.br"},
    {"id": "48", "name": "E-Confianca", "website": "https://www.e-confianca.com.br"},
    {"id": "232", "name": "Grupocarvalholeiloes", "website": "https://www.grupocarvalholeiloes.com.br"},
    {"id": "74", "name": "Kronbergleiloes", "website": "https://kronbergleiloes.com.br/"},
    {"id": "123", "name": "Leiloeslaraforster", "website": "https://www.leiloeslaraforster.com.br"},
    {"id": "80", "name": "Marquesleiloes", "website": "https://www.marquesleiloes.com.br"},
    {"id": "24", "name": "Pecinileiloes", "website": "https://www.pecinileiloes.com.br"},
    {"id": "95", "name": "Wmleiloes", "website": "https://wmleiloes.com.br/"}
]

async def analyze_site(site):
    """Analisa a estrutura de um site"""
    print(f"\n{'='*70}")
    print(f"Analisando: {site['name']}")
    print(f"URL: {site['website']}")
    print(f"{'='*70}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with httpx.AsyncClient(headers=headers, timeout=25.0, verify=False, follow_redirects=True) as client:
            response = await client.get(site['website'])
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}")
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Procurar por cards/items
            card_selectors = [
                'div[class*="card"]',
                'div[class*="item"]',
                'div[class*="lote"]',
                'div[class*="property"]',
                'div[class*="imovel"]',
                'article',
                '.property',
                '.imovel',
                '.lote'
            ]
            
            print("\nCARDS ENCONTRADOS:")
            for selector in card_selectors:
                cards = soup.select(selector)
                if len(cards) > 0:
                    print(f"  {selector}: {len(cards)} elementos")
                    if len(cards) <= 5:
                        for i, card in enumerate(cards[:2]):
                            classes = card.get('class', [])
                            print(f"    [{i+1}] classes: {classes}")
            
            # Procurar links
            links = soup.select('a[href]')
            property_links = [a for a in links if any(kw in a.get('href', '').lower() 
                for kw in ['imovel', 'lote', 'property', 'detalhes', 'leilao'])]
            
            print(f"\nLINKS DE PROPRIEDADES: {len(property_links)}")
            if property_links:
                for link in property_links[:3]:
                    print(f"  - {link.get('href')}")
            
            # Verificar se usa plataforma conhecida
            html_lower = response.text.lower()
            platforms = {
                'leilao.br': 'leilao.br' in html_lower,
                'superbid': 'superbid' in html_lower,
                'megaleiloes': 'megaleiloes' in html_lower,
                'portalzuk': 'portalzuk' in html_lower or 'zukerman' in html_lower,
            }
            
            print("\nPLATAFORMAS DETECTADAS:")
            for platform, found in platforms.items():
                if found:
                    print(f"  >> {platform}")
            
            # Verificar scripts/APIs
            scripts = soup.find_all('script', src=True)
            apis = [s.get('src') for s in scripts if 'api' in s.get('src', '').lower()]
            
            if apis:
                print(f"\nAPIs DETECTADAS: {len(apis)}")
                for api in apis[:3]:
                    print(f"  - {api}")
            
            print(f"\nOK - Analise concluida")
            
    except Exception as e:
        print(f"ERRO: {str(e)[:100]}")

async def main():
    print("="*70)
    print("ANÁLISE DOS 8 SITES COM IMÓVEIS")
    print("PARTE 3.3 - FASE 2")
    print("="*70)
    
    for site in sites:
        await analyze_site(site)
        await asyncio.sleep(1)
    
    print("\n" + "="*70)
    print("ANÁLISE CONCLUÍDA")
    print("="*70)
    
    print("\nPROXIMOS PASSOS:")
    print("1. Sites com plataforma conhecida: usar scraper existente")
    print("2. Sites customizados: criar seletores especificos")
    print("3. Re-executar scrapers")

if __name__ == "__main__":
    asyncio.run(main())
