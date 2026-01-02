"""
Script para aplicar migrations SQL no banco de dados.
"""

import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

def apply_migrations():
    """Aplica todas as migrations SQL."""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Buscar arquivos de migration
    migrations_dir = os.path.join(os.path.dirname(__file__), '..', 'migrations')
    migration_files = sorted(glob.glob(os.path.join(migrations_dir, '*.sql')))
    
    for migration_file in migration_files:
        filename = os.path.basename(migration_file)
        print(f"Aplicando: {filename}")
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        try:
            cur.execute(sql)
            conn.commit()
            print(f"  ✅ Sucesso!")
        except Exception as e:
            conn.rollback()
            print(f"  ❌ Erro: {e}")
    
    cur.close()
    conn.close()
    print("\n✅ Migrations concluídas!")

if __name__ == "__main__":
    apply_migrations()

