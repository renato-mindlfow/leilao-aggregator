#!/usr/bin/env python3
"""
Inspeciona estrutura real da API Superbid Agregado
"""

import asyncio
import httpx
import json
from pathlib import Path

HEADERS = {
    'Accept': 'application/json',
    'Origin': 'https://www.superbid.net',
    'Referer': 'https://www.superbid.net/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

async def main():
    """Inspeciona estrutura da API."""
    url = "https://offer-query.superbid.net/offers/"
    params = {
        "portalId": "2",
        "filter": "product.productType.description:imoveis;stores.id:[1161]",
        "requestOrigin": "store",
        "pageSize": "10",
        "pageNumber": "1"
    }
    
    print("Fazendo requisição à API...")
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.get(url, params=params, headers=HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\nTotal: {data.get('total', 0)}")
            print(f"Itens retornados: {len(data.get('offers', []))}")
            
            if data.get('offers'):
                first_item = data['offers'][0]
                
                print("\n" + "=" * 80)
                print("ESTRUTURA DO PRIMEIRO ITEM (completo):")
                print("=" * 80)
                print(json.dumps(first_item, indent=2, ensure_ascii=False))
                
                # Salvar em arquivo
                with open("estrutura_api_item.json", "w", encoding="utf-8") as f:
                    json.dump(first_item, f, indent=2, ensure_ascii=False)
                print("\n[OK] Estrutura salva em: estrutura_api_item.json")
                
                # Analisar campos importantes
                print("\n" + "=" * 80)
                print("ANÁLISE DE CAMPOS:")
                print("=" * 80)
                
                # Título
                product = first_item.get('product', {})
                print(f"\nTítulo:")
                print(f"  offer.product.title: {product.get('title')}")
                print(f"  offer.product.name: {product.get('name')}")
                print(f"  offer.title: {first_item.get('title')}")
                
                # URL
                print(f"\nURL:")
                print(f"  offer.url: {first_item.get('url')}")
                print(f"  offer.link: {first_item.get('link')}")
                print(f"  offer.product.url: {product.get('url')}")
                
                # Preço
                print(f"\nPreço:")
                print(f"  offer.price: {first_item.get('price')}")
                print(f"  offer.product.price: {product.get('price')}")
                
                # Localização
                print(f"\nLocalização:")
                print(f"  offer.address: {first_item.get('address')}")
                print(f"  offer.product.address: {product.get('address')}")
                
                # Imagens
                print(f"\nImagens:")
                print(f"  offer.images: {first_item.get('images')}")
                print(f"  offer.product.images: {product.get('images')}")
                
                # Store
                print(f"\nStore/Leiloeiro:")
                print(f"  offer.stores: {first_item.get('stores')}")
        else:
            print(f"ERRO: HTTP {response.status_code}")
            print(response.text[:500])

if __name__ == "__main__":
    asyncio.run(main())

