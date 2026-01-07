#!/usr/bin/env python3
"""
Verifica dados salvos no Supabase.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def main():
    print("="*60)
    print("VERIFICACAO DE DADOS NO SUPABASE")
    print("="*60)
    
    # Total de imóveis
    result = supabase.table("properties").select("id", count="exact").execute()
    total = result.count
    print(f"\n[TOTAL] Total de imoveis no banco: {total}")
    
    # Por leiloeiro
    print("\n[POR LEILOEIRO]")
    
    auctioneers = ["megaleiloes", "sodresantoro", "flexleiloes", "caixa"]
    
    for auc in auctioneers:
        result = supabase.table("properties").select("id", count="exact").eq("auctioneer_id", auc).execute()
        count = result.count or 0
        print(f"   {auc}: {count} imoveis")
    
    # Por categoria (novos imóveis)
    print("\n[POR CATEGORIA - NOVOS SCRAPERS]")
    
    for auc in ["megaleiloes", "sodresantoro", "flexleiloes"]:
        result = supabase.table("properties").select("category").eq("auctioneer_id", auc).execute()
        
        if result.data:
            categories = {}
            for p in result.data:
                cat = p.get("category", "Outro")
                categories[cat] = categories.get(cat, 0) + 1
            
            print(f"\n   {auc}:")
            for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
                print(f"      {cat}: {count}")
    
    # Amostra de imóveis novos
    print("\n[AMOSTRA - MEGA LEILOES]")
    
    result = supabase.table("properties").select("title, city, state, first_auction_value").eq("auctioneer_id", "megaleiloes").limit(5).execute()
    
    for p in result.data or []:
        print(f"\n   - {p.get('title', 'N/A')[:50]}")
        print(f"     {p.get('city', 'N/A')}/{p.get('state', 'N/A')} - R$ {p.get('first_auction_value', 'N/A')}")
    
    print("\n" + "="*60)
    print("[OK] Verificacao concluida")
    print("="*60)

if __name__ == "__main__":
    main()

