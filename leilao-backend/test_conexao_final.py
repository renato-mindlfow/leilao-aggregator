"""Teste final de conexão"""
from dotenv import load_dotenv
import os
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.getenv('DATABASE_URL')
print(f'[INFO] DATABASE_URL: {url[:80]}...' if url else '[ERRO] DATABASE_URL nao configurada')

try:
    conn = psycopg.connect(url, row_factory=dict_row)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) as count FROM properties')
    result = cur.fetchone()
    print(f'[OK] Conexao OK! Total de imoveis no banco: {result["count"]}')
    conn.close()
except Exception as e:
    print(f'[ERRO] {e}')

