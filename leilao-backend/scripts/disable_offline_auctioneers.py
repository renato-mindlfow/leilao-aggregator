#!/usr/bin/env python3
"""
Desativa leiloeiros offline no banco de dados.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Leiloeiros confirmados como offline
OFFLINE_AUCTIONEERS = [
    "leje",  # ERR_NAME_NOT_RESOLVED
    "lfranca",
]

def main():
    print("Desativando leiloeiros offline...")
    
    for auc_id in OFFLINE_AUCTIONEERS:
        try:
            # Tentar por ID
            result = supabase.table("auctioneers").update({
                "is_active": False,
                "scrape_status": "disabled",
                "scrape_error": "Site offline - domínio não resolve"
            }).eq("id", auc_id).execute()
            
            if result.data:
                print(f"[OK] Desativado: {auc_id}")
            else:
                # Tentar por nome
                result = supabase.table("auctioneers").update({
                    "is_active": False,
                    "scrape_status": "disabled",
                    "scrape_error": "Site offline - dominio nao resolve"
                }).ilike("name", f"%{auc_id}%").execute()
                
                if result.data:
                    print(f"[OK] Desativado: {auc_id}")
                else:
                    print(f"[AVISO] Nao encontrado: {auc_id}")
        except Exception as e:
            print(f"[ERRO] Erro ao desativar {auc_id}: {e}")

if __name__ == "__main__":
    main()

