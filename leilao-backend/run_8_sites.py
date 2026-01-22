"""
Script para executar scraping dos 8 sites identificados com imóveis
"""
import asyncio
import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.scrapers.scraper_manager import ScraperManager

# 8 sites com imóveis identificados na verificação
SITES_WITH_PROPERTIES = ['11', '48', '232', '74', '123', '80', '24', '95']

async def main():
    print("\n========================================")
    print("EXECUTANDO SCRAPERS DOS 8 SITES COM IMOVEIS")
    print("========================================\n")
    
    manager = ScraperManager()
    results = {}
    
    for site_id in SITES_WITH_PROPERTIES:
        try:
            print(f"\n[{site_id}] Iniciando scraping...")
            
            # Buscar informações do site
            auctioneer = await manager.supabase.table('auctioneers').select('*').eq('id', site_id).single().execute()
            
            if not auctioneer.data:
                print(f"[{site_id}] Leiloeiro não encontrado")
                results[site_id] = {'status': 'not_found', 'properties': 0}
                continue
            
            name = auctioneer.data.get('name', 'Unknown')
            website = auctioneer.data.get('website', '')
            
            print(f"[{site_id}] {name}")
            print(f"[{site_id}] URL: {website}")
            
            # Executar scraping
            success = await manager.run_scraper_by_id(site_id)
            
            if success:
                # Buscar contagem de propriedades
                props = await manager.supabase.table('properties').select('id', count='exact').eq('auctioneer_id', site_id).execute()
                prop_count = props.count or 0
                
                print(f"[{site_id}] SUCESSO - {prop_count} imóveis encontrados")
                results[site_id] = {'status': 'success', 'properties': prop_count}
            else:
                print(f"[{site_id}] ERRO no scraping")
                results[site_id] = {'status': 'error', 'properties': 0}
                
        except Exception as e:
            print(f"[{site_id}] EXCEPTION: {e}")
            results[site_id] = {'status': 'exception', 'properties': 0, 'error': str(e)}
    
    # Resumo final
    print("\n\n========================================")
    print("RESUMO FINAL")
    print("========================================\n")
    
    total_success = sum(1 for r in results.values() if r['status'] == 'success')
    total_properties = sum(r['properties'] for r in results.values())
    
    for site_id, result in results.items():
        status_emoji = "✅" if result['status'] == 'success' else "❌"
        print(f"{status_emoji} Site {site_id}: {result['status']} - {result['properties']} imóveis")
    
    print(f"\nTotal: {total_success}/{len(SITES_WITH_PROPERTIES)} sites com sucesso")
    print(f"Total de imóveis extraídos: {total_properties}")
    print("\n========================================\n")

if __name__ == "__main__":
    asyncio.run(main())
