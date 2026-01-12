"""
Script para diagnosticar e listar leiloeiros com erro
FASE 3 da tarefa autônoma
"""

import os
import sys
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERRO: DATABASE_URL nao configurada no .env")
    sys.exit(1)

def list_auctioneers_with_errors():
    """Lista leiloeiros com erro no banco."""
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, website, scrape_status, scrape_error, property_count
                    FROM auctioneers 
                    WHERE scrape_status = 'error' 
                    ORDER BY property_count DESC 
                    LIMIT 15
                """)
                
                rows = cur.fetchall()
                return rows
    except Exception as e:
        print(f"ERRO ao consultar banco: {e}")
        return []

def main():
    print("=" * 80)
    print("FASE 3: Diagnosticando leiloeiros com erro")
    print("=" * 80)
    print()
    
    auctioneers = list_auctioneers_with_errors()
    
    if not auctioneers:
        print("Nenhum leiloeiro com erro encontrado no banco.")
        return
    
    print(f"Encontrados {len(auctioneers)} leiloeiros com erro (ordenados por potencial):")
    print("=" * 80)
    
    for row in auctioneers:
        print(f"\nID: {row['id']}")
        print(f"  Nome: {row['name']}")
        print(f"  Website: {row['website']}")
        print(f"  Status: {row['scrape_status']}")
        print(f"  Imoveis: {row['property_count']}")
        error = row['scrape_error']
        if error:
            error_preview = error[:100] if len(error) > 100 else error
            print(f"  Erro: {error_preview}...")
        else:
            print(f"  Erro: N/A")
    
    print()
    print("=" * 80)
    print("Diagnostico concluido")
    print("=" * 80)

if __name__ == "__main__":
    main()

