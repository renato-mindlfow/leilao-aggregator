#!/usr/bin/env python3
"""Teste de estrutura HTML para otimizar seletores"""
import asyncio
import httpx
from bs4 import BeautifulSoup
import re
import sys
import codecs

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SITES_TESTE = [
    ("megaleiloes.com.br", "/imoveis"),
    ("portalzuk.com.br", "/leilao-de-imoveis"),
    ("sold.com.br", "/leiloes/imoveis"),
    ("lancejudicial.com.br", "/leiloes/imoveis"),
]

async def testar_site(dominio, path):
    url = f"https://www.{dominio}{path}"
    print(f"\n{'='*70}")
    print(f"🔍 TESTANDO: {url}")
    print('='*70)
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=HEADERS) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}")
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Estatísticas básicas
            print(f"\n📊 ESTATÍSTICAS:")
            print(f"   HTML size: {len(response.text):,} bytes")
            print(f"   Total links: {len(soup.find_all('a'))}")
            print(f"   Total divs: {len(soup.find_all('div'))}")
            
            # Buscar links que parecem ser imóveis
            print(f"\n🔗 LINKS QUE PARECEM SER IMÓVEIS:")
            imovel_links = []
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                if any(palavra in href.lower() for palavra in ['imovel', 'lote', 'item', 'leilao', 'auction']):
                    if 'detalhes' in href or 'view' in href or re.search(r'/\d+', href):
                        imovel_links.append(a)
            
            print(f"   Encontrados: {len(imovel_links)} links potenciais")
            
            if imovel_links:
                print(f"\n   PRIMEIROS 5 EXEMPLOS:")
                for i, link in enumerate(imovel_links[:5], 1):
                    href = link.get('href', '')
                    texto = link.get_text(strip=True)[:80]
                    classes = ' '.join(link.get('class', []))
                    print(f"   [{i}] href={href}")
                    print(f"       text={texto}")
                    print(f"       class={classes}")
                    print()
            
            # Buscar containers comuns
            print(f"\n📦 CONTAINERS POTENCIAIS:")
            containers = []
            for tag in ['div', 'article', 'section', 'li']:
                for elem in soup.find_all(tag, class_=True):
                    classes = ' '.join(elem.get('class', []))
                    if any(palavra in classes.lower() for palavra in ['card', 'item', 'lote', 'property', 'product', 'result', 'listing']):
                        if elem not in containers:
                            containers.append((tag, classes, elem))
            
            print(f"   Encontrados: {len(containers)} containers")
            
            if containers:
                print(f"\n   PRIMEIROS 3 TIPOS:")
                seen_classes = set()
                for tag, classes, elem in containers[:10]:
                    if classes not in seen_classes:
                        seen_classes.add(classes)
                        links_dentro = len(elem.find_all('a'))
                        print(f"   <{tag} class=\"{classes}\"> ({links_dentro} links)")
                        if len(seen_classes) >= 3:
                            break
            
            # Verificar se requer JavaScript
            print(f"\n⚙️ ANÁLISE JAVASCRIPT:")
            scripts = soup.find_all('script')
            print(f"   Scripts no HTML: {len(scripts)}")
            
            # Verificar se há placeholders vazios
            main_content = soup.find(['main', 'div'], id=re.compile(r'(content|main|app|root)', re.I))
            if main_content:
                texto_principal = main_content.get_text(strip=True)
                print(f"   Texto no conteúdo principal: {len(texto_principal)} chars")
                if len(texto_principal) < 500:
                    print(f"   ⚠️ POUCO CONTEÚDO - Provavelmente requer JavaScript!")
            
            # Buscar frameworks JS
            html_lower = response.text.lower()
            frameworks = []
            if 'react' in html_lower or 'reactdom' in html_lower:
                frameworks.append('React')
            if 'vue' in html_lower or 'vuejs' in html_lower:
                frameworks.append('Vue')
            if 'angular' in html_lower:
                frameworks.append('Angular')
            if 'next' in html_lower or 'nextjs' in html_lower:
                frameworks.append('Next.js')
            
            if frameworks:
                print(f"   Frameworks detectados: {', '.join(frameworks)}")
                print(f"   ⚠️ REQUER JAVASCRIPT (TIER 2)!")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

async def main():
    print("🧪 TESTE DE ESTRUTURA HTML - OTIMIZAÇÃO DE SELETORES\n")
    
    for dominio, path in SITES_TESTE:
        await testar_site(dominio, path)
        await asyncio.sleep(2)
    
    print(f"\n\n{'='*70}")
    print("✅ TESTES CONCLUÍDOS")
    print('='*70)

if __name__ == "__main__":
    asyncio.run(main())
