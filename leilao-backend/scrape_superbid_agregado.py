#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simplificado para scraping do Superbid Agregado
API: https://offer-query.superbid.net/offers/
"""

import json
import time
import requests
import sys
import os
from datetime import datetime
from typing import Dict, List, Set
from urllib.parse import urljoin

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================
# CONFIGURAÇÃO
# ============================================================

API_URL = "https://offer-query.superbid.net/offers/"
FILTER = "product.productType.description:imoveis;stores.id:[1161]"
PAGE_SIZE = 50
DELAY = 1.5  # segundos entre requisições
MAX_ITEMS = 12000
OUTPUT_FILE = "results/superbid_agregado_completo.json"

# ============================================================
# PARÂMETROS DA API
# ============================================================

API_PARAMS = {
    "portalId": "2",
    "filter": FILTER,
    "requestOrigin": "store",
    "pageSize": str(PAGE_SIZE),
}

# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def scrape_superbid_agregado():
    """Executa scraping completo do Superbid Agregado."""
    
    print("="*70)
    print("SCRAPING SUPERBID AGREGADO")
    print("="*70)
    print(f"API: {API_URL}")
    print(f"Filtro: {FILTER}")
    print(f"PageSize: {PAGE_SIZE}")
    print(f"Delay: {DELAY}s")
    print(f"Max Items: {MAX_ITEMS}")
    print(f"Output: {OUTPUT_FILE}")
    print("="*70)
    print(f"\nInício: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    properties = []
    property_ids: Set[int] = set()
    property_urls: Set[str] = set()
    errors = []
    pages_scraped = 0
    api_total = None
    
    current_page = 1
    max_pages = (MAX_ITEMS // PAGE_SIZE) + 10  # Margem de segurança
    
    while len(properties) < MAX_ITEMS and current_page <= max_pages:
        # Preparar parâmetros da requisição
        params = API_PARAMS.copy()
        params["pageNumber"] = str(current_page)
        
        print(f"[PÁGINA {current_page}] Buscando {PAGE_SIZE} itens...", end=" ")
        
        try:
            # Fazer requisição
            response = requests.get(API_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            offers = data.get("offers", [])
            total = data.get("total", 0)
            
            # Armazenar total da API (primeira página)
            if current_page == 1:
                api_total = total
                print(f"[OK] Total disponivel na API: {total}")
            else:
                print(f"[OK] Itens recebidos: {len(offers)}")
            
            if len(offers) == 0:
                print(f"  [WARN] Sem itens, parando...")
                break
            
            # Processar cada oferta
            processed = 0
            skipped_no_id = 0
            skipped_duplicate = 0
            
            for offer in offers:
                if len(properties) >= MAX_ITEMS:
                    break
                
                # Extrair ID da oferta (chave única)
                offer_id = offer.get("id")
                
                # Verificar duplicado por ID
                if offer_id and offer_id in property_ids:
                    skipped_duplicate += 1
                    continue
                
                # Extrair URL do imóvel
                link_url = offer.get("linkURL", "")
                if not link_url:
                    # Construir URL a partir do ID
                    auction_id = offer.get("auction", {}).get("id")
                    if offer_id:
                        link_url = f"/produto/{offer_id}"
                    elif auction_id:
                        link_url = f"/leilao/{auction_id}"
                    else:
                        skipped_no_id += 1
                        continue
                
                # Construir URL completa
                if link_url.startswith("http"):
                    full_url = link_url
                else:
                    full_url = urljoin("https://www.superbid.net", link_url)
                
                # Verificar duplicado por URL (se não tiver offer_id)
                if not offer_id and full_url in property_urls:
                    skipped_duplicate += 1
                    continue
                
                # Adicionar às listas de controle
                if offer_id:
                    property_ids.add(offer_id)
                property_urls.add(full_url)
                processed += 1
                
                # Extrair informações
                prop = {
                    "id": offer_id,
                    "url": full_url,
                    "title": offer.get("product", {}).get("shortDesc", "")[:200],
                    "price": offer.get("priceFormatted", ""),
                    "price_raw": offer.get("price", 0),
                    "location": "",
                    "category": offer.get("product", {}).get("productType", {}).get("description", ""),
                    "image_url": offer.get("product", {}).get("thumbnailUrl", ""),
                    "auction_id": offer.get("auction", {}).get("id"),
                    "store_id": offer.get("store", {}).get("id") if offer.get("store") else None,
                    "store_name": offer.get("store", {}).get("name", "") if offer.get("store") else "",
                    "end_date": offer.get("endDate", ""),
                    "end_date_time": offer.get("endDateTime", ""),
                    "total_bids": offer.get("totalBids", 0),
                    "offer_status": offer.get("offerStatus", ""),
                    "extracted_at": datetime.now().isoformat(),
                    "raw_data": offer,  # Incluir dados completos
                }
                properties.append(prop)
            
            print(f"  Processados: {processed} | Pulados (sem ID): {skipped_no_id} | Pulados (duplicados): {skipped_duplicate}")
            print(f"  Total acumulado: {len(properties)}/{MAX_ITEMS}")
            
            pages_scraped += 1
            
            # Se recebeu menos itens que o pageSize, provavelmente é a última página
            if len(offers) < PAGE_SIZE:
                print(f"  [INFO] Última página atingida")
                break
            
            # Delay entre requisições
            if len(properties) < MAX_ITEMS:
                time.sleep(DELAY)
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {str(e)}"
            print(f"  [ERRO] {error_msg}")
            errors.append(f"Página {current_page}: {error_msg}")
            
            # Se for 503, aguardar mais tempo
            if e.response.status_code == 503:
                print(f"  [WARN] 503 Service Unavailable, aguardando 5s...")
                time.sleep(5)
                continue
            else:
                break
                
        except Exception as e:
            error_msg = f"Erro: {str(e)}"
            print(f"  [ERRO] {error_msg}")
            errors.append(f"Página {current_page}: {error_msg}")
            break
        
        current_page += 1
    
    # Preparar resultado final
    result = {
        "source": "superbid_agregado",
        "api_url": API_URL,
        "filter": FILTER,
        "success": len(properties) > 0,
        "total_properties": len(properties),
        "api_total": api_total,
        "pages_scraped": pages_scraped,
        "properties": properties,
        "errors": errors,
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "config": {
            "page_size": PAGE_SIZE,
            "delay": DELAY,
            "max_items": MAX_ITEMS,
        }
    }
    
    # Salvar resultado
    import os
    os.makedirs(os.path.dirname(OUTPUT_FILE) if os.path.dirname(OUTPUT_FILE) else ".", exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # Relatório final
    print("\n" + "="*70)
    print("RESULTADO FINAL")
    print("="*70)
    print(f"Total de imóveis extraídos: {len(properties)}")
    print(f"Total disponível na API: {api_total}")
    print(f"Páginas processadas: {pages_scraped}")
    print(f"Erros: {len(errors)}")
    print(f"Arquivo salvo: {OUTPUT_FILE}")
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    if errors:
        print("\n[ERROS ENCONTRADOS]")
        for error in errors[:5]:  # Mostrar apenas os 5 primeiros
            print(f"  - {error}")
        if len(errors) > 5:
            print(f"  ... e mais {len(errors) - 5} erros")
    
    return result


if __name__ == "__main__":
    scrape_superbid_agregado()

