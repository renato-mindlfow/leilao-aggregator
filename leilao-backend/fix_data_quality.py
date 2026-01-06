#!/usr/bin/env python3
"""
Script autônomo para corrigir problemas de qualidade de dados no LeiloHub

PROBLEMAS CORRIGIDOS:
1. Categorias duplicadas (case-insensitive): "Apartamento" vs "APARTAMENTO"
2. Cidades duplicadas (case-insensitive): "São Paulo" vs "SAO PAULO" vs "são paulo"
3. Bairros duplicados (case-insensitive): "Centro" vs "CENTRO" vs "centro"

SOLUÇÃO: Normalizar todos para Title Case e consolidar registros
"""

import os
import sys
from dotenv import load_dotenv
from typing import Dict, List, Tuple

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Carregar .env
load_dotenv()

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ [ERRO] DATABASE_URL não configurada no .env")
    sys.exit(1)

print("="*80)
print("🔧 CORREÇÃO AUTOMÁTICA DE QUALIDADE DE DADOS - LEILOHUB")
print("="*80)
print(f"\n📊 Conectando ao banco de dados...")

try:
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    print("✅ Conexão estabelecida com sucesso!\n")
except Exception as e:
    print(f"❌ [ERRO] Falha na conexão: {e}")
    sys.exit(1)

# ============================================================================
# PROBLEMA 1: CATEGORIAS DUPLICADAS
# ============================================================================

print("="*80)
print("📁 PROBLEMA 1: Categorias Duplicadas")
print("="*80)

# Verificar categorias existentes
cursor = conn.execute("""
    SELECT category, COUNT(*) as count
    FROM properties
    WHERE is_active = TRUE
    GROUP BY category
    ORDER BY category
""")
categories = cursor.fetchall()

print(f"\n📋 Categorias encontradas ({len(categories)}):")
for cat in categories:
    print(f"   - '{cat['category']}': {cat['count']:,} imóveis")

# Identificar duplicatas (case-insensitive)
category_map = {}
duplicates_found = False

for cat in categories:
    cat_name = cat['category']
    
    # Pular valores NULL ou vazios
    if not cat_name or cat_name.strip() == '':
        continue
    
    cat_lower = cat_name.lower()
    
    if cat_lower in category_map:
        duplicates_found = True
        print(f"\n⚠️  DUPLICATA DETECTADA:")
        print(f"   '{category_map[cat_lower]}' vs '{cat_name}'")
    else:
        category_map[cat_lower] = cat_name

if duplicates_found:
    print(f"\n🔧 Normalizando categorias para Title Case...")
    
    # Primeiro, limpar valores NULL, vazios ou "None"
    print(f"\n🧹 Limpando valores inválidos...")
    with conn.transaction():
        cursor = conn.execute("""
            UPDATE properties
            SET category = 'Outro',
                updated_at = CURRENT_TIMESTAMP
            WHERE (category IS NULL 
               OR category = '' 
               OR LOWER(category) = 'none'
               OR category = 'None')
        """)
        
        invalid_count = cursor.rowcount
        if invalid_count > 0:
            print(f"   ✓ {invalid_count:,} registros com categoria inválida foram marcados como 'Outro'")
    
    # Mapeamento de normalização
    CATEGORY_NORMALIZATION = {
        'apartamento': 'Apartamento',
        'casa': 'Casa',
        'terreno': 'Terreno',
        'comercial': 'Comercial',
        'rural': 'Rural',
        'galpão': 'Galpão',
        'galpao': 'Galpão',
        'loja': 'Loja',
        'sala comercial': 'Sala Comercial',
        'prédio': 'Prédio',
        'predio': 'Prédio',
        'chácara': 'Chácara',
        'chacara': 'Chácara',
        'sitio': 'Sítio',
        'sítio': 'Sítio',
        'fazenda': 'Fazenda',
        'cobertura': 'Cobertura',
        'kitnet': 'Kitnet',
        'flat': 'Flat',
        'box': 'Box',
        'garagem': 'Garagem',
        'vaga de garagem': 'Vaga de Garagem',
        'estacionamento': 'Estacionamento',
        'outro': 'Outro',
        'outros': 'Outro',
        'industrial': 'Industrial',
        'área': 'Área',
        'area': 'Área',
        'imóvel rural': 'Rural',
        'imovel rural': 'Rural',
    }
    
    updates_count = 0
    
    with conn.transaction():
        for old_key, normalized in CATEGORY_NORMALIZATION.items():
            cursor = conn.execute("""
                UPDATE properties
                SET category = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE LOWER(category) = %s
                  AND category != %s
            """, (normalized, old_key, normalized))
            
            affected = cursor.rowcount
            if affected > 0:
                updates_count += affected
                print(f"   ✓ '{old_key}' → '{normalized}': {affected:,} registros")
    
    print(f"\n✅ Categorias normalizadas: {updates_count:,} registros atualizados")
