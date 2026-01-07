#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para gerar dedup_key para imóveis sem essa chave."""

import os
import sys
import hashlib
import io
import time
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def generate_dedup_key(source_url: str, auctioneer_id: str = None) -> str:
    """Gera chave única para deduplicação."""
    key_source = source_url or ""
    if auctioneer_id:
        key_source = f"{auctioneer_id}:{source_url}"
    return hashlib.md5(key_source.encode()).hexdigest()

def main():
    print("=" * 60)
    print("GERANDO DEDUP_KEY PARA IMÓVEIS")
    print("=" * 60)
    
    # Buscar imóveis sem dedup_key (em lotes de 1000)
    offset = 0
    batch_size = 1000
    total_updated = 0
    
    while True:
        print(f"\nProcessando lote {offset // batch_size + 1}...")
        
        # Buscar imóveis sem dedup_key (incluindo os que podem ter source_url vazio)
        try:
            response = supabase.table("properties") \
                .select("id, source_url, auctioneer_id") \
                .is_("dedup_key", "null") \
                .range(offset, offset + batch_size - 1) \
                .execute()
        except Exception as e:
            print(f"  [ERRO] Erro ao buscar imoveis: {str(e)[:100]}")
            time.sleep(2)
            continue
        
        if not response.data:
            print("Nenhum imóvel restante sem dedup_key.")
            break
        
        print(f"  Encontrados {len(response.data)} imoveis neste lote")
        
        # Gerar e atualizar dedup_key para cada imóvel (com retry)
        updated_in_batch = 0
        for prop in response.data:
            dedup_key = generate_dedup_key(
                prop.get("source_url", ""),
                prop.get("auctioneer_id", "")
            )
            
            # Atualizar no banco com retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    supabase.table("properties") \
                        .update({"dedup_key": dedup_key}) \
                        .eq("id", prop["id"]) \
                        .execute()
                    updated_in_batch += 1
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"    [RETRY] Erro ao atualizar {prop['id']}, tentativa {attempt + 1}/{max_retries}")
                        time.sleep(2 ** attempt)  # Backoff exponencial
                    else:
                        print(f"    [ERRO] Falha ao atualizar {prop['id']}: {str(e)[:100]}")
        
        total_updated += updated_in_batch
        print(f"  [OK] Atualizados: {total_updated} imoveis (lote: {updated_in_batch})")
        
        # Pequeno delay entre lotes para evitar sobrecarga
        if len(response.data) == batch_size:
            time.sleep(0.5)
        
        if len(response.data) < batch_size:
            break
        
        offset += batch_size
    
    print("\n" + "=" * 60)
    print(f"[OK] CONCLUIDO: {total_updated} imoveis atualizados com dedup_key")
    print("=" * 60)
    
    # Verificar resultado
    print("\nVerificando resultado...")
    check_response = supabase.table("properties") \
        .select("id, dedup_key", count="exact") \
        .execute()
    
    total = check_response.count if hasattr(check_response, 'count') else len(check_response.data) if check_response.data else 0
    
    # Contar com dedup_key
    with_key_response = supabase.table("properties") \
        .select("id", count="exact") \
        .not_.is_("dedup_key", "null") \
        .execute()
    
    with_key = with_key_response.count if hasattr(with_key_response, 'count') else len(with_key_response.data) if with_key_response.data else 0
    without_key = total - with_key
    
    print(f"\n[STATS] ESTATISTICAS:")
    print(f"  Total de imoveis: {total}")
    print(f"  Com dedup_key: {with_key}")
    print(f"  Sem dedup_key: {without_key}")

if __name__ == "__main__":
    main()

