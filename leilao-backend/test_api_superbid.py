import httpx

# Testar portalId 1 (Superbid)
r1 = httpx.get(
    'https://offer-query.superbid.net/offers/?portalId=1&filter=product.productType.description:imoveis&pageNumber=1&pageSize=10',
    headers={'Accept': 'application/json', 'Origin': 'https://www.superbid.net'},
    timeout=10
)
if r1.status_code == 200:
    data1 = r1.json()
    print(f"Portal 1 (Superbid): {data1.get('total', 0)} imoveis")
else:
    print(f"Portal 1: Erro {r1.status_code}")

# Testar portalId 2 (Sold)
r2 = httpx.get(
    'https://offer-query.superbid.net/offers/?portalId=2&filter=product.productType.description:imoveis&pageNumber=1&pageSize=10',
    headers={'Accept': 'application/json', 'Origin': 'https://www.superbid.net'},
    timeout=10
)
if r2.status_code == 200:
    data2 = r2.json()
    print(f"Portal 2 (Sold): {data2.get('total', 0)} imoveis")
else:
    print(f"Portal 2: Erro {r2.status_code}")

