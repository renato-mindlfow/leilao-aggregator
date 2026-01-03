"""
Teste de integração do scraper smart
"""
import asyncio
import logging
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.scraper_orchestrator import scraper_orchestrator

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_smart_scraping():
    """Teste completo do fluxo de scraping inteligente"""
    
    print("=" * 60)
    print("TESTE DE INTEGRAÇÃO - SCRAPER SMART")
    print("=" * 60)
    
    # Testar com 3 leiloeiros que têm config
    print("\nExecutando run_all_smart(limit=3, skip_geocoding=True)...")
    
    try:
        result = await scraper_orchestrator.run_all_smart(
            skip_geocoding=True, 
            limit=3
        )
        
        print("\n" + "=" * 60)
        print("RESULTADO FINAL")
        print("=" * 60)
        print(f"Total processados: {result.get('total_auctioneers', 0)}")
        print(f"Sucesso: {result.get('successful', 0)}")
        print(f"Falhas: {result.get('failed', 0)}")
        print(f"Usou config: {result.get('used_config', 0)}")
        print(f"Usou fallback: {result.get('used_fallback', 0)}")
        print(f"Total imóveis: {result.get('total_properties', 0)}")
        print(f"Novos: {result.get('new_properties', 0)}")
        print(f"Atualizados: {result.get('updated_properties', 0)}")
        
        if result.get('errors'):
            print("\nERROS:")
            for err in result['errors']:
                print(f"  - {err.get('name', 'Unknown')}: {err.get('error', 'Unknown error')}")
        
        # Critérios de sucesso
        total = result.get('total_auctioneers', 0)
        successful = result.get('successful', 0)
        
        if total == 0:
            print("\n⚠️ Nenhum leiloeiro processado")
            return False
        
        success_rate = successful / total
        
        print("\n" + "=" * 60)
        if success_rate >= 0.5:
            print(f"✅ TESTE PASSOU! Taxa de sucesso: {success_rate:.0%}")
            print("=" * 60)
            return True
        else:
            print(f"❌ TESTE FALHOU! Taxa de sucesso: {success_rate:.0%}")
            print("=" * 60)
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_smart_scraping())
    sys.exit(0 if success else 1)

