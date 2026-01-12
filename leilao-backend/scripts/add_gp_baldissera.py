"""
Script para adicionar GP Leilões e Baldissera ao banco de dados
FASE 2 da tarefa autônoma
"""

import os
import sys
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERRO: DATABASE_URL nao configurada no .env")
    sys.exit(1)

def add_auctioneer(id: str, name: str, website: str):
    """Adiciona ou atualiza um leiloeiro no banco."""
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Verificar se já existe
                cur.execute("SELECT id FROM auctioneers WHERE id = %s", (id,))
                existing = cur.fetchone()
                
                if existing:
                    print(f"  INFO: {name} ja existe no banco")
                    # Atualizar para garantir que está ativo
                    cur.execute("""
                        UPDATE auctioneers 
                        SET is_active = true, 
                            scrape_status = 'pending',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (id,))
                    conn.commit()
                    print(f"  OK: {name} atualizado")
                else:
                    cur.execute("""
                        INSERT INTO auctioneers (id, name, website, is_active, scrape_status, created_at, updated_at)
                        VALUES (%s, %s, %s, true, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (id, name, website))
                    conn.commit()
                    print(f"  OK: {name} adicionado ao banco")
                return True
    except Exception as e:
        print(f"  ERRO: Erro ao adicionar {name}: {e}")
        return False

def main():
    print("=" * 60)
    print("FASE 2: Adicionando GP Leilões e Baldissera")
    print("=" * 60)
    print()
    
    auctioneers = [
        {
            'id': 'gp_leiloes',
            'name': 'GP Leilões',
            'website': 'https://www.gpleiloes.com.br'
        },
        {
            'id': 'baldissera',
            'name': 'Baldissera Leiloeiros',
            'website': 'https://www.baldisseraleiloeiros.com.br'
        }
    ]
    
    success_count = 0
    for auc in auctioneers:
        print(f"\nProcessando: {auc['name']}")
        if add_auctioneer(auc['id'], auc['name'], auc['website']):
            success_count += 1
    
    print()
    print("=" * 60)
    print(f"Concluido: {success_count}/{len(auctioneers)} leiloeiros adicionados/atualizados")
    print("=" * 60)

if __name__ == "__main__":
    main()

