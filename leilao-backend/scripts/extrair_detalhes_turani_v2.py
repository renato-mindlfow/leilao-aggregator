"""
Script para extrair preço inicial e data de encerramento dos leilões do Turani
Versão melhorada que analisa a estrutura HTML da página de listagem
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

async def extrair_leiloes_da_listagem(url: str) -> list:
    """Extrai leilões diretamente da página de listagem"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Erro ao acessar site: Status {response.status_code}")
                return []
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            leiloes = []
            base_url = urlparse(url).scheme + '://' + urlparse(url).netloc
            
            # Salvar HTML para debug (opcional)
            # with open('debug_turani.html', 'w', encoding='utf-8') as f:
            #     f.write(html)
            
            # Estratégia 1: Procurar por links de leilões e extrair informações do contexto
            links = soup.find_all('a', href=True)
            
            seen_titles = set()
            
            for link in links:
                href = link.get('href', '')
                link_text = link.get_text(strip=True)
                
                # Verificar se é um link de leilão
                if not any(kw in href.lower() for kw in ['leilao', 'lote', 'imovel', '/imoveis/']):
                    continue
                
                # Construir URL completa
                if href.startswith('/'):
                    full_url = base_url + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = urljoin(url, href)
                
                # Encontrar o container pai que pode ter mais informações
                container = link.find_parent(['div', 'article', 'section', 'li', 'tr'])
                if not container:
                    container = link
                
                container_text = container.get_text()
                
                # Extrair título - limpar texto
                title = None
                # Tentar título do link
                if link_text and len(link_text) > 10:
                    title = link_text
                else:
                    # Procurar título em elementos próximos
                    title_elem = container.find(['h2', 'h3', 'h4', 'h5'])
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                
                if not title or len(title) < 10:
                    continue
                
                # Limpar título - remover textos comuns que não fazem parte do título
                # Remover prefixos comuns
                title = re.sub(r'^(COMPREISISTEMA|LEILÃO|ENCERRADO)\s*', '', title, flags=re.IGNORECASE)
                # Remover informações de avaliação e lance sugerido do título
                title = re.sub(r'Avalia[çc][ãa]o:.*?Lance sugerido:.*?$', '', title, flags=re.DOTALL | re.IGNORECASE)
                title = re.sub(r'Lance sugerido:.*?$', '', title, flags=re.DOTALL | re.IGNORECASE)
                title = re.sub(r'ABERTO PARA LANCE.*?$', '', title, flags=re.DOTALL | re.IGNORECASE)
                title = re.sub(r'ADICIONAR LANCE.*?$', '', title, flags=re.DOTALL | re.IGNORECASE)
                title = re.sub(r'\d+[ºo°]\s*leil[ãa]o:.*?$', '', title, flags=re.DOTALL | re.IGNORECASE)
                title = re.sub(r'\s+', ' ', title).strip()
                
                # Evitar duplicatas
                title_key = title.lower()[:50]
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                
                # Extrair preço - procurar por "Lance sugerido" primeiro, depois "Avaliação"
                price = None
                
                # Primeiro tentar "Lance sugerido" (preço inicial do leilão)
                lance_match = re.search(r'Lance\s+sugerido[:\s]*R\$\s*([\d.,]+)', container_text, re.IGNORECASE)
                if lance_match:
                    price = parse_brl(lance_match.group(1))
                
                # Se não encontrou, tentar "Avaliação" como fallback
                if not price:
                    avaliacao_match = re.search(r'Avalia[çc][ãa]o[:\s]*R\$\s*([\d.,]+)', container_text, re.IGNORECASE)
                    if avaliacao_match:
                        price = parse_brl(avaliacao_match.group(1))
                
                # Se ainda não encontrou, procurar qualquer preço grande
                if not price:
                    price_matches = re.findall(r'R\$\s*([\d]{1,3}(?:\.[\d]{3})*(?:,\d{2})?)', container_text)
                    for pm in price_matches:
                        p = parse_brl(pm)
                        if p and 10000 <= p <= 100000000:  # Valores razoáveis
                            price = p
                            break
                
                # Extrair data de encerramento - procurar por "1º leilão" primeiro
                closing_date = None
                
                # Primeiro tentar encontrar data do 1º leilão
                primeiro_leilao_match = re.search(r'1[ºo°]\s*leil[ãa]o[:\s]*(\d{1,2}/\d{1,2}/\d{4})', container_text, re.IGNORECASE)
                if primeiro_leilao_match:
                    closing_date = parse_date(primeiro_leilao_match.group(1))
                
                # Se não encontrou, procurar qualquer data
                if not closing_date:
                    date_patterns = [
                        r'(\d{1,2}/\d{1,2}/\d{4})',
                        r'(\d{1,2}/\d{1,2}/\d{2})',
                    ]
                    for pattern in date_patterns:
                        match = re.search(pattern, container_text)
                        if match:
                            closing_date = parse_date(match.group(1))
                            if closing_date:
                                break
                
                leiloes.append({
                    'title': title,
                    'price': price,
                    'closing_date': closing_date,
                    'url': full_url
                })
                
                if len(leiloes) >= 7:
                    break
            
            # Se não encontrou suficiente, tentar estratégia alternativa
            if len(leiloes) < 7:
                logger.info("Tentando estratégia alternativa de extração...")
                
                # Procurar por todos os elementos que podem conter informações de leilão
                all_elements = soup.find_all(['div', 'article', 'section', 'li'])
                
                for elem in all_elements:
                    elem_text = elem.get_text()
                    
                    # Verificar se parece ser um card de leilão
                    if not any(kw in elem_text.lower() for kw in ['leilão', 'lote', 'imóvel', 'apartamento', 'casa', 'terreno']):
                        continue
                    
                    # Extrair título
                    title_elem = elem.find(['h2', 'h3', 'h4', 'h5', 'a'])
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    if not title or len(title) < 10:
                        continue
                    
                    # Limpar título
                    title = re.sub(r'^(COMPREISISTEMA|LEILÃO|ENCERRADO)\s*', '', title, flags=re.IGNORECASE)
                    title = re.sub(r'Avalia[çc][ãa]o:.*?Lance sugerido:.*?$', '', title, flags=re.DOTALL | re.IGNORECASE)
                    title = re.sub(r'Lance sugerido:.*?$', '', title, flags=re.DOTALL | re.IGNORECASE)
                    title = re.sub(r'ABERTO PARA LANCE.*?$', '', title, flags=re.DOTALL | re.IGNORECASE)
                    title = re.sub(r'ADICIONAR LANCE.*?$', '', title, flags=re.DOTALL | re.IGNORECASE)
                    title = re.sub(r'\d+[ºo°]\s*leil[ãa]o:.*?$', '', title, flags=re.DOTALL | re.IGNORECASE)
                    title = re.sub(r'\s+', ' ', title).strip()
                    
                    # Evitar duplicatas
                    title_key = title.lower()[:50]
                    if title_key in seen_titles:
                        continue
                    seen_titles.add(title_key)
                    
                    # Extrair preço - procurar por "Lance sugerido" primeiro
                    price = None
                    
                    # Primeiro tentar "Lance sugerido"
                    lance_match = re.search(r'Lance\s+sugerido[:\s]*R\$\s*([\d.,]+)', elem_text, re.IGNORECASE)
                    if lance_match:
                        price = parse_brl(lance_match.group(1))
                    
                    # Se não encontrou, tentar "Avaliação"
                    if not price:
                        avaliacao_match = re.search(r'Avalia[çc][ãa]o[:\s]*R\$\s*([\d.,]+)', elem_text, re.IGNORECASE)
                        if avaliacao_match:
                            price = parse_brl(avaliacao_match.group(1))
                    
                    # Se ainda não encontrou, procurar qualquer preço grande
                    if not price:
                        price_matches = re.findall(r'R\$\s*([\d.,]+)', elem_text)
                        for pm in price_matches:
                            p = parse_brl(pm)
                            if p and 10000 <= p <= 100000000:
                                price = p
                                break
                    
                    # Extrair data - procurar por "1º leilão" primeiro
                    closing_date = None
                    
                    # Primeiro tentar encontrar data do 1º leilão
                    primeiro_leilao_match = re.search(r'1[ºo°]\s*leil[ãa]o[:\s]*(\d{1,2}/\d{1,2}/\d{4})', elem_text, re.IGNORECASE)
                    if primeiro_leilao_match:
                        closing_date = parse_date(primeiro_leilao_match.group(1))
                    
                    # Se não encontrou, procurar qualquer data
                    if not closing_date:
                        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', elem_text)
                        if date_match:
                            closing_date = parse_date(date_match.group(1))
                    
                    # Procurar link
                    link_elem = elem.find('a', href=True)
                    url_leilao = None
                    if link_elem:
                        href = link_elem.get('href')
                        if href.startswith('/'):
                            url_leilao = base_url + href
                        elif href.startswith('http'):
                            url_leilao = href
                    
                    leiloes.append({
                        'title': title,
                        'price': price,
                        'closing_date': closing_date,
                        'url': url_leilao or url
                    })
                    
                    if len(leiloes) >= 7:
                        break
            
            return leiloes
            
    except Exception as e:
        logger.error(f"Erro ao processar site: {e}")
        import traceback
        traceback.print_exc()
        return []

async def main():
    base_url = "https://www.turanileiloes.com.br/imoveis"
    
    logger.info(f"\n{'='*60}")
    logger.info(f"EXTRAINDO DETALHES DOS LEILÕES DO TURANI")
    logger.info(f"Site: {base_url}")
    logger.info("="*60)
    
    leiloes = await extrair_leiloes_da_listagem(base_url)
    
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

