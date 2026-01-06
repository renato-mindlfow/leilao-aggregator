"""
Verificar ofertas sem ID no Sold
"""
import requests

url = "https://offer-query.superbid.net/offers/"
params = {
    "portalId": "[2,15]",
    "requestOrigin": "store",
    "locale": "pt_BR",
    "timeZoneId": "America/Sao_Paulo",
    "searchType": "opened",
    "filter": "product.productType.description:imoveis;stores.id:[1161,1741]",
    "geoLocation": "true",
    "pageSize": 50,
}

for page in range(1, 4):
    params["pageNumber"] = page
    r = requests.get(url, params=params)
    data = r.json()
    offers = data.get("offers", [])
    
    sem_id = 0
    com_id = 0
    
    for offer in offers:
        offer_id = offer.get("id")
        if offer_id:
            com_id += 1
        else:
            sem_id += 1
            print(f"Pagina {page} - Oferta sem ID:")
            print(f"  auction.id: {offer.get('auction', {}).get('id')}")
            print(f"  linkURL: {offer.get('linkURL', 'N/A')}")
    
    print(f"\nPagina {page}: {com_id} com ID, {sem_id} sem ID")