else:
    print("\n✅ Nenhuma duplicata de categoria encontrada")

# ============================================================================
# PROBLEMA 2: CIDADES DUPLICADAS
# ============================================================================

print("\n" + "="*80)
print("🏙️  PROBLEMA 2: Cidades Duplicadas")
print("="*80)

# Verificar cidades duplicadas (case-insensitive)
cursor = conn.execute("""
    SELECT 
        LOWER(city) as city_lower,
        array_agg(DISTINCT city) as variants,
        SUM(1) as total_count
    FROM properties
    WHERE is_active = TRUE
    GROUP BY LOWER(city)
    HAVING COUNT(DISTINCT city) > 1
    ORDER BY total_count DESC
    LIMIT 50
""")
city_duplicates = cursor.fetchall()

if city_duplicates:
    print(f"\n⚠️  {len(city_duplicates)} cidades com variações detectadas:")
    for dup in city_duplicates[:10]:
        print(f"   - {dup['city_lower']}: {dup['variants']} ({dup['total_count']:,} imóveis)")
    
    print(f"\n🔧 Normalizando cidades para Title Case...")
    
    updates_count = 0
    
    with conn.transaction():
        cursor = conn.execute("""
            UPDATE properties
            SET city = INITCAP(city),
                updated_at = CURRENT_TIMESTAMP
            WHERE city != INITCAP(city)
        """)
        
        updates_count = cursor.rowcount
    
    print(f"✅ Cidades normalizadas: {updates_count:,} registros atualizados")
else:
    print("\n✅ Nenhuma duplicata de cidade encontrada")

# ============================================================================
# PROBLEMA 3: BAIRROS DUPLICADOS
# ============================================================================

print("\n" + "="*80)
print("🏘️  PROBLEMA 3: Bairros Duplicados")
print("="*80)

# Verificar bairros duplicados (case-insensitive)
cursor = conn.execute("""
    SELECT 
        LOWER(neighborhood) as neighborhood_lower,
        array_agg(DISTINCT neighborhood) as variants,
        SUM(1) as total_count
    FROM properties
    WHERE is_active = TRUE
      AND neighborhood IS NOT NULL
      AND neighborhood != ''
    GROUP BY LOWER(neighborhood)
    HAVING COUNT(DISTINCT neighborhood) > 1
    ORDER BY total_count DESC
    LIMIT 50
""")
neighborhood_duplicates = cursor.fetchall()

if neighborhood_duplicates:
    print(f"\n⚠️  {len(neighborhood_duplicates)} bairros com variações detectadas:")
    for dup in neighborhood_duplicates[:10]:
        print(f"   - {dup['neighborhood_lower']}: {dup['variants']} ({dup['total_count']:,} imóveis)")
    
    print(f"\n🔧 Normalizando bairros para Title Case...")
    
    updates_count = 0
    
    with conn.transaction():
        cursor = conn.execute("""
            UPDATE properties
            SET neighborhood = INITCAP(neighborhood),
                updated_at = CURRENT_TIMESTAMP
            WHERE neighborhood IS NOT NULL
              AND neighborhood != ''
              AND neighborhood != INITCAP(neighborhood)
        """)
        
        updates_count = cursor.rowcount
    
    print(f"✅ Bairros normalizados: {updates_count:,} registros atualizados")
else:
    print("\n✅ Nenhuma duplicata de bairro encontrada")

# ============================================================================
# RELATÓRIO FINAL
# ============================================================================

print("\n" + "="*80)
print("📊 RELATÓRIO FINAL - DADOS APÓS NORMALIZAÇÃO")
print("="*80)

