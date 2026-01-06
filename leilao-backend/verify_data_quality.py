#!/usr/bin/env python3
"""
Script para verificar a qualidade dos dados após correção
"""

import os
import sys
from dotenv import load_dotenv

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ [ERRO] DATABASE_URL não configurada no .env")
    sys.exit(1)

print("="*80)
print("🔍 VERIFICAÇÃO FINAL DE QUALIDADE DE DADOS")
print("="*80)

try:
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    
    # Métricas gerais
    print("\n📊 MÉTRICAS GERAIS:")
    cursor = conn.execute('SELECT COUNT(DISTINCT category) as cats FROM properties WHERE is_active = TRUE')
    print(f"   ✅ Categorias únicas: {cursor.fetchone()['cats']}")
    
    cursor = conn.execute('SELECT COUNT(DISTINCT city) as cities FROM properties WHERE is_active = TRUE')
    print(f"   ✅ Cidades únicas: {cursor.fetchone()['cities']:,}")
    
    cursor = conn.execute('SELECT COUNT(DISTINCT neighborhood) as hoods FROM properties WHERE is_active = TRUE AND neighborhood IS NOT NULL')
    print(f"   ✅ Bairros únicos: {cursor.fetchone()['hoods']:,}")
    
    cursor = conn.execute('SELECT COUNT(*) as total FROM properties WHERE is_active = TRUE')
    print(f"   ✅ Total de imóveis ativos: {cursor.fetchone()['total']:,}")
    
    # Verificar duplicatas
    print("\n🔍 VERIFICAÇÃO DE DUPLICATAS:")
    
    cursor = conn.execute("""
        SELECT LOWER(category) as cat, COUNT(DISTINCT category) as vars 
        FROM properties WHERE is_active = TRUE 
        GROUP BY LOWER(category) 
        HAVING COUNT(DISTINCT category) > 1
    """)
    cat_dups = cursor.fetchall()
    
    if cat_dups:
        print(f"   ⚠️  Duplicatas de categoria: {len(cat_dups)}")
        for dup in cat_dups[:5]:
            print(f"      - {dup['cat']}: {dup['vars']} variantes")
    else:
        print(f"   ✅ Duplicatas de categoria: 0")
    
    cursor = conn.execute("""
        SELECT LOWER(city) as city, COUNT(DISTINCT city) as vars 
        FROM properties WHERE is_active = TRUE 
        GROUP BY LOWER(city) 
        HAVING COUNT(DISTINCT city) > 1
    """)
    city_dups = cursor.fetchall()
    
    if city_dups:
        print(f"   ⚠️  Duplicatas de cidade: {len(city_dups)}")
        for dup in city_dups[:5]:
            print(f"      - {dup['city']}: {dup['vars']} variantes")
    else:
        print(f"   ✅ Duplicatas de cidade: 0")
    
    cursor = conn.execute("""
        SELECT LOWER(neighborhood) as hood, COUNT(DISTINCT neighborhood) as vars 
        FROM properties WHERE is_active = TRUE AND neighborhood IS NOT NULL 
        GROUP BY LOWER(neighborhood) 
        HAVING COUNT(DISTINCT neighborhood) > 1
    """)
    hood_dups = cursor.fetchall()
    
    if hood_dups:
        print(f"   ⚠️  Duplicatas de bairro: {len(hood_dups)}")
        for dup in hood_dups[:5]:
            print(f"      - {dup['hood']}: {dup['vars']} variantes")
    else:
        print(f"   ✅ Duplicatas de bairro: 0")
    
    # Top 10 categorias
    print("\n📁 TOP 10 CATEGORIAS:")
    cursor = conn.execute("""
        SELECT category, COUNT(*) as count
        FROM properties
        WHERE is_active = TRUE
        GROUP BY category
        ORDER BY count DESC
        LIMIT 10
    """)
    cats = cursor.fetchall()
    for cat in cats:
        cat_name = cat['category'] if cat['category'] else '(vazio)'
        print(f"   {cat_name:20} {cat['count']:>6,} imóveis")
    
    conn.close()
    
    print("\n" + "="*80)
    if not cat_dups and not city_dups and not hood_dups:
        print("✅ QUALIDADE DE DADOS: EXCELENTE!")
        print("   Nenhuma duplicata detectada.")
    else:
        print("⚠️  ATENÇÃO: Ainda há duplicatas a corrigir")
    print("="*80)
    
except Exception as e:
    print(f"❌ [ERRO] {e}")
    sys.exit(1)

