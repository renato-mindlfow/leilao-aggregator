#!/usr/bin/env python3
"""
Script para executar scraping COMPLETO do Superbid Agregado
- API: https://offer-query.superbid.net/offers/
- Filtro: product.productType.description:imoveis;stores.id:[1161]
- max_items: 12000
- pageSize: 50
- delay entre páginas: 1.5s (para evitar 503)
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Diretórios
RESULTS_DIR = Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Headers para API
API_HEADERS = {
    'Accept': 'application/json',
    'Origin': 'https://www.superbid.net',
    'Referer': 'https://www.superbid.net/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


async def scrape_superbid_agregado_completo(max_items: int = 12000) -> dict:
    """Scraper completo para Superbid Agregado via API com delay de 1.5s."""
    
    print("\n" + "="*70)
    print("SUPERBID AGREGADO - SCRAPING COMPLETO")
    print("="*70)
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Max items: {max_items:,}")
    print(f"Delay entre páginas: 1.5s")
    print("="*70)
    
    result = {
        "id": "superbid_agregado",
        "name": "Superbid Agregado",
        "method": "api",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "success": False,
        "total_properties": 0,
        "pages_scraped": 0,
        "properties": [],
        "errors": [],
        "api_total": None
    }
    
    try:
        api_url = "https://offer-query.superbid.net/offers/"
        params = {
            "portalId": "2",
            "filter": "product.productType.description:imoveis;stores.id:[1161]",
            "requestOrigin": "store",
            "pageSize": "50",
            "pageNumber": "1"
        }
        
        page = 1
        property_ids = set()
        
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            while len(result["properties"]) < max_items:
                params["pageNumber"] = str(page)
                
                print(f"\n   Página {page}...", end=" ", flush=True)
                
                try:
                    response = await client.get(api_url, params=params, headers=API_HEADERS)
                    response.raise_for_status()
                    data = response.json()
                    
                    offers = data.get("offers", [])
                    total = data.get("total", 0)
                    
                    if page == 1:
                        result["api_total"] = total
                        print(f"Total disponível na API: {total:,}")
                        estimated_pages = (total + 49) // 50  # Arredondar para cima
                        estimated_time = (estimated_pages * 1.5) / 60  # minutos
                        print(f"   Páginas estimadas: ~{estimated_pages}")
                        print(f"   Tempo estimado: ~{estimated_time:.1f} minutos")
                    else:
                        print(f"{len(offers)} itens recebidos")
                    
                    if not offers:
                        print("   [WARN] Sem itens, parando...")
                        break
                    
                    processed = 0
                    skipped_duplicate = 0
                    
                    for offer in offers:
                        if len(result["properties"]) >= max_items:
                            break
                        
                        offer_id = offer.get("id")
                        if not offer_id:
                            continue
                        
                        if offer_id in property_ids:
                            skipped_duplicate += 1
                            continue
                        
                        property_ids.add(offer_id)
                        processed += 1
                        
                        # Extrair dados
                        product = offer.get("product", {})
                        prop = {
                            "id": offer_id,
                            "url": f"https://www.superbid.net/produto/{offer_id}",
                            "title": product.get("shortDesc", "")[:200],
                            "price": offer.get("priceFormatted", ""),
                            "location": "",
                            "image_url": product.get("thumbnailUrl", ""),
                            "category": product.get("productType", {}).get("description", ""),
                            "extracted_at": datetime.now().isoformat(),
                            "auctioneer_id": "superbid_agregado",
                            "auctioneer_name": "Superbid Agregado"
                        }
                        
                        # Localização
                        location = product.get("location", {})
                        if location:
                            city = location.get("city", "")
                            state = location.get("state", "")
                            if city or state:
                                prop["location"] = f"{city}, {state}".strip(", ")
                                prop["city"] = city
                                prop["state"] = state
                        
                        # Preço numérico
                        price_value = offer.get("price")
                        if price_value:
                            prop["price_value"] = price_value
                        
                        result["properties"].append(prop)
                    
                    if skipped_duplicate > 0:
                        print(f"      [INFO] {skipped_duplicate} duplicados pulados")
                    
                    result["pages_scraped"] = page
                    
                    # Se recebeu menos itens que o pageSize, provavelmente é a última página
                    if len(offers) < 50:
                        print("   [INFO] Última página atingida")
                        break
                    
                    # Delay de 1.5s entre páginas
                    await asyncio.sleep(1.5)
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 503:
                        error_msg = f"Página {page}: 503 Service Unavailable - Rate limit atingido"
                        result["errors"].append(error_msg)
                        print(f"\n   [ERRO] {error_msg}")
                        print("   [INFO] Aguardando 10s antes de continuar...")
                        await asyncio.sleep(10)
                        # Tentar novamente a mesma página
                        continue
                    else:
                        error_msg = f"Página {page}: HTTP {e.response.status_code}"
                        result["errors"].append(error_msg)
                        print(f"\n   [ERRO] {error_msg}")
                        break
                except Exception as e:
                    error_msg = f"Página {page}: {str(e)}"
                    result["errors"].append(error_msg)
                    print(f"\n   [ERRO] {error_msg[:100]}")
                    break
                
                page += 1
                
                # Progresso a cada 10 páginas
                if page % 10 == 0:
                    progress = (len(result["properties"]) / max_items) * 100
                    print(f"\n   [PROGRESSO] {len(result['properties']):,} imóveis extraídos ({progress:.1f}%)")
        
        result["success"] = len(result["properties"]) > 0
        result["total_properties"] = len(result["properties"])
        result["finished_at"] = datetime.now().isoformat()
        
        print("\n" + "="*70)
        print("RESULTADO FINAL")
        print("="*70)
        print(f"   Imóveis extraídos: {result['total_properties']:,}")
        print(f"   Páginas processadas: {result['pages_scraped']}")
        print(f"   Total disponível na API: {result['api_total']:,}" if result['api_total'] else "")
        print(f"   Erros: {len(result['errors'])}")
        print("="*70)
        
    except Exception as e:
        result["errors"].append(str(e))
        print(f"\n   [ERRO FATAL] {e}")
        import traceback
        traceback.print_exc()
    
    return result


async def main():
    """Função principal."""
    
    result = await scrape_superbid_agregado_completo(max_items=12000)
    
    # Salvar resultado
    output_file = RESULTS_DIR / "resultado_superbid_agregado_completo.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n[SAVED] Resultado salvo em: {output_file}")
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())

