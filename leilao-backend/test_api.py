"""
Testes da API de propriedades.
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

# URL base da API (ajuste conforme necessário)
BASE_URL = os.getenv("API_URL", "http://localhost:8000")

def test_list_properties():
    """Testa listagem básica."""
    print("=" * 60)
    print("TESTE: Listagem de propriedades")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/properties")
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total: {data['total']}")
        print(f"Página: {data['page']}/{data['total_pages']}")
        print(f"Itens na página: {len(data['data'])}")
        print("✅ PASSOU")
    else:
        print(f"❌ FALHOU: {response.text}")

def test_filter_by_state():
    """Testa filtro por estado."""
    print("\n" + "=" * 60)
    print("TESTE: Filtro por estado (SP)")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/properties?state=SP")
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total em SP: {data['total']}")
        
        # Verifica se todos são de SP
        all_sp = all(p.get('state') == 'SP' for p in data['data'])
        if all_sp:
            print("✅ PASSOU - Todos os resultados são de SP")
        else:
            print("⚠️ AVISO - Alguns resultados não são de SP")
    else:
        print(f"❌ FALHOU: {response.text}")

def test_filter_by_category():
    """Testa filtro por categoria."""
    print("\n" + "=" * 60)
    print("TESTE: Filtro por categoria (Apartamento)")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/properties?category=Apartamento")
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total de Apartamentos: {data['total']}")
        print("✅ PASSOU")
    else:
        print(f"❌ FALHOU: {response.text}")

def test_sorting():
    """Testa ordenação."""
    print("\n" + "=" * 60)
    print("TESTE: Ordenação por valor (ascendente)")
    print("=" * 60)
    
    response = requests.get(
        f"{BASE_URL}/api/properties?sort_by=first_auction_value&order=asc&page_size=5"
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        values = [p.get('first_auction_value') for p in data['data'] if p.get('first_auction_value')]
        
        print("Primeiros 5 valores:")
        for i, v in enumerate(values, 1):
            print(f"  {i}. R$ {v:,.2f}")
        
        # Verifica se está ordenado
        is_sorted = values == sorted(values)
        if is_sorted:
            print("✅ PASSOU - Valores ordenados corretamente")
        else:
            print("⚠️ AVISO - Valores podem não estar ordenados")
    else:
        print(f"❌ FALHOU: {response.text}")

def test_stats():
    """Testa endpoint de estatísticas."""
    print("\n" + "=" * 60)
    print("TESTE: Estatísticas")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/properties/stats")
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total de propriedades: {data['total_properties']}")
        print(f"Total ativos: {data['total_active']}")
        print(f"Desconto médio: {data.get('avg_discount', 'N/A')}%")
        print("\nPor categoria:")
        for cat, count in data['by_category'].items():
            print(f"  - {cat}: {count}")
        print("✅ PASSOU")
    else:
        print(f"❌ FALHOU: {response.text}")

def test_categories_endpoint():
    """Testa endpoint de categorias."""
    print("\n" + "=" * 60)
    print("TESTE: Lista de categorias")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/properties/categories")
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Categorias: {data['categories']}")
        print("✅ PASSOU")
    else:
        print(f"❌ FALHOU: {response.text}")

def test_states_endpoint():
    """Testa endpoint de estados."""
    print("\n" + "=" * 60)
    print("TESTE: Lista de estados")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/properties/states")
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Estados ({len(data['states'])}): {', '.join(data['states'][:10])}...")
        print("✅ PASSOU")
    else:
        print(f"❌ FALHOU: {response.text}")

def main():
    print("\n" + "=" * 60)
    print("TESTES DA API DE PROPRIEDADES")
    print("=" * 60)
    print(f"URL Base: {BASE_URL}\n")
    
    test_list_properties()
    test_filter_by_state()
    test_filter_by_category()
    test_sorting()
    test_stats()
    test_categories_endpoint()
    test_states_endpoint()
    
    print("\n" + "=" * 60)
    print("TESTES CONCLUÍDOS")
    print("=" * 60)

if __name__ == "__main__":
    main()

