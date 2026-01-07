#!/usr/bin/env python3
"""Teste rápido do HTML do Sodré Santoro"""

import httpx
from bs4 import BeautifulSoup
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'pt-BR,pt;q=0.9',
}

url = "https://www.sodresantoro.com.br/imoveis"

print(f"Acessando: {url}")
response = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)
print(f"Status: {response.status_code}")
print(f"URL final: {response.url}")

soup = BeautifulSoup(response.text, 'html.parser')

# Tentar diferentes seletores
selectors = [
    "a[href*='/leilao']",
    "a[href*='/lote']",
    "a[href*='/imovel']",
    ".card",
    ".item",
    "article",
    "div[class*='lote']",
    "div[class*='leilao']",
]

print("\nTestando seletores:")
for selector in selectors:
    elements = soup.select(selector)
    if elements:
        print(f"  {selector}: {len(elements)} elementos")
        if len(elements) <= 5:
            for elem in elements[:3]:
                href = elem.get('href', '') if hasattr(elem, 'get') else ''
                text = elem.get_text(strip=True)[:50] if hasattr(elem, 'get_text') else str(elem)[:50]
                print(f"    - {href[:60]} | {text}")

# Procurar por links de leilão/lote usando regex
print("\nProcurando links com regex:")
links = soup.find_all('a', href=re.compile(r'/(leilao|lote|imovel)/'))
print(f"  Links encontrados: {len(links)}")
for link in links[:10]:
    href = link.get('href', '')
    text = link.get_text(strip=True)[:50]
    print(f"    - {href[:80]} | {text}")

