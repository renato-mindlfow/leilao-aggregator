#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para corrigir auctioneer_name nulos."""

import os
import sys
import io
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

# Mapeamento de auctioneer_id para nome correto
AUCTIONEER_NAMES = {
    "caixa": "Caixa Econômica Federal",
    "superbid_agregado": "Superbid Agregado",
    "portal_zuk": "Portal Zukerman",
    "mega_leiloes": "Mega Leilões",
    "lance_judicial": "Lance Judicial",
    "sold": "Sold Leilões",
    "sodre_santoro": "Sodré Santoro",
    # Adicionar mais conforme necessário
}

def main():
    print("=" * 60)
    print("CORRIGINDO AUCTIONEER_NAME NULOS")
    print("=" * 60)
    
    # 1. Buscar imóveis com auctioneer_name nulo
    response = supabase.table("properties") \
        .select("auctioneer_id, auctioneer_name") \
        .is_("auctioneer_name", "null") \
        .execute()
    
    if not response.data:
        print("\n[OK] Nenhum imovel com auctioneer_name nulo encontrado.")
        return
    
    print(f"\nEncontrados {len(response.data)} imóveis com auctioneer_name nulo")
    
    # Agrupar por auctioneer_id
    ids_sem_nome = {}
    for prop in response.data:
        aid = prop.get("auctioneer_id")
        if aid:
            ids_sem_nome[aid] = ids_sem_nome.get(aid, 0) + 1
    
    print(f"\nAuctioneer IDs sem nome:")
    for aid, count in sorted(ids_sem_nome.items(), key=lambda x: -x[1]):
        print(f"  {aid}: {count} imóveis")
    
    # 2. Corrigir usando mapeamento ou inferindo do ID
    total_corrigidos = 0
    
    for auctioneer_id in ids_sem_nome.keys():
        # Tentar obter nome do mapeamento
        nome = AUCTIONEER_NAMES.get(auctioneer_id)
        
        # Se não encontrar, inferir do ID (Title Case)
        if not nome:
            nome = auctioneer_id.replace("_", " ").title()
        
        print(f"\nCorrigindo {auctioneer_id} -> {nome}")
        
        # Atualizar no banco
        result = supabase.table("properties") \
            .update({"auctioneer_name": nome}) \
            .eq("auctioneer_id", auctioneer_id) \
            .is_("auctioneer_name", "null") \
            .execute()
        
        total_corrigidos += ids_sem_nome[auctioneer_id]
        print(f"  [OK] {ids_sem_nome[auctioneer_id]} imoveis corrigidos")
    
    # 3. Verificar imóveis onde auctioneer_id também é nulo
    response2 = supabase.table("properties") \
        .select("id, title, source_url") \
        .is_("auctioneer_name", "null") \
        .is_("auctioneer_id", "null") \
        .limit(10) \
        .execute()
    
    if response2.data:
        print(f"\n[AVISO] {len(response2.data)} imoveis sem auctioneer_id E auctioneer_name:")
        for prop in response2.data[:5]:
            print(f"  - {prop.get('title', 'Sem título')[:50]}...")
            print(f"    URL: {prop.get('source_url', 'N/A')[:60]}...")
    
    print("\n" + "=" * 60)
    print(f"[OK] CONCLUIDO: {total_corrigidos} imoveis corrigidos")
    print("=" * 60)
    
    # Verificar resultado final
    print("\nVerificando resultado...")
    final_check = supabase.table("properties") \
        .select("id, auctioneer_name", count="exact") \
        .is_("auctioneer_name", "null") \
        .execute()
    
    remaining = final_check.count if hasattr(final_check, 'count') else len(final_check.data) if final_check.data else 0
    print(f"\n[STATS] ESTATISTICAS:")
    print(f"  Imoveis corrigidos: {total_corrigidos}")
    print(f"  Imoveis ainda sem auctioneer_name: {remaining}")

if __name__ == "__main__":
    main()

