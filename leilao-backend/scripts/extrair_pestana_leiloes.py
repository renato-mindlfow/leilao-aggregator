"""
Script para extrair leilões do site Pestana Leilões
Usa estratégias de bypass para contornar bloqueios
"""
import asyncio
import httpx
import logging
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse
import sys
import os

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_brl(price_str: str) -> float | None:
    """Parse Brazilian Real format to float."""
    if not price_str:
        return None
    try:
        cleaned = re.sub(r'[R$\s]', '', price_str)
        cleaned = cleaned.replace('.', '').replace(',', '.')
        return float(cleaned)
    except (ValueError, AttributeError):
        return None

def parse_date(date_str: str) -> str | None:
    """Parse Brazilian date format to ISO format."""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    patterns = [
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%d/%m/%Y'),
        (r'(\d{1,2})/(\d{1,2})/(\d{2})', '%d/%m/%y'),
    ]
    
    for pattern, fmt in patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                from datetime import datetime
                dt = datetime.strptime(match.group(0), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
    
    return None

async def fetch_with_bypass(url: str, strategy: int = 1) -> tuple[str | None, int]:
    """
    Tenta acessar URL com diferentes estratégias de bypass
    
    Returns:
        (html_content, status_code)
    """
    base_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    
    strategies = [
        # Estratégia 1: Headers básicos
        {
            'headers': base_headers,
            'timeout': 30.0,
            'follow_redirects': True
        },
        # Estratégia 2: Headers mais completos (simula navegador real)
        {
            'headers': {
                **base_headers,
                'Referer': 'https://www.google.com/',
                'Sec-Fetch-User': '?1',
                'DNT': '1',
            },
            'timeout': 30.0,
            'follow_redirects': True
        },
        # Estratégia 3: Headers mínimos (pode passar por alguns filtros)
        {
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            },
            'timeout': 30.0,
            'follow_redirects': True
        },
        # Estratégia 4: Usar Jina Reader (bypass via API)
        {
            'headers': {'X-Return-Format': 'html'},
            'timeout': 60.0,
            'follow_redirects': False,
            'use_jina': True
        }
    ]
    
    for i, config in enumerate(strategies, 1):
        try:
            logger.info(f"Tentando estratégia {i}...")
            
            if config.get('use_jina'):
                # Usar Jina Reader API
                jina_url = f"https://r.jina.ai/{url}"
                async with httpx.AsyncClient(timeout=config['timeout']) as client:
                    response = await client.get(jina_url, headers=config['headers'])
                    if response.status_code == 200:
                        logger.info(f"✅ Estratégia {i} (Jina) funcionou")
                        return response.text, response.status_code
            else:
                async with httpx.AsyncClient(
                    timeout=config['timeout'],
                    follow_redirects=config['follow_redirects']
                ) as client:
                    response = await client.get(url, headers=config['headers'])
                    
                    if response.status_code == 200:
                        html = response.text
                        # Verificar se não é página de erro
                        if 'navegador incompatível' in html.lower() or 'browser' in html.lower() and 'incompatível' in html.lower():
                            logger.warning(f"⚠️ Estratégia {i} retornou página de erro de navegador")
                            continue
                        logger.info(f"✅ Estratégia {i} funcionou")
                        return html, response.status_code
                    else:
                        logger.warning(f"⚠️ Estratégia {i} retornou status {response.status_code}")
                        
        except httpx.TimeoutException:
            logger.warning(f"⚠️ Estratégia {i} timeout")
            continue
        except Exception as e:
            logger.warning(f"⚠️ Estratégia {i} erro: {e}")
            continue
    
    return None, 0

