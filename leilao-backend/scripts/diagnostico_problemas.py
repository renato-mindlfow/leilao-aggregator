#!/usr/bin/env python3
"""Script de diagnóstico para os 3 problemas pendentes."""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERRO: SUPABASE_URL e SUPABASE_KEY devem estar configurados no .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def diagnostico_problema_2():
    """Diagnosticar problema 2: Valores de 1º e 2º leilão trocados."""
    print("\n" + "=" * 60)
    print("DIAGNÓSTICO PROBLEMA 2: VALORES 1º E 2º LEILÃO TROCADOS")
    print("=" * 60)
    
    # Consultar propriedades de Campinas
    print("\n[1] Consultando propriedades de Campinas no banco...")
    response = supabase.table("properties").select(
        "id, title, first_auction_value, second_auction_value, evaluation_value, city, state, source"
    ).ilike("city", "%campinas%").limit(10).execute()
    
    if not response.data:
        print("  [AVISO] Nenhuma propriedade de Campinas encontrada.")
        return
    
    print(f"\n[2] Encontradas {len(response.data)} propriedades de Campinas:")
    print("-" * 60)
    
    for prop in response.data:
        print(f"\nID: {prop.get('id', 'N/A')[:20]}...")
        print(f"Título: {prop.get('title', 'N/A')[:50]}...")
        print(f"Cidade: {prop.get('city', 'N/A')}")
        print(f"Estado: {prop.get('state', 'N/A')}")
        print(f"Fonte: {prop.get('source', 'N/A')}")
        print(f"Valor Avaliação: {prop.get('evaluation_value', 'N/A')}")
        print(f"1º Leilão: {prop.get('first_auction_value', 'N/A')}")
        print(f"2º Leilão: {prop.get('second_auction_value', 'N/A')}")
        
        # Verificar se os valores estão na ordem esperada
        first = prop.get('first_auction_value')
        second = prop.get('second_auction_value')
        eval_val = prop.get('evaluation_value')
        
        if first and second:
            if first < second:
                print("  [PROBLEMA] 1o Leilao < 2o Leilao (deveria ser maior)")
            elif first > second:
                print("  [OK] Ordem correta: 1o Leilao > 2o Leilao")
            else:
                print("  [AVISO] Valores iguais")
        
        if eval_val and first:
            if eval_val < first:
                print("  [PROBLEMA] Avaliacao < 1o Leilao (deveria ser maior)")
    
    print("\n" + "-" * 60)
    print("[3] Verificando scrapers...")
    print("  - Verificar se superbid_scraper.py extrai corretamente os stages")
    print("  - Verificar se sync_to_supabase.py mapeia corretamente")

