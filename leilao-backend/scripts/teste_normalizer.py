"""
Teste unitário do normalizer com valores None e tipos errados
"""
import asyncio
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai_normalizer import ai_normalizer

def test_normalize_with_none_values():
    """Testa normalização com valores None"""
    
    print("=" * 60)
    print("TESTE UNITÁRIO - AI NORMALIZER")
    print("=" * 60)
    
    # Caso 1: Todos os campos None
    print("\n[Teste 1] Todos os campos None")
    prop_all_none = {
        'title': None,
        'price': None,
        'area': None,
        'category': None,
        'state': None,
        'city': None,
        'address': None,
    }
    
    try:
        result = asyncio.run(ai_normalizer.normalize_property(prop_all_none))
        print("  ✅ Teste 1 (todos None): OK")
        print(f"     Resultado: {result}")
    except Exception as e:
        print(f"  ❌ Teste 1 (todos None): FALHOU - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Caso 2: Alguns campos None
    print("\n[Teste 2] Alguns campos None")
    prop_some_none = {
        'title': 'Apartamento 2 quartos',
        'price': 150000,
        'area': None,  # None
        'category': 'Apartamento',
        'state': None,  # None
        'city': 'São Paulo',
        'address': None,  # None
    }
    
    try:
        result = asyncio.run(ai_normalizer.normalize_property(prop_some_none))
        print("  ✅ Teste 2 (alguns None): OK")
        print(f"     Resultado: {result}")
    except Exception as e:
        print(f"  ❌ Teste 2 (alguns None): FALHOU - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Caso 3: Campos vazios (string vazia)
    print("\n[Teste 3] Campos vazios (string vazia)")
    prop_empty = {
        'title': '',
        'price': '',
        'area': '',
        'category': '',
        'state': '',
        'city': '',
    }
    
    try:
        result = asyncio.run(ai_normalizer.normalize_property(prop_empty))
        print("  ✅ Teste 3 (strings vazias): OK")
        print(f"     Resultado: {result}")
    except Exception as e:
        print(f"  ❌ Teste 3 (strings vazias): FALHOU - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Caso 4: Tipos errados
    print("\n[Teste 4] Tipos errados")
    prop_wrong_types = {
        'title': 123,  # int ao invés de string
        'price': 'abc',  # string ao invés de número
        'area': ['100m²'],  # lista ao invés de string
        'category': {'type': 'apt'},  # dict ao invés de string
        'state': 42,  # int ao invés de string
        'city': True,  # bool ao invés de string
    }
    
    try:
        result = asyncio.run(ai_normalizer.normalize_property(prop_wrong_types))
        print("  ✅ Teste 4 (tipos errados): OK")
        print(f"     Resultado: {result}")
    except Exception as e:
        print(f"  ❌ Teste 4 (tipos errados): FALHOU - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Caso 5: Valores válidos
    print("\n[Teste 5] Valores válidos")
    prop_valid = {
        'title': 'Apartamento 2 quartos em São Paulo',
        'price': 'R$ 150.000,00',
        'area': '80 m²',
        'category': 'Apartamento',
        'state': 'São Paulo',
        'city': 'são paulo',
        'address': 'Rua das Flores, 123',
    }
    
    try:
        result = asyncio.run(ai_normalizer.normalize_property(prop_valid))
        print("  ✅ Teste 5 (valores válidos): OK")
        print(f"     Resultado: {result}")
    except Exception as e:
        print(f"  ❌ Teste 5 (valores válidos): FALHOU - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_normalize_with_none_values()
    sys.exit(0 if success else 1)

