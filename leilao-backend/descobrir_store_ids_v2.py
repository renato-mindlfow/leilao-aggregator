"""
Descobrir store.id específico de cada leiloeiro - VERSÃO 2
Acessa cada site e procura o store.id no HTML/JavaScript
"""
import httpx
import json
import re
from pathlib import Path
from typing import Optional, Dict, List

SITES = [
    {"id": "lancenoleilao", "name": "Lance no Leilão", "url": "https://www.lancenoleilao.com.br"},
    {"id": "lut", "name": "LUT", "url": "https://www.lut.com.br"},
    {"id": "bigleilao", "name": "Big Leilão", "url": "https://www.bigleilao.com.br"},
    {"id": "vialeiloes", "name": "Via Leilões", "url": "https://www.vialeiloes.com.br"},
    {"id": "freitasleiloeiro", "name": "Freitas Leiloeiro", "url": "https://www.freitasleiloeiro.com.br"},
    {"id": "frazaoleiloes", "name": "Frazão Leilões", "url": "https://www.frazaoleiloes.com.br"},
    {"id": "francoleiloes", "name": "Franco Leilões", "url": "https://www.francoleiloes.com.br"},
    {"id": "leiloesfreire", "name": "Leilões Freire", "url": "https://www.leiloesfreire.com.br"},
    {"id": "bfrcontabil", "name": "BFR Contábil", "url": "https://www.bfrcontabil.com.br"},
]

API_BASE = "https://offer-query.superbid.net/offers/"
CONFIG_DIR = Path("app/configs/sites")