async def extrair_leiloes_pestana():
    """Extrai leilões do site Pestana"""
    
    base_url = "https://www.pestanaleiloes.com.br"
    
    logger.info(f"\n{'='*60}")
    logger.info(f"EXTRAINDO LEILÕES DO PESTANA")
    logger.info(f"Site: {base_url}")
    logger.info("="*60)
    
    # Tentar acessar homepage
    html, status = await fetch_with_bypass(base_url)
    
    if not html:
        logger.error("❌ Não foi possível acessar o site após todas as estratégias")
        return []
    
    logger.info(f"✅ Site acessado com sucesso (status: {status})")
    logger.info(f"HTML recebido: {len(html)} caracteres")
    
    # Salvar HTML para debug
    with open('leilao-backend/scripts/pestana_debug.html', 'w', encoding='utf-8') as f:
        f.write(html)
    logger.info("HTML salvo em pestana_debug.html para análise")
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Verificar se é página de erro
    page_text = soup.get_text().lower()
    if 'navegador incompatível' in page_text or ('browser' in page_text and 'incompatível' in page_text):
        logger.warning("⚠️ Página de erro de navegador detectada, mas continuando análise...")
        # Continuar mesmo assim, pois o Jina pode ter extraído conteúdo útil
    
    leiloes = []
    seen_titles = set()
    
    # Estratégia 1: Procurar por qualquer texto que pareça ser título de leilão
    # O Jina pode ter extraído o conteúdo mesmo com bloqueio
    all_text = soup.get_text()
    
    # Procurar por padrões de títulos de leilões
    title_patterns = [
        r'(?:LOTE|APARTAMENTO|CASA|TERRENO|IMÓVEL|IMOVEL)[^\n]{20,200}',
        r'[A-Z][^\n]{30,150}(?:RS|SP|RJ|MG|PR|SC|BA|GO|PE|CE|DF|ES|MT|MS|PA|PB|AL|SE|TO|PI|MA|RN|RO|AC|AP|RR|AM)[^\n]{0,50}',
    ]
    
    potential_titles = []
    for pattern in title_patterns:
        matches = re.findall(pattern, all_text, re.IGNORECASE)
        potential_titles.extend(matches)
    
    logger.info(f"Encontrados {len(potential_titles)} possíveis títulos")
    
    # Estratégia 2: Procurar por links de leilões
    links = soup.find_all('a', href=True)
    base_url_parsed = urlparse(base_url)
    
    for link in links:
        href = link.get('href', '')
        link_text = link.get_text(strip=True)
        
        # Verificar se é link de leilão
        if not any(kw in href.lower() for kw in ['leilao', 'lote', 'imovel', '/imoveis/', '/lotes/']):
            continue
        
        # Construir URL completa
        if href.startswith('/'):
            full_url = base_url + href
        elif href.startswith('http'):
            full_url = href
        else:
            full_url = urljoin(base_url, href)
        
        # Encontrar container pai
        container = link.find_parent(['div', 'article', 'section', 'li', 'tr'])
        if not container:
            container = link
        
        container_text = container.get_text()
        
        # Extrair título
        title = None
        if link_text and len(link_text) > 10:
            title = link_text
        else:
            title_elem = container.find(['h2', 'h3', 'h4', 'h5'])
            if title_elem:
                title = title_elem.get_text(strip=True)
        
        if not title or len(title) < 10:
            continue
        
        # Evitar duplicatas
        title_key = title.lower()[:50]
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        
        # Extrair preço
        price = None
        lance_match = re.search(r'Lance\s+(?:Inicial|sugerido|mínimo)[:\s]*R\$\s*([\d.,]+)', container_text, re.IGNORECASE)
        if lance_match:
            price = parse_brl(lance_match.group(1))
        
        if not price:
            avaliacao_match = re.search(r'(?:Avaliação|Valor)[:\s]*R\$\s*([\d.,]+)', container_text, re.IGNORECASE)
            if avaliacao_match:
                price = parse_brl(avaliacao_match.group(1))
        
        if not price:
            price_matches = re.findall(r'R\$\s*([\d]{1,3}(?:\.[\d]{3})*(?:,\d{2})?)', container_text)
            for pm in price_matches:
                p = parse_brl(pm)
                if p and 10000 <= p <= 100000000:
                    price = p
                    break
        
        # Extrair data
        closing_date = None
        primeiro_leilao_match = re.search(r'1[ºo°]\s*leil[ãa]o[:\s]*(\d{1,2}/\d{1,2}/\d{4})', container_text, re.IGNORECASE)
        if primeiro_leilao_match:
            closing_date = parse_date(primeiro_leilao_match.group(1))
        
        if not closing_date:
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', container_text)
            if date_match:
                closing_date = parse_date(date_match.group(1))
        
        leiloes.append({
            'title': title,
            'price': price,
            'closing_date': closing_date,
            'url': full_url
        })
        
        if len(leiloes) >= 20:  # Limitar
            break
    
    # Estratégia 2: Procurar por cards/containers de leilões
    if len(leiloes) < 5:
        logger.info("Poucos leilões encontrados, tentando estratégia alternativa...")
        
        cards = soup.find_all(['div', 'article', 'section'], class_=lambda x: x and any(
            kw in x.lower() for kw in ['card', 'item', 'leilao', 'lote', 'imovel']
        ))
        
        for card in cards[:20]:
            card_text = card.get_text()
            
            if not any(kw in card_text.lower() for kw in ['leilão', 'lote', 'imóvel']):
                continue
            
            title_elem = card.find(['h2', 'h3', 'h4', 'h5', 'a'])
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            
            title_key = title.lower()[:50]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            
            # Extrair preço
            price = None
            lance_match = re.search(r'Lance\s+(?:Inicial|sugerido)[:\s]*R\$\s*([\d.,]+)', card_text, re.IGNORECASE)
            if lance_match:
                price = parse_brl(lance_match.group(1))
            
            if not price:
                price_matches = re.findall(r'R\$\s*([\d.,]+)', card_text)
                for pm in price_matches:
                    p = parse_brl(pm)
                    if p and 10000 <= p <= 100000000:
                        price = p
                        break
            
            # Extrair data
            closing_date = None
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', card_text)
            if date_match:
                closing_date = parse_date(date_match.group(1))
            
            # Procurar link
            link_elem = card.find('a', href=True)
            url = base_url
            if link_elem:
                href = link_elem.get('href')
                if href.startswith('/'):
                    url = base_url + href
                elif href.startswith('http'):
                    url = href
            
            leiloes.append({
                'title': title,
                'price': price,
                'closing_date': closing_date,
                'url': url
            })
            
            if len(leiloes) >= 20:
                break
    
    return leiloes

async def main():
    leiloes = await extrair_leiloes_pestana()
    
    # Formatar como JSON
    resultado = {
        'source': 'Pestana Leilões',
        'source_url': 'https://www.pestanaleiloes.com.br',
        'extracted_at': datetime.now().isoformat(),
        'total_leiloes': len(leiloes),
        'leiloes': leiloes
    }
    
    # Imprimir JSON formatado
    print("\n" + "="*60)
    print("RESULTADO EM JSON:")
    print("="*60)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    
    # Salvar em arquivo
    output_file = 'leilao-backend/scripts/pestana_leiloes.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ Resultado salvo em {output_file}")
    logger.info(f"✅ Total de leilões extraídos: {len(leiloes)}")

if __name__ == "__main__":
    asyncio.run(main())

