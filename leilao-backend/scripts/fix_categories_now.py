#!/usr/bin/env python3
"""
CORREÇÃO DIRETA DE CATEGORIAS EM UPPERCASE
"""

import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

print("="*60)
print("CORRIGINDO CATEGORIAS EM UPPERCASE")
print("="*60)

# Mapeamento direto - uppercase para Title Case
FIXES = {
    'APARTAMENTO': 'Apartamento',
    'TERRENO': 'Terreno',
    'OUTRO': 'Outro',
    'RURAL': 'Rural',
    'CASA': 'Casa',
    'COMERCIAL': 'Comercial',
    'GARAGEM': 'Garagem',
    'LOJA': 'Loja',
    'ÁREA': 'Área',
    'AREA': 'Área',
    'FAZENDA': 'Rural',
    'CHÁCARA': 'Rural',
    'CHACARA': 'Rural',
    'OUTROS': 'Outro',
}

total_fixed = 0

for wrong, correct in FIXES.items():
    # Primeiro, contar quantos existem
    count_result = supabase.table("properties").select("id", count="exact").eq("category", wrong).execute()
    count = count_result.count or 0
    
    if count > 0:
        print(f"\n'{wrong}' -> '{correct}': {count} registros")
        
        # Atualizar todos os registros de uma vez
        result = supabase.table("properties").update(
            {"category": correct}
        ).eq("category", wrong).execute()
        
        batch_count = len(result.data) if result.data else 0
        total_fixed += batch_count
        print(f"  OK: {batch_count} registros atualizados")

print(f"\n{'='*60}")
print(f"TOTAL CORRIGIDO: {total_fixed} registros")
print("="*60)

# Verificar resultado
print("\nVERIFICANDO CATEGORIAS APÓS CORREÇÃO:")
result = supabase.table("properties").select("category").execute()
categories = {}
for row in result.data or []:
    cat = row.get('category', 'N/A')
    categories[cat] = categories.get(cat, 0) + 1

for cat in sorted(categories.keys()):
    marker = " ⚠️" if cat.isupper() else ""
    print(f"  {cat}: {categories[cat]}{marker}")

