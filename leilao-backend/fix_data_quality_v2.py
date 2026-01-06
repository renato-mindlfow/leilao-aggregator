#!/usr/bin/env python3
"""
Script CORRIGIDO para normalizar dados - versão 2
Usa transações explícitas e COMMIT manual
"""

import os
import sys
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ [ERRO] DATABASE_URL não configurada")
    sys.exit(1)

print("="*80)
print("🔧 CORREÇÃO DE QUALIDADE DE DADOS - V2")
print("="*80)

conn = psycopg.connect(DATABASE_URL, autocommit=False)

try:
    print("\n📁 CORRIGINDO CATEGORIAS...")
    
    # Lista de atualizações
    updates = [
        ("apartamento", "Apartamento"),
        ("casa", "Casa"),
        ("terreno", "Terreno"),
        ("comercial", "Comercial"),
        ("rural", "Rural"),
        ("outro", "Outro"),
        ("outros", "Outro"),
        ("galpao", "Galpão"),
        ("galpão", "Galpão"),
        ("imóvel rural", "Rural"),
        ("imovel rural", "Rural"),
    ]
    
    total_updated = 0
    
    for old_val, new_val in updates:
        cursor = conn.execute("""
            UPDATE properties
            SET category = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE LOWER(category) = %s
              AND category != %s
        """, (new_val, old_val, new_val))
        
        count = cursor.rowcount
        total_updated += count
        if count > 0:
            print(f"   ✓ '{old_val}' → '{new_val}': {count:,} registros")
    
    # Limpar valores NULL/vazios
    cursor = conn.execute("""
        UPDATE properties
        SET category = 'Outro',
            updated_at = CURRENT_TIMESTAMP
        WHERE category IS NULL OR category = '' OR category = 'None'
    """)
    null_count = cursor.rowcount
    if null_count > 0:
        print(f"   ✓ NULL/vazios → 'Outro': {null_count:,} registros")
        total_updated += null_count
    
    # COMMIT das categorias
    conn.commit()
    print(f"\n✅ Categorias: {total_updated:,} registros atualizados e COMMIT realizado")
    
    print("\n🏙️  CORRIGINDO CIDADES...")
    cursor = conn.execute("""
        UPDATE properties
        SET city = INITCAP(city),
            updated_at = CURRENT_TIMESTAMP
        WHERE city IS NOT NULL
          AND city != ''
          AND city != INITCAP(city)
    """)
    city_count = cursor.rowcount
    conn.commit()
    print(f"✅ Cidades: {city_count:,} registros atualizados e COMMIT realizado")
    
    print("\n🏘️  CORRIGINDO BAIRROS...")
    cursor = conn.execute("""
        UPDATE properties
        SET neighborhood = INITCAP(neighborhood),
            updated_at = CURRENT_TIMESTAMP
        WHERE neighborhood IS NOT NULL
          AND neighborhood != ''
          AND neighborhood != INITCAP(neighborhood)
    """)
    hood_count = cursor.rowcount
    conn.commit()
    print(f"✅ Bairros: {hood_count:,} registros atualizados e COMMIT realizado")
    
    print("\n" + "="*80)
    print("✅ CORREÇÃO CONCLUÍDA!")
    print("="*80)
    print(f"\nTotal de registros atualizados:")
    print(f"  • Categorias: {total_updated:,}")
    print(f"  • Cidades: {city_count:,}")
    print(f"  • Bairros: {hood_count:,}")
    print(f"  • TOTAL: {total_updated + city_count + hood_count:,}")
    
except Exception as e:
    conn.rollback()
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    conn.close()

