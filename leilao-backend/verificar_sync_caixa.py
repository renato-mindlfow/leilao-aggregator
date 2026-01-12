"""Verificar resultado do sync da Caixa no banco"""
from dotenv import load_dotenv
import os
import psycopg
from psycopg.rows import dict_row

load_dotenv()
conn = psycopg.connect(os.getenv('DATABASE_URL'), row_factory=dict_row)
cur = conn.cursor()

# Total de imóveis
cur.execute('SELECT COUNT(*) as count FROM properties')
total = cur.fetchone()['count']
print(f'Total de imoveis no banco: {total}')

# Imóveis da Caixa
cur.execute("SELECT COUNT(*) as count FROM properties WHERE auctioneer_id = 'caixa_federal'")
caixa = cur.fetchone()['count']
print(f'Imoveis da Caixa: {caixa}')

# Por estado (top 5)
cur.execute("""
    SELECT state, COUNT(*) as qtd 
    FROM properties 
    WHERE auctioneer_id = 'caixa_federal' 
    GROUP BY state 
    ORDER BY qtd DESC 
    LIMIT 5
""")
print(f'\nTop 5 estados:')
for row in cur.fetchall():
    print(f'  {row["state"]}: {row["qtd"]}')

# Verificar leiloeiro Caixa
cur.execute("SELECT * FROM auctioneers WHERE id = 'caixa_federal'")
leiloeiro = cur.fetchone()
if leiloeiro:
    print(f'\nLeiloeiro Caixa:')
    print(f'  ID: {leiloeiro["id"]}')
    print(f'  Nome: {leiloeiro["name"]}')
    print(f'  Status: {leiloeiro.get("scrape_status", "N/A")}')
    print(f'  Total de imoveis: {leiloeiro.get("property_count", 0)}')
    print(f'  Ultimo scrape: {leiloeiro.get("last_scrape", "N/A")}')
else:
    print('\n[AVISO] Leiloeiro Caixa nao encontrado na tabela auctioneers')

conn.close()

