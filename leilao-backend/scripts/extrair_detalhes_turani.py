"""
Script para extrair preço inicial e data de encerramento dos leilões do Turani
Formata como JSON para validação no orquestrador
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

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    
    # Padrões comuns de data brasileira
    patterns = [
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%d/%m/%Y'),
        (r'(\d{1,2})/(\d{1,2})/(\d{2})', '%d/%m/%y'),
        (r'(\d{1,2})-(\d{1,2})-(\d{4})', '%d-%m-%Y'),
    ]
    
    for pattern, fmt in patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                dt = datetime.strptime(match.group(0), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
    
    return None

async def extrair_detalhes_leilao(url: str, headers: dict) -> dict | None:
    """Extrai detalhes de um leilão específico"""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Erro ao acessar {url}: Status {response.status_code}")
                return None
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extrair título
            title = None
            title_selectors = ['h1', '.titulo', '.title', '.property-title', '.leilao-titulo']
            for selector in title_selectors:
                elem = soup.select_one(selector)
                if elem:
                    title = elem.get_text(strip=True)
                    if title and len(title) > 10:
                        break
            
            if not title:
                # Tentar encontrar título em meta tags
                meta_title = soup.find('meta', property='og:title')
                if meta_title:
                    title = meta_title.get('content', '').strip()
            
            # Extrair preço inicial
            price = None
            page_text = soup.get_text()
            
            # Padrões para encontrar preço inicial
            price_patterns = [
                r'Lance\s*Inicial[:\s]*R\$\s*([\d.,]+)',
                r'1[ºo°]\s*Leil[aã]o[:\s]*R\$\s*([\d.,]+)',
                r'Valor\s*Inicial[:\s]*R\$\s*([\d.,]+)',
                r'Pre[çc]o\s*Inicial[:\s]*R\$\s*([\d.,]+)',
                r'R\$\s*([\d]{1,3}(?:\.[\d]{3})*(?:,\d{2})?)\s*(?:lance|inicial|valor)',
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    price = parse_brl(match.group(1))
                    if price and price > 1000:  # Filtrar valores muito baixos
                        break
            
            # Se não encontrou, procurar todos os preços e pegar o maior
            if not price:
                all_prices = re.findall(r'R\$\s*([\d.,]+)', page_text)
                prices = [parse_brl(p) for p in all_prices if parse_brl(p)]
                if prices:
                    # Pegar o maior preço que seja razoável (entre 10k e 100M)
                    valid_prices = [p for p in prices if 10000 <= p <= 100000000]
                    if valid_prices:
                        price = max(valid_prices)
            
            # Extrair data de encerramento
            closing_date = None
            
            # Padrões para encontrar data de encerramento
            date_patterns = [
                r'Encerramento[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'Data\s*de\s*Encerramento[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'Fim\s*do\s*Leil[ãa]o[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'1[ºo°]\s*Leil[aã]o[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'Data\s*do\s*Leil[ãa]o[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    closing_date = parse_date(match.group(1))
                    if closing_date:
                        break
            
            # Se não encontrou, procurar por datas próximas a palavras-chave
            if not closing_date:
                # Procurar por padrão "DD/MM/YYYY" próximo a palavras-chave
                date_with_context = re.search(
                    r'(?:encerramento|leil[ãa]o|data|fim)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                    page_text, re.IGNORECASE
                )
                if date_with_context:
                    closing_date = parse_date(date_with_context.group(1))
            
            return {
                'title': title or 'Título não encontrado',
                'price': price,
                'closing_date': closing_date,
                'url': url
            }
            
    except Exception as e:
        logger.error(f"Erro ao extrair detalhes de {url}: {e}")
        return None

async def encontrar_links_leiloes(url: str, headers: dict) -> list:
    """Encontra links para páginas de detalhes dos leilões"""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Erro ao acessar site: Status {response.status_code}")
                return []
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            links = []
            base_url = urlparse(url).scheme + '://' + urlparse(url).netloc
            
            # Procurar por links que parecem ser de leilões
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Verificar se o link parece ser de um leilão
                if any(keyword in href.lower() or keyword in text.lower() 
                       for keyword in ['leilao', 'lote', 'imovel', 'property', 'auction']):
                    # Construir URL completa
                    if href.startswith('/'):
                        full_url = base_url + href
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = urljoin(url, href)
                    
                    # Verificar se não é a mesma página
                    if full_url != url and full_url not in links:
                        links.append(full_url)
            
            return links[:20]  # Limitar a 20 links
            
    except Exception as e:
        logger.error(f"Erro ao encontrar links: {e}")
        return []

async def main():
    base_url = "https://www.turanileiloes.com.br/imoveis"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"EXTRAINDO DETALHES DOS LEILÕES DO TURANI")
    logger.info(f"Site: {base_url}")
    logger.info("="*60)
    
    # Encontrar links dos leilões
    logger.info("\n1. Buscando links dos leilões...")
    links = await encontrar_links_leiloes(base_url, headers)
    
    if not links:
        logger.warning("Nenhum link encontrado. Tentando estratégia alternativa...")
        # Tentar extrair diretamente da página de listagem
        links = [base_url]  # Pelo menos tentar a própria página
    
    logger.info(f"Encontrados {len(links)} links")
    
    # Extrair detalhes de cada leilão
    logger.info("\n2. Extraindo detalhes de cada leilão...")
    leiloes = []
    
    for i, link in enumerate(links[:7], 1):  # Limitar aos primeiros 7
        logger.info(f"  [{i}/{min(len(links), 7)}] Processando {link}...")
        detalhes = await extrair_detalhes_leilao(link, headers)
        if detalhes:
            leiloes.append(detalhes)
        await asyncio.sleep(1)  # Delay para não sobrecarregar o servidor
    
    # Se não encontrou detalhes suficientes, tentar extrair da página de listagem
    if len(leiloes) < 7:
        logger.info("\n3. Tentando extrair da página de listagem...")
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(base_url, headers=headers)
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                # Procurar por cards ou itens de leilão
                # Primeiro, tentar encontrar estrutura específica do site
                cards = []
                
                # Estratégia 1: Procurar por elementos com classes específicas
                for tag in ['div', 'article', 'section', 'li']:
                    elements = soup.find_all(tag, class_=lambda x: x and any(kw in x.lower() for kw in ['card', 'item', 'leilao', 'lote', 'imovel']))
                    cards.extend(elements)
                
                # Estratégia 2: Se não encontrou, procurar por estrutura de lista
                if not cards:
                    # Procurar por links que parecem ser de leilões
                    links = soup.find_all('a', href=re.compile(r'leilao|lote|imovel', re.I))
                    for link in links:
                        parent = link.find_parent(['div', 'article', 'section', 'li'])
                        if parent and parent not in cards:
                            cards.append(parent)
                
                for card in cards[:7]:
                    title_elem = card.find(['h2', 'h3', 'h4', 'a'])
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        
                        # Procurar preço no card
                        card_text = card.get_text()
                        price = None
                        price_match = re.search(r'R\$\s*([\d.,]+)', card_text)
                        if price_match:
                            price = parse_brl(price_match.group(1))
                        
                        # Procurar data no card
                        closing_date = None
                        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', card_text)
                        if date_match:
                            closing_date = parse_date(date_match.group(1))
                        
                        # Procurar link
                        link_elem = card.find('a', href=True)
                        url = None
                        if link_elem:
                            href = link_elem.get('href')
                            if href.startswith('/'):
                                url = urlparse(base_url).scheme + '://' + urlparse(base_url).netloc + href
                            elif href.startswith('http'):
                                url = href
                        
                        if title and len(title) > 10:
                            leiloes.append({
                                'title': title,
                                'price': price,
                                'closing_date': closing_date,
                                'url': url or base_url
                            })
    
    # Formatar como JSON
    resultado = {
        'source': 'Turanileiloes',
        'source_url': base_url,
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
    output_file = 'leilao-backend/scripts/turani_leiloes.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ Resultado salvo em {output_file}")
    logger.info(f"✅ Total de leilões extraídos: {len(leiloes)}")

if __name__ == "__main__":
    asyncio.run(main())