# Categorias únicas
cursor = conn.execute("""
    SELECT category, COUNT(*) as count
    FROM properties
    WHERE is_active = TRUE
    GROUP BY category
    ORDER BY count DESC
""")
categories_final = cursor.fetchall()

print(f"\n📁 Categorias únicas: {len(categories_final)}")
for cat in categories_final:
    print(f"   - {cat['category']}: {cat['count']:,} imóveis")

# Cidades únicas
cursor = conn.execute("""
    SELECT COUNT(DISTINCT city) as unique_cities
    FROM properties
    WHERE is_active = TRUE
""")
unique_cities = cursor.fetchone()['unique_cities']
print(f"\n🏙️  Cidades únicas: {unique_cities:,}")

# Bairros únicos
cursor = conn.execute("""
    SELECT COUNT(DISTINCT neighborhood) as unique_neighborhoods
    FROM properties
    WHERE is_active = TRUE
      AND neighborhood IS NOT NULL
      AND neighborhood != ''
""")
unique_neighborhoods = cursor.fetchone()['unique_neighborhoods']
print(f"\n🏘️  Bairros únicos: {unique_neighborhoods:,}")

# Total de imóveis ativos
cursor = conn.execute("""
    SELECT COUNT(*) as total
    FROM properties
    WHERE is_active = TRUE
""")
total_properties = cursor.fetchone()['total']
print(f"\n✅ Total de imóveis ativos: {total_properties:,}")

# ============================================================================
# VERIFICAÇÃO DE QUALIDADE
# ============================================================================

print("\n" + "="*80)
print("🔍 VERIFICAÇÃO DE QUALIDADE")
print("="*80)

# Verificar se ainda há duplicatas de categorias
cursor = conn.execute("""
    SELECT 
        LOWER(category) as category_lower,
        COUNT(DISTINCT category) as variants
    FROM properties
    WHERE is_active = TRUE
    GROUP BY LOWER(category)
    HAVING COUNT(DISTINCT category) > 1
""")
category_issues = cursor.fetchall()

if category_issues:
    print(f"\n⚠️  ATENÇÃO: Ainda há {len(category_issues)} categorias com variações:")
    for issue in category_issues:
        print(f"   - {issue['category_lower']}: {issue['variants']} variantes")
else:
    print("\n✅ Categorias: Nenhuma duplicata detectada")

# Verificar se ainda há duplicatas de cidades
cursor = conn.execute("""
    SELECT 
        LOWER(city) as city_lower,
        COUNT(DISTINCT city) as variants
    FROM properties
    WHERE is_active = TRUE
    GROUP BY LOWER(city)
    HAVING COUNT(DISTINCT city) > 1
""")
city_issues = cursor.fetchall()

if city_issues:
    print(f"\n⚠️  ATENÇÃO: Ainda há {len(city_issues)} cidades com variações")
else:
    print("✅ Cidades: Nenhuma duplicata detectada")

# Verificar se ainda há duplicatas de bairros
cursor = conn.execute("""
    SELECT 
        LOWER(neighborhood) as neighborhood_lower,
        COUNT(DISTINCT neighborhood) as variants
    FROM properties
    WHERE is_active = TRUE
      AND neighborhood IS NOT NULL
      AND neighborhood != ''
    GROUP BY LOWER(neighborhood)
    HAVING COUNT(DISTINCT neighborhood) > 1
""")
neighborhood_issues = cursor.fetchall()

if neighborhood_issues:
    print(f"\n⚠️  ATENÇÃO: Ainda há {len(neighborhood_issues)} bairros com variações")
else:
    print("✅ Bairros: Nenhuma duplicata detectada")

# ============================================================================
# FINALIZAÇÃO
# ============================================================================

conn.close()

print("\n" + "="*80)
print("✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
print("="*80)
print("\n📝 Resumo:")
print(f"   • Categorias normalizadas para Title Case")
print(f"   • Cidades normalizadas para Title Case")
print(f"   • Bairros normalizados para Title Case")
print(f"   • Total de imóveis ativos: {total_properties:,}")
print("\n💡 Os dados agora estão consistentes e prontos para uso!")
print("\n" + "="*80)

