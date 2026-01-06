#!/usr/bin/env python3
"""
Investigar por que ainda há duplicatas após a correção
"""

import os
import sys
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)

print("="*80)
print("🔍 INVESTIGAÇÃO DE DUPLICATAS")
print("="*80)

# Categorias
print("\n📁 Variantes de 'Apartamento':")
cursor = conn.execute("""
    SELECT category, COUNT(*) as count, is_active
    FROM properties
    WHERE LOWER(category) = 'apartamento'
    GROUP BY category, is_active
    ORDER BY is_active DESC, count DESC
""")
for r in cursor.fetchall():
    active = "ATIVO" if r['is_active'] else "INATIVO"
    print(f"   '{r['category']}' ({active}): {r['count']:,}")

print("\n📁 Variantes de 'Casa':")
cursor = conn.execute("""
    SELECT category, COUNT(*) as count, is_active
    FROM properties
    WHERE LOWER(category) = 'casa'
    GROUP BY category, is_active
    ORDER BY is_active DESC, count DESC
""")
for r in cursor.fetchall():
    active = "ATIVO" if r['is_active'] else "INATIVO"
    print(f"   '{r['category']}' ({active}): {r['count']:,}")

print("\n📁 Todas as categorias (ATIVOS):")
cursor = conn.execute("""
    SELECT category, COUNT(*) as count
    FROM properties
    WHERE is_active = TRUE
    GROUP BY category
    ORDER BY count DESC
    LIMIT 20
""")
for r in cursor.fetchall():
    cat = r['category'] if r['category'] else '(NULL)'
    print(f"   '{cat}': {r['count']:,}")

print("\n" + "="*80)
print("💡 INSIGHT:")
print("   Se ainda houver 'APARTAMENTO', 'CASA', etc., significa que:")
print("   1. Há imóveis INATIVOS (is_active = FALSE) com essas categorias")
print("   2. OU o script fix_data_quality.py só atualizou is_active = TRUE")
print("="*80)

conn.close()