def diagnostico_problema_3():
    """Diagnosticar problema 3: Mapa sem marcadores (geocoding)."""
    print("\n" + "=" * 60)
    print("DIAGNÓSTICO PROBLEMA 3: MAPA SEM MARCADORES (GEOCODING)")
    print("=" * 60)
    
    # Contar total de propriedades
    print("\n[1] Contando propriedades no banco...")
    total_response = supabase.table("properties").select("id", count="exact").eq("is_active", True).execute()
    total = total_response.count or 0
    
    # Contar propriedades com coordenadas
    coords_response = supabase.table("properties").select(
        "id", count="exact"
    ).eq("is_active", True).not_.is_("latitude", "null").not_.is_("longitude", "null").execute()
    com_coords = coords_response.count or 0
    
    print(f"\n[2] Estatísticas:")
    print(f"  Total de propriedades ativas: {total}")
    print(f"  Com coordenadas (latitude/longitude): {com_coords}")
    print(f"  Sem coordenadas: {total - com_coords}")
    print(f"  Percentual com coordenadas: {(com_coords/total*100) if total > 0 else 0:.1f}%")
    
    if com_coords == 0:
        print("\n  [PROBLEMA] Nenhuma propriedade tem coordenadas!")
        print("  Acao: O geocoding nao esta rodando ou nao esta salvando coordenadas.")
    elif com_coords < total * 0.1:
        print("\n  [PROBLEMA] Poucas propriedades tem coordenadas (<10%)")
        print("  Acao: Criar script para geocodificar em batch.")
    else:
        print("\n  [OK] Muitas propriedades tem coordenadas.")
        print("  Verificar se o problema esta no frontend.")
    
    # Verificar algumas propriedades sem coordenadas
    print("\n[3] Verificando propriedades sem coordenadas...")
    sem_coords_response = supabase.table("properties").select(
        "id, title, city, state, address, geocoding_status"
    ).eq("is_active", True).is_("latitude", "null").limit(5).execute()
    
    if sem_coords_response.data:
        print(f"\n  Exemplo de propriedades sem coordenadas:")
        for prop in sem_coords_response.data[:3]:
            print(f"    - {prop.get('city', 'N/A')}, {prop.get('state', 'N/A')} - Status: {prop.get('geocoding_status', 'N/A')}")
    
    # Verificar algumas propriedades com coordenadas
    print("\n[4] Verificando propriedades com coordenadas...")
    com_coords_response = supabase.table("properties").select(
        "id, title, city, state, latitude, longitude"
    ).eq("is_active", True).not_.is_("latitude", "null").limit(5).execute()
    
    if com_coords_response.data:
        print(f"\n  Exemplo de propriedades com coordenadas:")
        for prop in com_coords_response.data[:3]:
            print(f"    - {prop.get('city', 'N/A')}, {prop.get('state', 'N/A')} - ({prop.get('latitude', 'N/A')}, {prop.get('longitude', 'N/A')})")

def diagnostico_problema_1():
    """Diagnosticar problema 1: Normalização na entrada."""
    print("\n" + "=" * 60)
    print("DIAGNÓSTICO PROBLEMA 1: NORMALIZAÇÃO NA ENTRADA")
    print("=" * 60)
    
    print("\n[1] Verificando dados no banco (exemplos de normalização)...")
    
    # Verificar categorias
    cat_response = supabase.table("properties").select("category").limit(100).execute()
    categorias = {}
    for prop in cat_response.data:
        cat = prop.get('category', '')
        categorias[cat] = categorias.get(cat, 0) + 1
    
    print(f"\n  Categorias encontradas (primeiras 10):")
    for cat, count in sorted(categorias.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    - '{cat}': {count} propriedades")
    
    # Verificar cidades
    city_response = supabase.table("properties").select("city").limit(100).execute()
    cidades = {}
    for prop in city_response.data:
        city = prop.get('city', '')
        cidades[city] = cidades.get(city, 0) + 1
    
    print(f"\n  Cidades encontradas (primeiras 10):")
    for city, count in sorted(cidades.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    - '{city}': {count} propriedades")
    
    # Verificar estados
    state_response = supabase.table("properties").select("state").limit(100).execute()
    estados = {}
    for prop in state_response.data:
        state = prop.get('state', '')
        estados[state] = estados.get(state, 0) + 1
    
    print(f"\n  Estados encontrados:")
    for state, count in sorted(estados.items(), key=lambda x: x[1], reverse=True):
        print(f"    - '{state}': {count} propriedades")
    
    print("\n[2] Verificando se sync_to_supabase.py tem normalização...")
    sync_file = Path(__file__).parent / "sync_to_supabase.py"
    if sync_file.exists():
        content = sync_file.read_text(encoding='utf-8')
        if 'normalize_property' in content:
            print("  [OK] Funcao normalize_property existe")
            if 'title()' in content or '.title()' in content:
                print("  [OK] Usa .title() para normalizacao")
            else:
                print("  [AVISO] Nao usa .title() para normalizacao")
        else:
            print("  [AVISO] Funcao normalize_property nao encontrada")

def main():
    print("=" * 60)
    print("DIAGNÓSTICO COMPLETO - 3 PROBLEMAS PENDENTES")
    print("=" * 60)
    
    diagnostico_problema_2()
    diagnostico_problema_3()
    diagnostico_problema_1()
    
    print("\n" + "=" * 60)
    print("DIAGNÓSTICO CONCLUÍDO")
    print("=" * 60)

if __name__ == "__main__":
    main()

