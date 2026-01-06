"""Validação rápida do LOTE 1 - Sites Superbid/White-label"""
import httpx
import json
from pathlib import Path

SITES = [
    {"id": "superbid", "name": "Superbid", "url": "https://www.superbid.net"},
    {"id": "lancenoleilao", "name": "Lance no Leilão", "url": "https://www.lancenoleilao.com.br"},
    {"id": "lut", "name": "LUT", "url": "https://www.lut.com.br"},
    {"id": "bigleilao", "name": "Big Leilão", "url": "https://www.bigleilao.com.br"},
    {"id": "vialeiloes", "name": "Via Leilões", "url": "https://www.vialeiloes.com.br"},
]

API_BASE = "https://offer-query.superbid.net/offers/"
CONFIG_DIR = Path("app/configs/sites")

def test_portal_ids(site):
    """Testa diferentes portalIds para encontrar o correto"""
    results = {}
    for portal_id in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        try:
            url = f"{API_BASE}?portalId={portal_id}&filter=product.productType.description:imoveis&pageNumber=1&pageSize=10"
            r = httpx.get(
                url,
                headers={'Accept': 'application/json', 'Origin': site['url']},
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                total = data.get('total', 0)
                if total > 0:
                    results[portal_id] = total
        except:
            continue
    return results

print("="*70)
print("VALIDAÇÃO LOTE 1 - Sites Superbid/White-label")
print("="*70)

results_table = []

for site in SITES:
    print(f"\n{site['name']} ({site['url']})")
    print("-" * 70)
    
    # Testar portalIds
    portal_results = test_portal_ids(site)
    
    if portal_results:
        # Pegar o portalId com mais imóveis
        best_portal = max(portal_results.items(), key=lambda x: x[1])
        portal_id = str(best_portal[0])
        total = best_portal[1]
        
        print(f"  [OK] API encontrada! Portal ID: {portal_id}, Total: {total} imóveis")
        
        # Atualizar config
        config_file = CONFIG_DIR / f"{site['id']}.json"
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config['enabled'] = True
        config['method'] = 'api_rest'
        config['api']['params']['portalId'] = portal_id
        config['notes'] = [f"API Superbid - Portal ID {portal_id} - {total} imoveis - VALIDADO"]
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        results_table.append({
            'site': site['name'],
            'tem_imoveis': 'SIM',
            'url': '',
            'metodo': 'api_rest',
            'imoveis': total,
            'status': 'OK'
        })
    else:
        print(f"  [WARN] Nenhuma API encontrada ou sem imóveis")
        # Desabilitar
        config_file = CONFIG_DIR / f"{site['id']}.json"
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config['enabled'] = False
        config['notes'] = ["Nenhuma API Superbid encontrada com imóveis - REQUER ANÁLISE MANUAL"]
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        results_table.append({
            'site': site['name'],
            'tem_imoveis': 'NÃO',
            'url': 'N/A',
            'metodo': 'N/A',
            'imoveis': 0,
            'status': 'DESABILITADO'
        })

print("\n" + "="*70)
print("RESUMO")
print("="*70)
print(f"{'Site':<25} {'Tem Imóveis?':<15} {'URL':<10} {'Método':<12} {'Imóveis':<10} {'Status'}")
print("-"*70)
for r in results_table:
    print(f"{r['site']:<25} {r['tem_imoveis']:<15} {r['url']:<10} {r['metodo']:<12} {r['imoveis']:<10} {r['status']}")

