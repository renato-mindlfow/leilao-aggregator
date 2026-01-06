"""
Script para extrair leilões do site Pestana Leilões
Tenta acessar API e URLs específicas de imóveis
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

async def try_api_endpoint(base_url: str) -> list:
    """Tenta acessar API do site"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'pt-BR,pt;q=0.9',
        'Referer': base_url,
    }
    
    # Tentar endpoints de API comuns
    api_endpoints = [
        'https://api.pestanaleiloes.com.br/api/lotes?tipoBem=462&page=1&qty=50',
        'https://api.pestanaleiloes.com.br/lotes?tipoBem=462',
        'https://api.pestanaleiloes.com.br/api/imoveis',
        'https://api.pestanaleiloes.com.br/api/properties',
    ]
    
    for endpoint in api_endpoints:
        try:
            logger.info(f"Tentando API: {endpoint}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(endpoint, headers=headers)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        logger.info(f"✅ API retornou dados: {type(data)}")
                        # Processar dados da API
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict) and 'data' in data:
                            return data['data']
                        elif isinstance(data, dict) and 'lotes' in data:
                            return data['lotes']
                    except:
                        pass
        except Exception as e:
            logger.debug(f"Erro ao acessar {endpoint}: {e}")
            continue
    
    return []

async def try_imoveis_url(base_url: str) -> tuple[str | None, int]:
    """Tenta acessar URL específica de imóveis"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': base_url,
    }
    
    # URLs específicas de imóveis
    urls = [
        f'{base_url}/procurar-bens?tipoBem=462&lotePage=1&loteQty=50',
        f'{base_url}/imoveis',
        f'{base_url}/lotes?tipo=imovel',
        f'{base_url}/busca?tipoBem=462',
    ]
    
    for url in urls:
        try:
            logger.info(f"Tentando URL: {url}")
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    html = response.text
                    # Verificar se não é página de erro
                    if 'navegador incompatível' not in html.lower():
                        logger.info(f"✅ URL funcionou: {url}")
                        return html, response.status_code
        except Exception as e:
            logger.debug(f"Erro ao acessar {url}: {e}")
            continue
    
    return None, 0

async def extrair_leiloes_pestana():
    """Extrai leilões do site Pestana"""
    
    base_url = "https://www.pestanaleiloes.com.br"
    
    logger.info(f"\n{'='*60}")
    logger.info(f"EXTRAINDO LEILÕES DO PESTANA")
    logger.info(f"Site: {base_url}")
    logger.info("="*60)
    
    leiloes = []
    
    # Estratégia 1: Tentar API
    logger.info("\n1. Tentando acessar API...")
    api_data = await try_api_endpoint(base_url)
    if api_data:
        logger.info(f"✅ API retornou {len(api_data)} itens")
        # Processar dados da API
        for item in api_data[:20]:  # Limitar
            if isinstance(item, dict):
                title = item.get('titulo') or item.get('title') or item.get('descricao') or item.get('description')
                price = item.get('valor') or item.get('price') or item.get('lanceInicial') or item.get('lance_inicial')
                date = item.get('dataLeilao') or item.get('data_leilao') or item.get('data') or item.get('closingDate')
                url = item.get('url') or item.get('link')
                
                if title:
                    leiloes.append({
                        'title': str(title),
                        'price': parse_brl(str(price)) if price else None,
                        'closing_date': parse_date(str(date)) if date else None,
                        'url': urljoin(base_url, str(url)) if url else base_url
                    })
    
    # Estratégia 2: Tentar URL específica de imóveis
    if len(leiloes) == 0:
        logger.info("\n2. Tentando URL específica de imóveis...")
        html, status = await try_imoveis_url(base_url)
        
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Procurar por dados em scripts JSON-LD ou variáveis JavaScript
            scripts = soup.find_all('script')
            for script in scripts:
                script_text = script.string or ''
                # Procurar por JSON no JavaScript
                json_matches = re.findall(r'\{[^{}]*"titulo"[^{}]*\}', script_text, re.IGNORECASE)
                for match in json_matches:
                    try:
                        data = json.loads(match)
                        if 'titulo' in data or 'title' in data:
                            leiloes.append({
                                'title': data.get('titulo') or data.get('title', ''),
                                'price': parse_brl(str(data.get('valor') or data.get('price', ''))),
                                'closing_date': parse_date(str(data.get('data') or data.get('date', ''))),
                                'url': base_url
                            })
                    except:
                        pass
            
            # Procurar por links e cards
            links = soup.find_all('a', href=True)
            seen_titles = set()
            
            for link in links:
                href = link.get('href', '')
                if not any(kw in href.lower() for kw in ['lote', 'imovel', 'leilao']):
                    continue
                
                container = link.find_parent(['div', 'article', 'section'])
                if not container:
                    continue
                
                container_text = container.get_text()
                title = link.get_text(strip=True)
                
                if not title or len(title) < 10:
                    title_elem = container.find(['h2', 'h3', 'h4'])
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                
                if not title or len(title) < 10:
                    continue
                
                title_key = title.lower()[:50]
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                
                # Extrair preço e data
                price = None
                price_match = re.search(r'R\$\s*([\d.,]+)', container_text)
                if price_match:
                    price = parse_brl(price_match.group(1))
                
                closing_date = None
                date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', container_text)
                if date_match:
                    closing_date = parse_date(date_match.group(1))
                
                full_url = urljoin(base_url, href) if href.startswith('/') else (href if href.startswith('http') else urljoin(base_url, href))
                
                leiloes.append({
                    'title': title,
                    'price': price,
                    'closing_date': closing_date,
                    'url': full_url
                })
                
                if len(leiloes) >= 20:
                    break
    
    # Se ainda não encontrou, criar JSON vazio com sugestões
    if len(leiloes) == 0:
        logger.warning("\n⚠️ Nenhum leilão encontrado")
        logger.info("\n📝 DIAGNÓSTICO E SUGESTÕES DE BYPASS:")
        logger.info("   O site Pestana Leilões usa:")
        logger.info("   1. JavaScript para renderizar conteúdo (SPA)")
        logger.info("   2. Verificação de navegador compatível")
        logger.info("   3. Possível API em: api.pestanaleiloes.com.br")
        logger.info("\n   SOLUÇÕES RECOMENDADAS:")
        logger.info("   1. ✅ Usar Selenium/Playwright com navegador real")
        logger.info("   2. ✅ Usar o PestanaScraper existente (app/scrapers/pestana_scraper.py)")
        logger.info("   3. ✅ Tentar acessar API diretamente com autenticação")
        logger.info("   4. ✅ Usar serviço de scraping como ScrapingBee")
        logger.info("   5. ✅ Analisar requisições XHR/Fetch no DevTools do navegador")
    
    return leiloes

async def main():
    leiloes = await extrair_leiloes_pestana()
    
    # Formatar como JSON
    resultado = {
        'source': 'Pestana Leilões',
        'source_url': 'https://www.pestanaleiloes.com.br',
        'extracted_at': datetime.now().isoformat(),
        'total_leiloes': len(leiloes),
        'leiloes': leiloes,
        'note': 'Site requer JavaScript. Use Selenium/Playwright para acesso completo.' if len(leiloes) == 0 else None
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

