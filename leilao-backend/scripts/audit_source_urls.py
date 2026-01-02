"""
Script para auditar URLs de origem dos imóveis.
Identifica imóveis sem URL válida para correção.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

def audit_source_urls():
    """Audita URLs de origem dos imóveis."""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Contar URLs vazias ou inválidas
    cur.execute("""
        SELECT COUNT(*) FROM properties 
        WHERE source_url IS NULL 
           OR source_url = '' 
           OR source_url = '#'
           OR source_url LIKE '%leilohub%'
    """)
    invalid_count = cur.fetchone()[0]
    
    # Contar total
    cur.execute("SELECT COUNT(*) FROM properties")
    total_count = cur.fetchone()[0]
    
    # Listar por leiloeiro
    cur.execute("""
        SELECT auctioneer_name, COUNT(*) as total,
               SUM(CASE WHEN source_url IS NULL OR source_url = '' OR source_url = '#' OR source_url LIKE '%leilohub%' THEN 1 ELSE 0 END) as invalid
        FROM properties
        GROUP BY auctioneer_name
        ORDER BY invalid DESC
        LIMIT 20
    """)
    by_auctioneer = cur.fetchall()
    
    cur.close()
    conn.close()
    
    print(f"\n📊 AUDITORIA DE URLs DE ORIGEM")
    print(f"{'='*50}")
    print(f"Total de imóveis: {total_count}")
    if total_count > 0:
        percentage = 100 * invalid_count / total_count
        print(f"URLs inválidas: {invalid_count} ({percentage:.1f}%)")
    else:
        print(f"URLs inválidas: {invalid_count}")
    print(f"\n📋 Por Leiloeiro (top 20 com mais problemas):")
    print(f"{'-'*50}")
    
    for row in by_auctioneer:
        name, total, invalid = row
        name = name or "Desconhecido"
        print(f"{name[:30]:<30} Total: {total:>5} | Inválidas: {invalid:>5}")

if __name__ == "__main__":
    audit_source_urls()

