"""
Script para extrair preço inicial e data de encerramento dos leilões do Turani
Acessa cada página individual para extrair dados precisos
"""
import asyncio
import httpx
import logging
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse

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
    """Extrai detalhes de um leilão específico acessando sua página"""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Erro ao acessar {url}: Status {response.status_code}")
                return None
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()
            
            # Extrair título
            title = None
            title_selectors = ['h1', '.titulo', '.title', '.property-title', 'title']
            for selector in title_selectors:
                elem = soup.select_one(selector)
                if elem:
                    title = elem.get_text(strip=True)
                    if title and len(title) > 10:
                        break
            
            if not title:
                # Tentar meta tag
                meta_title = soup.find('meta', property='og:title')
                if meta_title:
                    title = meta_title.get('content', '').strip()
            
            # Limpar título
            if title:
                title = re.sub(r'^(COMPREISISTEMA|LEILÃO|ENCERRADO|CLASSICDIAMANTE)\s*', '', title, flags=re.IGNORECASE)
                title = re.sub(r'\s+', ' ', title).strip()
            
            # Extrair preço - procurar por "Lance sugerido" primeiro
            price = None
            lance_match = re.search(r'Lance\s+sugerido[:\s]*R\$\s*([\d.,]+)', page_text, re.IGNORECASE)
            if lance_match:
                price = parse_brl(lance_match.group(1))
            
            # Se não encontrou, tentar "Avaliação"
            if not price:
                avaliacao_match = re.search(r'Avalia[çc][ãa]o[:\s]*R\$\s*([\d.,]+)', page_text, re.IGNORECASE)
                if avaliacao_match:
                    price = parse_brl(avaliacao_match.group(1))
            
            # Extrair data de encerramento - procurar por "1º leilão"
            closing_date = None
            primeiro_leilao_match = re.search(r'1[ºo°]\s*leil[ãa]o[:\s]*(\d{1,2}/\d{1,2}/\d{4})', page_text, re.IGNORECASE)
            if primeiro_leilao_match:
                closing_date = parse_date(primeiro_leilao_match.group(1))
            
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
            seen_urls = set()
            
            # Procurar por links que parecem ser de leilões
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                
                # Verificar se é um link de leilão
                if not any(kw in href.lower() for kw in ['/imoveis/', 'leilao', 'lote']):
                    continue
                
                # Construir URL completa
                if href.startswith('/'):
                    full_url = base_url + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = urljoin(url, href)
                
                # Evitar duplicatas
                if full_url in seen_urls or full_url == url:
                    continue
                seen_urls.add(full_url)
                
                links.append(full_url)
            
            return links[:7]  # Limitar a 7 leilões
            
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
        logger.warning("Nenhum link encontrado na página de listagem")
        return
    
    logger.info(f"Encontrados {len(links)} links de leilões")
    
    # Extrair detalhes de cada leilão
    logger.info("\n2. Extraindo detalhes de cada leilão...")
    leiloes = []
    
    for i, link in enumerate(links, 1):
        logger.info(f"  [{i}/{len(links)}] Processando {link}...")
        detalhes = await extrair_detalhes_leilao(link, headers)
        if detalhes:
            leiloes.append(detalhes)
            logger.info(f"      ✅ Título: {detalhes['title'][:60]}...")
            logger.info(f"      ✅ Preço: R$ {detalhes['price']:,.2f}" if detalhes['price'] else "      ⚠️ Preço: não encontrado")
            logger.info(f"      ✅ Data: {detalhes['closing_date']}" if detalhes['closing_date'] else "      ⚠️ Data: não encontrada")
        await asyncio.sleep(1)  # Delay para não sobrecarregar o servidor
    
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

