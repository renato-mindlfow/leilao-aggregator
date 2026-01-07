#!/usr/bin/env python3
"""
Garante que os leiloeiros verificados existem no banco.
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

VERIFIED_AUCTIONEERS = [
    {
        "id": "megaleiloes",
        "name": "Mega Leilões",
        "website": "https://www.megaleiloes.com.br",
        "is_active": True,
        "scrape_status": "pending",
    },
    {
        "id": "sodresantoro",
        "name": "Sodré Santoro",
        "website": "https://leilao.sodresantoro.com.br",
        "is_active": True,
        "scrape_status": "pending",
    },
    {
        "id": "flexleiloes",
        "name": "Flex Leilões",
        "website": "https://www.flexleiloes.com.br",
        "is_active": True,
        "scrape_status": "pending",
    },
]

def main():
    print("Verificando/criando leiloeiros no banco...")
    
    for auc in VERIFIED_AUCTIONEERS:
        try:
            # Verificar se existe
            result = supabase.table("auctioneers").select("id").eq("id", auc["id"]).execute()
            
            if result.data:
                print(f"[OK] {auc['name']} ja existe")
            else:
                # Criar
                auc["created_at"] = datetime.now().isoformat()
                auc["updated_at"] = datetime.now().isoformat()
                
                supabase.table("auctioneers").insert(auc).execute()
                print(f"[+] {auc['name']} criado")
                
        except Exception as e:
            print(f"[ERRO] Erro com {auc['name']}: {e}")

if __name__ == "__main__":
    main()

