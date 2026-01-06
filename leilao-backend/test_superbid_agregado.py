#!/usr/bin/env python3
"""
Teste do Scraper Superbid Agregado
Valida API REST e extração de dados
"""

import asyncio
import httpx
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# Configuração
CONFIG_PATH = Path("app/configs/sites/superbid_agregado.json")

# Headers para API Superbid
HEADERS = {
    'Accept': 'application/json',
    'Origin': 'https://www.superbid.net',
    'Referer': 'https://www.superbid.net/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


async def load_config() -> Dict:
    """Carrega configuração do scraper."""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


async def test_api_page(config: Dict, page: int = 1, page_size: int = 50) -> Optional[Dict]:
    """Testa uma página da API."""
    api_config = config['api']
    base_url = api_config['base_url']
    params = api_config['params'].copy()
    params[api_config['pagination_param']] = str(page)
    params['pageSize'] = str(page_size)
    
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(base_url, params=params, headers=HEADERS)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"  ERRO: HTTP {response.status_code}")
                print(f"  Resposta: {response.text[:200]}")
                return None
    except Exception as e:
        print(f"  ERRO na requisição: {e}")
        return None


def extract_property_data(offer: Dict) -> Dict:
    """Extrai dados relevantes de um imóvel."""
    prop = {
        'id': offer.get('id'),
        'title': None,
        'price': None,
        'location': None,
        'city': None,
        'state': None,
        'url': None,
        'image_url': None,
        'auctioneer': None,
        'store_id': None
    }
    
    # Título - usar product.shortDesc ou offerDescription
    product = offer.get('product', {})
    offer_desc = offer.get('offerDescription', {})
    
    prop['title'] = (
        product.get('shortDesc') or 
        offer_desc.get('offerDescription', '').split('<br>')[0].strip() or
        offer.get('title')
    )
    
    # Preço - direto do offer.price
    price = offer.get('price')
    if isinstance(price, (int, float)):
        prop['price'] = price
    elif isinstance(price, dict):
        prop['price'] = price.get('value') or price.get('amount')
    
    # Localização - usar product.location
    location = product.get('location', {})
    if location:
        city_str = location.get('city', '')
        state_str = location.get('state', '')
        
        # Extrair cidade e estado (formato pode ser "Gaspar - SC" ou separado)
        if city_str:
            if ' - ' in city_str:
                parts = city_str.split(' - ')
                prop['city'] = parts[0].strip()
                prop['state'] = parts[1].strip() if len(parts) > 1 else state_str
            else:
                prop['city'] = city_str
                prop['state'] = state_str
        
        if prop['city'] or prop['state']:
            prop['location'] = f"{prop['city'] or ''}, {prop['state'] or ''}".strip(', ')
    
    # URL - construir a partir do ID e auction
    auction = offer.get('auction', {})
    auction_id = auction.get('id')
    offer_id = offer.get('id')
    
    if offer_id:
        # Formato típico: https://www.superbid.net/leilao/{auction_id}/lote/{offer_id}
        if auction_id:
            prop['url'] = f"https://www.superbid.net/leilao/{auction_id}/lote/{offer_id}"
        else:
            prop['url'] = f"https://www.superbid.net/lote/{offer_id}"
    
    # Imagem - usar product.galleryJson ou thumbnailUrl
    gallery = product.get('galleryJson', [])
    if gallery and len(gallery) > 0:
        # Procurar primeira imagem destacada ou primeira imagem
        for img in gallery:
            if isinstance(img, dict):
                if img.get('highlight'):
                    prop['image_url'] = img.get('link')
                    break
        if not prop['image_url'] and gallery[0]:
            prop['image_url'] = gallery[0].get('link') if isinstance(gallery[0], dict) else gallery[0]
    
    if not prop['image_url']:
        prop['image_url'] = product.get('thumbnailUrl')
    
    # Leiloeiro/Store
    stores = offer.get('stores') or []
    if stores and len(stores) > 0:
        store = stores[0] if isinstance(stores[0], dict) else {'id': stores[0]}
        prop['store_id'] = store.get('id') if isinstance(store, dict) else store
        prop['auctioneer'] = store.get('name') if isinstance(store, dict) else None
    
    return prop


def validate_property(prop: Dict) -> tuple[bool, List[str]]:
    """Valida se um imóvel tem dados mínimos."""
    errors = []
    
    if not prop.get('id'):
        errors.append("Sem ID")
    if not prop.get('title'):
        errors.append("Sem título")
    if not prop.get('price'):
        errors.append("Sem preço")
    if not prop.get('url'):
        errors.append("Sem URL")
    
    return len(errors) == 0, errors


