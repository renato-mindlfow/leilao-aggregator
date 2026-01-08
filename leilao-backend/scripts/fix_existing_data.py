#!/usr/bin/env python3
"""
CORRIGE DADOS EXISTENTES NO BANCO
Normaliza estados, categorias e cidades de todos os imóveis.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.utils.normalizer import normalize_state, normalize_category, normalize_city

# Conectar ao Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def fix_states():
    """Corrige estados não normalizados."""
    print("\n" + "="*60)
    print("CORRIGINDO ESTADOS")
    print("="*60)
    
    # Buscar estados únicos problemáticos
    result = supabase.table("properties").select("state").execute()
    
    states_to_fix = {}
    for row in result.data or []:
        state = row.get('state', '')
        if state and state != normalize_state(state):
            correct = normalize_state(state)
            if state not in states_to_fix:
                states_to_fix[state] = correct
    
    print(f"Estados a corrigir: {len(states_to_fix)}")
    for wrong, correct in states_to_fix.items():
        print(f"  '{wrong}' -> '{correct}'")
    
    # Corrigir cada estado
    total_fixed = 0
    for wrong, correct in states_to_fix.items():
        result = supabase.table("properties").update({
            "state": correct
        }).eq("state", wrong).execute()
        
        count = len(result.data) if result.data else 0
        total_fixed += count
        print(f"  Corrigido '{wrong}' -> '{correct}': {count} registros")
    
    print(f"\n✅ Total de registros corrigidos (estados): {total_fixed}")
    return total_fixed


def fix_categories():
    """Corrige categorias não normalizadas."""
    print("\n" + "="*60)
    print("CORRIGINDO CATEGORIAS")
    print("="*60)
    
    # Buscar categorias únicas problemáticas
    result = supabase.table("properties").select("category").execute()
    
    categories_to_fix = {}
    for row in result.data or []:
        cat = row.get('category', '')
        if cat and cat != normalize_category(cat):
            correct = normalize_category(cat)
            if cat not in categories_to_fix:
                categories_to_fix[cat] = correct
    
    print(f"Categorias a corrigir: {len(categories_to_fix)}")
    for wrong, correct in categories_to_fix.items():
        print(f"  '{wrong}' -> '{correct}'")
    
    # Corrigir cada categoria
    total_fixed = 0
    for wrong, correct in categories_to_fix.items():
        result = supabase.table("properties").update({
            "category": correct
        }).eq("category", wrong).execute()
        
        count = len(result.data) if result.data else 0
        total_fixed += count
        print(f"  Corrigido '{wrong}' -> '{correct}': {count} registros")
    
    print(f"\n✅ Total de registros corrigidos (categorias): {total_fixed}")
    return total_fixed


def fix_cities():
    """Corrige cidades com sufixo de estado."""
    print("\n" + "="*60)
    print("CORRIGINDO CIDADES")
    print("="*60)
    
    # Buscar cidades com padrão de sufixo
    result = supabase.table("properties").select("city").execute()
    
    cities_to_fix = {}
    for row in result.data or []:
        city = row.get('city', '')
        if city:
            correct = normalize_city(city)
            if city != correct:
                if city not in cities_to_fix:
                    cities_to_fix[city] = correct
    
    print(f"Cidades a corrigir: {len(cities_to_fix)}")
    for wrong, correct in list(cities_to_fix.items())[:20]:  # Mostrar primeiras 20
        print(f"  '{wrong}' -> '{correct}'")
    if len(cities_to_fix) > 20:
        print(f"  ... e mais {len(cities_to_fix) - 20}")
    
    # Corrigir cada cidade
    total_fixed = 0
    for wrong, correct in cities_to_fix.items():
        result = supabase.table("properties").update({
            "city": correct
        }).eq("city", wrong).execute()
        
        count = len(result.data) if result.data else 0
        total_fixed += count
        if count > 0:
            print(f"  Corrigido '{wrong}' -> '{correct}': {count} registros")
    
    print(f"\n✅ Total de registros corrigidos (cidades): {total_fixed}")
    return total_fixed


def main():
    print("="*60)
    print("CORREÇÃO DE DADOS EXISTENTES")
    print("="*60)
    
    # Verificar conexão
    result = supabase.table("properties").select("id", count="exact").limit(1).execute()
    total = result.count or 0
    print(f"\nTotal de imóveis no banco: {total:,}")
    
    # Corrigir
    states_fixed = fix_states()
    categories_fixed = fix_categories()
    cities_fixed = fix_cities()
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO")
    print("="*60)
    print(f"Estados corrigidos: {states_fixed}")
    print(f"Categorias corrigidas: {categories_fixed}")
    print(f"Cidades corrigidas: {cities_fixed}")
    print(f"Total: {states_fixed + categories_fixed + cities_fixed}")
    print("\n✅ Correção concluída!")


if __name__ == "__main__":
    main()

