#!/usr/bin/env python3
"""Sync scraped properties to Supabase."""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERRO: SUPABASE_URL e SUPABASE_KEY devem estar configurados no .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_id(source_url: str) -> str:
    """Gerar ID único baseado na URL."""
    return hashlib.md5(source_url.encode()).hexdigest()

def parse_price(price_str: str) -> float:
    """Converter string de preço para float."""
    if not price_str:
        return None
    try:
        # Remove "R$", espaços, pontos e vírgulas
        cleaned = price_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
        return float(cleaned)
    except:
        return None

def extract_location_parts(location: str) -> tuple:
    """Extrair estado e cidade de uma string de localização."""
    if not location:
        return ("", "")
    
    parts = location.split(",")
    if len(parts) >= 2:
        city = parts[0].strip()
        state = parts[1].strip()[:2] if len(parts[1].strip()) >= 2 else ""
        return (state, city)
    elif len(parts) == 1:
        # Tentar extrair estado se estiver no formato "Cidade - UF"
        if " - " in parts[0]:
            city_state = parts[0].split(" - ")
            if len(city_state) == 2:
                return (city_state[1].strip()[:2], city_state[0].strip())
        return ("", parts[0].strip())
    return ("", "")

def normalize_property(prop: dict, source: str) -> dict:
    """Normalizar propriedade para o schema do Supabase."""
    source_url = prop.get("url") or prop.get("source_url") or prop.get("link") or ""
    
    if not source_url:
        return None
    
    # Extrair valores
    title = prop.get("title", "") or ""
    price_str = prop.get("price", "") or ""
    location = prop.get("location", "") or ""
    
    # Converter preço
    first_auction_value = parse_price(price_str)
    
    # Extrair estado e cidade
    state, city = extract_location_parts(location)
    
    # Determinar categoria
    category = "Outro"
    if any(word in title.lower() for word in ["apto", "apartamento", "ap"]):
        category = "Apartamento"
    elif any(word in title.lower() for word in ["casa", "residencial"]):
        category = "Casa"
    elif any(word in title.lower() for word in ["terreno", "lote"]):
        category = "Terreno"
    elif any(word in title.lower() for word in ["sala", "comercial", "loja"]):
        category = "Comercial"
    
    return {
        "id": generate_id(source_url),
        "title": title[:500] if title else "",
        "category": category,
        "auction_type": prop.get("auction_type", "Extrajudicial"),
        "state": state,
        "city": city[:255] if city else "",
        "address": prop.get("address", "") or "",
        "evaluation_value": parse_price(prop.get("evaluation_value", "")) if prop.get("evaluation_value") else None,
        "first_auction_value": first_auction_value,
        "second_auction_value": parse_price(prop.get("second_auction_value", "")) if prop.get("second_auction_value") else None,
        "discount_percentage": prop.get("discount_percentage"),
        "image_url": prop.get("image_url") or prop.get("image") or "",
        "source_url": source_url,
        "auctioneer_id": source,
        "auctioneer_name": prop.get("auctioneer_name") or source,
        "source": source,
        "is_active": True,
        "updated_at": datetime.now().isoformat()
    }

def sync_file(filepath: str, source: str) -> dict:
    """Sincronizar arquivo de resultado para Supabase."""
    print(f"\n[PROCESSANDO] {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Tentar diferentes estruturas de dados
    properties = []
    if isinstance(data, list):
        properties = data
    elif isinstance(data, dict):
        properties = data.get("properties") or data.get("imoveis") or data.get("items") or data.get("offers") or []
    
    if not properties:
        print(f"  [AVISO] Nenhum imovel encontrado em {filepath}")
        return {"inserted": 0, "errors": 0, "source": source}
    
    print(f"  [INFO] {len(properties)} imoveis encontrados")
    
    inserted = 0
    errors = 0
    batch = []
    batch_size = 100
    
    for prop in properties:
        try:
            normalized = normalize_property(prop, source)
            if normalized and normalized["id"] and normalized["source_url"]:
                batch.append(normalized)
                
                if len(batch) >= batch_size:
                    try:
                        supabase.table("properties").upsert(batch, on_conflict="id").execute()
                        inserted += len(batch)
                        print(f"  [OK] {inserted} inseridos...")
                    except Exception as e:
                        print(f"  [ERRO] Erro no batch: {e}")
                        errors += len(batch)
                    batch = []
        except Exception as e:
            errors += 1
            if errors <= 5:  # Mostrar apenas os primeiros 5 erros
                print(f"  [AVISO] Erro ao normalizar imovel: {e}")
    
    # Inserir batch restante
    if batch:
        try:
            supabase.table("properties").upsert(batch, on_conflict="id").execute()
            inserted += len(batch)
        except Exception as e:
            print(f"  [ERRO] Erro no batch final: {e}")
            errors += len(batch)
    
    print(f"  [CONCLUIDO] {inserted} inseridos, {errors} erros")
    return {"inserted": inserted, "errors": errors, "source": source}

def main():
    print("=" * 60)
    print("SYNC PARA SUPABASE - LeiloHub")
    print("=" * 60)
    
    results_dir = Path(__file__).parent.parent / "results"
    
    files = [
        ("resultado_superbid_agregado.json", "superbid_agregado"),
        ("resultado_portal_zuk.json", "portal_zuk"),
        ("resultado_mega_leiloes.json", "mega_leiloes"),
        ("resultado_lance_judicial.json", "lance_judicial"),
        ("resultado_sold.json", "sold"),
    ]
    
    total_inserted = 0
    total_errors = 0
    
    for filename, source in files:
        filepath = results_dir / filename
        if filepath.exists():
            result = sync_file(str(filepath), source)
            total_inserted += result["inserted"]
            total_errors += result["errors"]
        else:
            print(f"\n[AVISO] Arquivo nao encontrado: {filename}")
    
    print("\n" + "=" * 60)
    print(f"TOTAL: {total_inserted} inseridos, {total_errors} erros")
    print("=" * 60)

if __name__ == "__main__":
    main()

