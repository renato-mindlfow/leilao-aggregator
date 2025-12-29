# test_db_connection.py
import os
import sys
from dotenv import load_dotenv

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"DATABASE_URL carregada: {DATABASE_URL[:50] if DATABASE_URL else 'NAO ENCONTRADA'}...")

if not DATABASE_URL:
    print("[ERRO] DATABASE_URL nao encontrada no .env")
    exit(1)

import psycopg
from psycopg.rows import dict_row

try:
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    cursor = conn.execute("SELECT COUNT(*) as total FROM properties")
    result = cursor.fetchone()
    print(f"[OK] Conexao OK! Total de imoveis: {result['total']}")
    conn.close()
except Exception as e:
    print(f"[ERRO] Erro de conexao: {e}")
    exit(1)