def extract_store_id_from_html(html: str, site_url: str) -> List[int]:
    """Extrai possíveis store.ids do HTML/JavaScript"""
    store_ids = []
    
    # Padrões para procurar store.id
    patterns = [
        # JavaScript: storeId: 123, "storeId": 123, 'storeId': 123
        r'store[Ii]d["\']?\s*[:=]\s*(\d+)',
        r'store[_-]?id["\']?\s*[:=]\s*(\d+)',
        r'"storeId"\s*:\s*(\d+)',
        r"'storeId'\s*:\s*(\d+)",
        # stores.id: [123] ou stores.id:123
        r'stores\.id\s*:\s*\[?(\d+)',
        r'stores\["id"\]\s*[:=]\s*(\d+)',
        # API calls: stores.id:[123]
        r'stores\.id\s*:\s*\[(\d+)\]',
        r'stores\.id\s*=\s*(\d+)',
        # URL parameters
        r'store[Ii]d=(\d+)',
        r'store[_-]?id=(\d+)',
        # JSON embedded
        r'"store"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)',
        r"'store'\s*:\s*\{[^}]*'id'\s*:\s*(\d+)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html)
        for match in matches:
            if match.isdigit():
                store_id = int(match)
                if 1 <= store_id <= 10000:  # Range razoável
                    store_ids.append(store_id)
    
    return list(set(store_ids))  # Remove duplicados

def test_store_id(store_id: int, portal_id: str, site_url: str) -> Optional[Dict]:
    """Testa um store.id específico"""
    try:
        url = f"{API_BASE}?portalId={portal_id}&filter=product.productType.description:imoveis;stores.id:[{store_id}]&pageNumber=1&pageSize=10"
        r = httpx.get(
            url,
            headers={
                'Accept': 'application/json',
                'Origin': site_url,
                'Referer': site_url + '/',
            },
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            total = data.get('total', 0)
            if total > 0:
                # Verificar se os imóveis realmente pertencem a este store
                offers = data.get('offers', [])
                if offers:
                    # Verificar o store.id do primeiro imóvel
                    first_store = offers[0].get('store', {}).get('id')
                    if first_store == store_id:
                        return {
                            "store_id": store_id,
                            "portal_id": portal_id,
                            "total": total
                        }
    except:
        pass
    return None

def find_store_id_for_site(site: Dict) -> Optional[Dict]:
    """Encontra o store.id de um site"""
    print(f"\n{site['name']} ({site['url']})")
    print("-" * 70)
    
    # 1. Buscar no HTML da página principal
    print("  [1/3] Buscando store.id no HTML...")
    try:
        r = httpx.get(site['url'], timeout=15, follow_redirects=True)
        html = r.text
        
        store_ids_found = extract_store_id_from_html(html, site['url'])
        if store_ids_found:
            print(f"    Encontrados {len(store_ids_found)} possíveis store.ids: {store_ids_found[:5]}")
            
            # Testar cada um
            for store_id in store_ids_found[:10]:  # Testa até 10
                result = test_store_id(store_id, "2", site['url'])
                if result:
                    print(f"    [OK] Store ID {store_id} confirmado! Total: {result['total']} imoveis")
                    return result
    except Exception as e:
        print(f"    [ERRO] Erro ao buscar HTML: {e}")
    
    # 2. Tentar acessar página de imóveis
    print("  [2/3] Tentando acessar página de imóveis...")
    imoveis_urls = [
        f"{site['url']}/imoveis",
        f"{site['url']}/leilao-de-imoveis",
        f"{site['url']}/leiloes/imoveis",
        f"{site['url']}/categoria/imoveis",
    ]
    
    for imoveis_url in imoveis_urls:
        try:
            r = httpx.get(imoveis_url, timeout=10, follow_redirects=True)
            if r.status_code == 200:
                html = r.text
                store_ids_found = extract_store_id_from_html(html, site['url'])
                if store_ids_found:
                    print(f"    Encontrados store.ids na página de imóveis: {store_ids_found[:5]}")
                    for store_id in store_ids_found[:10]:
                        result = test_store_id(store_id, "2", site['url'])
                        if result:
                            print(f"    [OK] Store ID {store_id} confirmado! Total: {result['total']} imoveis")
                            return result
        except:
            continue
    
    # 3. Testar range de IDs comuns (fallback)
    print("  [3/3] Testando IDs comuns...")
    common_ids = list(range(100, 2000, 50))  # Testa de 100 em 100 até 2000
    for store_id in common_ids:
        result = test_store_id(store_id, "2", site['url'])
        if result and result['total'] < 50000:  # Se retornar menos que o total geral, pode ser específico
            print(f"    [OK] Store ID {store_id} encontrado! Total: {result['total']} imoveis")
            return result
    
    print(f"  [WARN] Nenhum store.id específico encontrado")
    return None

print("="*70)
print("DESCOBRINDO store.id ESPECÍFICO DE CADA LEILOEIRO - V2")
print("="*70)

results = []

for site in SITES:
    store_info = find_store_id_for_site(site)
    
    if store_info:
        # Atualizar config
        config_file = CONFIG_DIR / f"{site['id']}.json"
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        filter_str = f"product.productType.description:imoveis;stores.id:[{store_info['store_id']}]"
        config['api']['params']['filter'] = filter_str
        config['api']['params']['portalId'] = store_info['portal_id']
        config['notes'] = [
            f"API Superbid - Portal ID {store_info['portal_id']} - Store ID {store_info['store_id']} - {store_info['total']} imoveis - VALIDADO"
        ]
        config['enabled'] = True
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        results.append({
            'site': site['name'],
            'store_id': store_info['store_id'],
            'portal_id': store_info['portal_id'],
            'imoveis': store_info['total'],
            'status': 'OK'
        })
    else:
        results.append({
            'site': site['name'],
            'store_id': 'N/A',
            'portal_id': 'N/A',
            'imoveis': 0,
            'status': 'NÃO ENCONTRADO'
        })

print("\n" + "="*70)
print("RESUMO FINAL")
print("="*70)
print(f"{'Site':<25} {'store.id':<10} {'Portal ID':<10} {'Imóveis':<10} {'Status'}")
print("-"*70)
for r in results:
    print(f"{r['site']:<25} {str(r['store_id']):<10} {str(r['portal_id']):<10} {r['imoveis']:<10} {r['status']}")

