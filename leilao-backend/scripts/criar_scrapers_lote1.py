"""
Cria e testa scrapers para leiloeiros do Lote 1
"""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from app.services.universal_scraper import UniversalScraper
import asyncio

print("=" * 70)
print("TESTANDO SCRAPERS PARA LOTE 1")
print("=" * 70)

# Lista de sites para testar
sites = [
    {
        "name": "Vivaleiloes",
        "website": "https://www.vivaleiloes.com.br",
    },
    {
        "name": "Unileiloes",
        "website": "https://www.unileiloes.com.br",
    }
]

resultados = []

async def test_site(site):
    print(f"\n{'=' * 70}")
    print(f"TESTANDO: {site['name']}")
    print(f"URL: {site['website']}")
    print(f"{'=' * 70}")
    
    try:
        scraper = UniversalScraper()
        
        # Testar scraping
        properties = await scraper.scrape_auctioneer(site)
        
        # Limitar a 5 imóveis para teste
        properties = properties[:5] if len(properties) > 5 else properties
        
        print(f"\n✓ Sucesso!")
        print(f"  Imóveis encontrados: {len(properties)}")
        
        if properties:
            print(f"\n  Amostra do primeiro imóvel:")
            first = properties[0]
            print(f"    Título: {first.get('title', 'N/A')[:60]}")
            print(f"    Cidade: {first.get('city', 'N/A')}")
            print(f"    Estado: {first.get('state', 'N/A')}")
            print(f"    Preço: {first.get('price', 'N/A')}")
            print(f"    URL: {first.get('source_url', 'N/A')[:60]}")
            
            return {
                "nome": site['name'],
                "auctioneer_id": site['name'].lower(),
                "status": "SUCESSO",
                "imoveis": len(properties)
            }
        else:
            print(f"\n⚠ Nenhum imóvel retornado")
            return {
                "nome": site['name'],
                "auctioneer_id": site['name'].lower(),
                "status": "SEM_IMOVEIS",
                "imoveis": 0
            }
            
    except Exception as e:
        print(f"\n✗ Erro: {e}")
        import traceback
        traceback.print_exc()
        return {
            "nome": site['name'],
            "auctioneer_id": site['name'].lower(),
            "status": "ERRO",
            "erro": str(e)[:100]
        }

async def main():
    for site in sites:
        resultado = await test_site(site)
        resultados.append(resultado)

    # Resumo
    print(f"\n{'=' * 70}")
    print("RESUMO")
    print(f"{'=' * 70}")

    for r in resultados:
        print(f"\n{r['nome']} ({r['auctioneer_id']})")
        print(f"  Status: {r['status']}")
        if r['status'] == "SUCESSO":
            print(f"  Imóveis: {r['imoveis']}")
        elif r['status'] == "ERRO":
            print(f"  Erro: {r.get('erro', 'N/A')}")

    # Salvar resultados
    import json
    output_path = os.path.join(os.path.dirname(__file__), "scrapers_lote1_resultados.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\nResultados salvos em: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
