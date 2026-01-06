"""
Debug: Verificar duplicados no Sold
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

# Buscar todas as 3 páginas
all_offer_ids = []
all_auction_ids = []

for page in range(1, 4):
    params["pageNumber"] = page
    r = requests.get(url, params=params)
    data = r.json()
    offers = data.get("offers", [])
    
    print(f"\nPágina {page}: {len(offers)} ofertas")
    
    for offer in offers:
        offer_id = offer.get("id")
        auction_id = offer.get("auction", {}).get("id")
        
        if offer_id:
            all_offer_ids.append((page, offer_id))
        if auction_id:
            all_auction_ids.append((page, auction_id))

# Verificar duplicados
from collections import Counter

offer_id_counts = Counter([oid for _, oid in all_offer_ids])
auction_id_counts = Counter([aid for _, aid in all_auction_ids])

duplicate_offers = {k: v for k, v in offer_id_counts.items() if v > 1}
duplicate_auctions = {k: v for k, v in auction_id_counts.items() if v > 1}

print(f"\nTotal de offer_ids únicos: {len(offer_id_counts)}")
print(f"Total de auction_ids únicos: {len(auction_id_counts)}")
print(f"Total de ofertas processadas: {len(all_offer_ids)}")

if duplicate_offers:
    print(f"\n[AVISO] Offer IDs duplicados: {len(duplicate_offers)}")
    for oid, count in list(duplicate_offers.items())[:5]:
        print(f"  offer.id {oid}: aparece {count} vezes")
        # Mostrar em quais paginas
        pages = [p for p, o in all_offer_ids if o == oid]
        print(f"    Paginas: {pages}")

if duplicate_auctions:
    print(f"\n[AVISO] Auction IDs duplicados: {len(duplicate_auctions)}")
    for aid, count in list(duplicate_auctions.items())[:5]:
        print(f"  auction.id {aid}: aparece {count} vezes")

# Verificar se todos os offer_ids da página 3 já existem nas páginas anteriores
print(f"\nVerificando se ofertas da pagina 3 ja existem nas paginas 1-2:")
page3_offer_ids = [oid for p, oid in all_offer_ids if p == 3]
page1_2_offer_ids = set([oid for p, oid in all_offer_ids if p in [1, 2]])

duplicados_pag3 = [oid for oid in page3_offer_ids if oid in page1_2_offer_ids]
print(f"  Ofertas da pagina 3 que ja existem nas paginas 1-2: {len(duplicados_pag3)}")
if duplicados_pag3:
    print(f"  IDs duplicados: {duplicados_pag3[:10]}")