async def test_scraper(max_items: int = 500):
    """Testa o scraper com limite de itens."""
    print("=" * 80)
    print("TESTE DO SCRAPER SUPERBID AGREGADO")
    print("=" * 80)
    print(f"Limite: {max_items} imóveis")
    print(f"Config: {CONFIG_PATH}")
    print()
    
    # Carregar config
    try:
        config = await load_config()
        print(f"[OK] Config carregado: {config['name']}")
    except Exception as e:
        print(f"[ERRO] Erro ao carregar config: {e}")
        return
    
    # Testar primeira página
    print("\n[1] Testando API - Página 1...")
    data = await test_api_page(config, page=1, page_size=50)
    
    if not data:
        print("[ERRO] API não respondeu corretamente")
        return
    
    # Verificar estrutura
    total = data.get(config['api']['total_field'], 0)
    items = data.get(config['api']['items_field'], [])
    
    print(f"[OK] API respondeu com sucesso")
    print(f"  Total de imóveis: {total:,}")
    print(f"  Itens na página 1: {len(items)}")
    
    if total == 0:
        print("[AVISO] Total é 0 - verificar filtros da API")
        return
    
    if len(items) == 0:
        print("[AVISO] Nenhum item retornado - verificar estrutura da resposta")
        print(f"  Estrutura: {list(data.keys())}")
        return
    
    # Analisar primeiro item
    print("\n[2] Analisando estrutura dos dados...")
    first_item = items[0]
    print(f"  Chaves do item: {list(first_item.keys())[:10]}...")
    
    # Extrair dados
    print("\n[3] Extraindo dados dos imóveis...")
    properties = []
    page = 1
    page_size = 50
    errors = []
    
    while len(properties) < max_items:
        print(f"  Página {page}...", end=" ")
        
        data = await test_api_page(config, page=page, page_size=page_size)
        if not data:
            errors.append(f"Página {page}: Erro na requisição")
            break
        
        items = data.get(config['api']['items_field'], [])
        if not items:
            print("sem mais itens")
            break
        
        page_properties = []
        for item in items:
            prop = extract_property_data(item)
            is_valid, prop_errors = validate_property(prop)
            
            if is_valid:
                page_properties.append(prop)
            else:
                errors.append(f"Item {prop.get('id', '?')}: {', '.join(prop_errors)}")
        
        properties.extend(page_properties)
        print(f"{len(page_properties)} válidos (total: {len(properties)})")
        
        # Verificar se há mais páginas
        if len(items) < page_size:
            print("  Última página alcançada")
            break
        
        if len(properties) >= max_items:
            break
        
        page += 1
        await asyncio.sleep(0.5)  # Rate limiting
    
    # Resultados
    print("\n" + "=" * 80)
    print("RESULTADOS DO TESTE")
    print("=" * 80)
    print(f"Total de imóveis extraídos: {len(properties)}")
    print(f"Total disponível na API: {total:,}")
    print(f"Páginas processadas: {page}")
    print(f"Erros encontrados: {len(errors)}")
    
    # Exemplos
    if properties:
        print("\n[4] Exemplos de imóveis extraídos:")
        print("-" * 80)
        for i, prop in enumerate(properties[:5], 1):
            print(f"\nExemplo {i}:")
            print(f"  ID: {prop.get('id')}")
            print(f"  Título: {prop.get('title', 'N/A')[:80]}")
            print(f"  Preço: R$ {prop.get('price', 0):,.2f}" if prop.get('price') else "  Preço: N/A")
            print(f"  Localização: {prop.get('location', 'N/A')}")
            print(f"  Cidade/Estado: {prop.get('city', 'N/A')} / {prop.get('state', 'N/A')}")
            print(f"  URL: {prop.get('url', 'N/A')[:80]}")
            print(f"  Store ID: {prop.get('store_id', 'N/A')}")
            print(f"  Leiloeiro: {prop.get('auctioneer', 'N/A')}")
    
    # Erros
    if errors:
        print("\n[5] Erros encontrados:")
        print("-" * 80)
        for error in errors[:20]:  # Mostrar apenas primeiros 20
            print(f"  - {error}")
        if len(errors) > 20:
            print(f"  ... e mais {len(errors) - 20} erros")
    
    # Validação final
    print("\n[6] Validação Final:")
    print("-" * 80)
    
    if len(properties) > 0:
        print("[OK] Scraper funcionando corretamente")
        print(f"[OK] {len(properties)} imóveis extraídos com sucesso")
        
        # Estatísticas
        with_price = sum(1 for p in properties if p.get('price'))
        with_location = sum(1 for p in properties if p.get('location'))
        with_image = sum(1 for p in properties if p.get('image_url'))
        
        print(f"\nEstatísticas:")
        print(f"  Com preço: {with_price}/{len(properties)} ({with_price*100/len(properties):.1f}%)")
        print(f"  Com localização: {with_location}/{len(properties)} ({with_location*100/len(properties):.1f}%)")
        print(f"  Com imagem: {with_image}/{len(properties)} ({with_image*100/len(properties):.1f}%)")
        
        if len(properties) >= max_items:
            print(f"\n[AVISO] Limite de {max_items} imóveis atingido")
            print("  Execute com limite maior para extrair todos os imóveis")
    else:
        print("[ERRO] Nenhum imóvel válido extraído")
        print("  Verificar estrutura da API e mapeamento de campos")
    
    # Salvar amostra
    if properties:
        sample_file = Path("test_superbid_agregado_sample.json")
        with open(sample_file, 'w', encoding='utf-8') as f:
            json.dump(properties[:10], f, indent=2, ensure_ascii=False)
        print(f"\n[OK] Amostra salva em: {sample_file}")
    
    print("\n" + "=" * 80)


async def main():
    """Executa testes."""
    import sys
    
    # Teste inicial com 500 imóveis
    print("\n>>> TESTE INICIAL (500 imóveis) <<<\n")
    await test_scraper(max_items=500)
    
    # Executar teste completo automaticamente se não houver argumento --skip-full
    if '--skip-full' not in sys.argv:
        print("\n" + "=" * 80)
        print("TESTE COMPLETO (12.000 imóveis)")
        print("=" * 80)
        print("Executando teste completo automaticamente...")
        print("Isso pode levar alguns minutos...\n")
        
        await test_scraper(max_items=12000)
    else:
        print("\nTeste completo pulado (--skip-full)")


if __name__ == "__main__":
    asyncio.run(main())

