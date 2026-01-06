"""
Investigar API do Freitas Leiloeiro para descobrir como filtrar imóveis.
"""
import httpx
import json

BASE_URL = "https://www.freitasleiloeiro.com.br"

# Endpoints descobertos nas requisições de rede
endpoints = [
    "/Leiloes/ListarLeiloes",
    "/Leiloes/ListarLeiloes?cards=true",
    "/Leiloes/ListarLeiloesDestaques?tipoDestaque=1",
    "/Leiloes/PesquisarDestaques",
]

print("="*70)
print("INVESTIGANDO API FREITAS LEILOEIRO")
print("="*70)

headers = {
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': 'Mozilla/5.0',
    'Referer': BASE_URL + '/',
}

for endpoint in endpoints:
    try:
        url = BASE_URL + endpoint
        print(f"\nTestando: {endpoint}")
        r = httpx.get(url, headers=headers, timeout=10, verify=False)
        
        if r.status_code == 200:
            content_type = r.headers.get('content-type', '')
            if 'json' in content_type:
                data = r.json()
                print(f"  [OK] Retornou JSON")
                print(f"  Tipo: {type(data)}")
                if isinstance(data, list):
                    print(f"  Itens: {len(data)}")
                    if data:
                        print(f"  Primeiro item keys: {list(data[0].keys())[:5] if isinstance(data[0], dict) else 'N/A'}")
                elif isinstance(data, dict):
                    print(f"  Keys: {list(data.keys())[:5]}")
                    if 'leiloes' in data or 'items' in data or 'data' in data:
                        items = data.get('leiloes') or data.get('items') or data.get('data')
                        if items:
                            print(f"  Total itens: {len(items) if isinstance(items, list) else 'N/A'}")
            else:
                print(f"  [INFO] Retornou {content_type[:50]}")
        else:
            print(f"  [ERRO] Status: {r.status_code}")
    except Exception as e:
        print(f"  [ERRO] {str(e)[:100]}")

# Tentar descobrir parâmetros para filtrar imóveis
print("\n" + "="*70)
print("TESTANDO FILTROS DE IMÓVEIS")
print("="*70)

# Parâmetros comuns para filtrar imóveis
test_params = [
    {"Categoria": 3},  # Categoria 3 pode ser imóveis
    {"TipoLoteId": 3},
    {"categoria": "imoveis"},
    {"tipo": "imoveis"},
]

for params in test_params:
    try:
        url = BASE_URL + "/Leiloes/ListarLeiloes"
        r = httpx.get(url, params=params, headers=headers, timeout=10, verify=False)
        if r.status_code == 200 and 'json' in r.headers.get('content-type', ''):
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"\n[OK] Parâmetros {params} retornaram {len(data)} itens")
            elif isinstance(data, dict):
                items = data.get('leiloes') or data.get('items') or data.get('data')
                if items and len(items) > 0:
                    print(f"\n[OK] Parâmetros {params} retornaram {len(items)} itens")
    except:
        pass

