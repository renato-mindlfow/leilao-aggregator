"""
Descobrir store.id específico de cada leiloeiro na API Superbid.
"""
import httpx
import json
import re
from pathlib import Path
from typing import Optional, Dict

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

# Store IDs conhecidos (do Sold: 1161, 1741)
# Vamos testar um range amplo
STORE_IDS_TO_TEST = list(range(1, 2000))  # Testa IDs de 1 a 1999

def find_store_id(site: Dict, portal_id: str = "2") -> Optional[Dict]:
    """
    Tenta descobrir o store.id específico de um site.
    Estratégia: testa diferentes store.ids e vê qual retorna imóveis.
    """
    print(f"  Testando store.ids para {site['name']}...")
    
    headers = {
        'Accept': 'application/json',
        'Origin': site['url'],
        'Referer': site['url'] + '/',
    }
    
    # Primeiro, vamos tentar buscar na página HTML do site
    # para ver se há alguma referência ao store.id
    try:
        r = httpx.get(site['url'], timeout=10)
        html = r.text
        
        # Procurar por padrões como storeId, store_id, storeId: X, etc
        patterns = [
            r'store[Ii]d["\']?\s*[:=]\s*(\d+)',
            r'store[_-]?id["\']?\s*[:=]\s*(\d+)',
            r'"storeId"\s*:\s*(\d+)',
            r"'storeId'\s*:\s*(\d+)",
            r'stores\.id\s*:\s*\[?(\d+)',
        ]
        
        found_ids = []
        for pattern in patterns:
            matches = re.findall(pattern, html)
            found_ids.extend([int(m) for m in matches if m.isdigit()])
        
        if found_ids:
            # Testar os IDs encontrados
            for store_id in set(found_ids):
                try:
                    url = f"{API_BASE}?portalId={portal_id}&filter=product.productType.description:imoveis;stores.id:[{store_id}]&pageNumber=1&pageSize=10"
                    r = httpx.get(url, headers=headers, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        total = data.get('total', 0)
                        if total > 0:
                            print(f"    [OK] Store ID {store_id} encontrado no HTML! Total: {total} imoveis")
                            return {
                                "store_id": store_id,
                                "portal_id": portal_id,
                                "total": total
                            }
                except:
                    continue
    except:
        pass
    
    # Se não encontrou no HTML, testa um range menor de IDs comuns
    # (mais rápido que testar 2000 IDs)
    common_ids = [1161, 1741, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500]
    
    print(f"  Testando {len(common_ids)} store.ids comuns...")
    for store_id in common_ids:
        try:
            url = f"{API_BASE}?portalId={portal_id}&filter=product.productType.description:imoveis;stores.id:[{store_id}]&pageNumber=1&pageSize=10"
            r = httpx.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                total = data.get('total', 0)
                if total > 0:
                    # Verificar se os imóveis retornados realmente pertencem a este store
                    offers = data.get('offers', [])
                    if offers:
                        first_store = offers[0].get('store', {}).get('id')
                        if first_store == store_id:
                            print(f"    [OK] Store ID {store_id} confirmado! Total: {total} imoveis")
                            return {
                                "store_id": store_id,
                                "portal_id": portal_id,
                                "total": total
                            }
        except:
            continue
    
    print(f"  [WARN] Nenhum store.id encontrado")
    return None

def update_config(site: Dict, store_info: Dict):
    """Atualiza o config com o store.id descoberto"""
    config_file = CONFIG_DIR / f"{site['id']}.json"
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Atualizar filtro com store.id
    filter_str = f"product.productType.description:imoveis;stores.id:[{store_info['store_id']}]"
    config['api']['params']['filter'] = filter_str
    config['api']['params']['portalId'] = store_info['portal_id']
    config['notes'] = [
        f"API Superbid - Portal ID {store_info['portal_id']} - Store ID {store_info['store_id']} - {store_info['total']} imoveis - VALIDADO"
    ]
    config['enabled'] = True
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

print("="*70)
print("DESCOBRINDO store.id DE CADA LEILOEIRO")
print("="*70)

results = []

for site in SITES:
    print(f"\n{site['name']} ({site['url']})")
    print("-" * 70)
    
    store_info = find_store_id(site)
    
    if store_info:
        update_config(site, store_info)
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
print("RESUMO")
print("="*70)
print(f"{'Site':<25} {'store.id':<10} {'Portal ID':<10} {'Imóveis':<10} {'Status'}")
print("-"*70)
for r in results:
    print(f"{r['site']:<25} {str(r['store_id']):<10} {str(r['portal_id']):<10} {r['imoveis']:<10} {r['status']}")

