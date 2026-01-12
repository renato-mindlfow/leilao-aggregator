"""
Script para gerar relatório final consolidado
FASE FINAL da tarefa autônoma
"""

import os
import sys
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERRO: DATABASE_URL nao configurada no .env")
    sys.exit(1)

def generate_report():
    """Gera relatório consolidado."""
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                print('=' * 60)
                print(f'RELATORIO FINAL - {datetime.now().strftime("%Y-%m-%d %H:%M")}')
                print('=' * 60)
                
                # Total de imóveis
                cur.execute('SELECT COUNT(*) as total FROM properties')
                total = cur.fetchone()['total']
                print(f'\nTotal de imoveis no banco: {total}')
                
                # Por leiloeiro (top 10)
                cur.execute('''
                    SELECT auctioneer_id, COUNT(*) as qtd 
                    FROM properties 
                    GROUP BY auctioneer_id 
                    ORDER BY qtd DESC 
                    LIMIT 10
                ''')
                print(f'\nTop 10 leiloeiros por volume:')
                for row in cur.fetchall():
                    print(f'  {row["auctioneer_id"]}: {row["qtd"]}')
                
                # Status dos leiloeiros
                cur.execute('''
                    SELECT scrape_status, COUNT(*) as count
                    FROM auctioneers 
                    GROUP BY scrape_status
                ''')
                print(f'\nStatus dos leiloeiros:')
                for row in cur.fetchall():
                    print(f'  {row["scrape_status"]}: {row["count"]}')
                
                # Imóveis por estado (top 5)
                cur.execute('''
                    SELECT state, COUNT(*) as qtd 
                    FROM properties 
                    GROUP BY state 
                    ORDER BY qtd DESC 
                    LIMIT 5
                ''')
                print(f'\nTop 5 estados:')
                for row in cur.fetchall():
                    print(f'  {row["state"]}: {row["qtd"]}')
                
                # Leiloeiros ativos
                cur.execute('''
                    SELECT COUNT(*) as count
                    FROM auctioneers 
                    WHERE is_active = true
                ''')
                active_count = cur.fetchone()['count']
                print(f'\nLeiloeiros ativos: {active_count}')
                
                # Leiloeiros com erro
                cur.execute('''
                    SELECT COUNT(*) as count
                    FROM auctioneers 
                    WHERE scrape_status = 'error'
                ''')
                error_count = cur.fetchone()['count']
                print(f'Leiloeiros com erro: {error_count}')
                
                # Leiloeiros pendentes
                cur.execute('''
                    SELECT COUNT(*) as count
                    FROM auctioneers 
                    WHERE scrape_status = 'pending'
                ''')
                pending_count = cur.fetchone()['count']
                print(f'Leiloeiros pendentes: {pending_count}')
                
                conn.close()
                
                print('\n' + '=' * 60)
                print('FIM DO RELATORIO')
                print('=' * 60)
                
    except Exception as e:
        print(f"ERRO ao gerar relatorio: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_report()

