from dotenv import load_dotenv
import os
load_dotenv()

from supabase import create_client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

print('=== STATUS GERAL DO SISTEMA ===')

# Total de imoveis
props = supabase.table('properties').select('id', count='exact').execute()
print(f'Total de imoveis: {props.count}')

# Total de leiloeiros
aucs = supabase.table('auctioneers').select('id', count='exact').execute()
print(f'Total de leiloeiros: {aucs.count}')

print()
print('=== STATUS DOS SCRAPERS ===')

# Contar por status
for status in ['success', 'error', 'pending', 'needs_playwright']:
    count = supabase.table('auctioneers').select('id', count='exact').eq('scrape_status', status).execute()
    print(f'  {status}: {count.count}')

print()
print('=== LEILOEIROS COM ERRO ===')
erros = supabase.table('auctioneers').select('id, name, scrape_error, property_count').eq('scrape_status', 'error').limit(10).execute()
for e in erros.data:
    erro_msg = str(e.get('scrape_error', ''))[:50] if e.get('scrape_error') else 'None'
    print(f"  {e['name']}: {e['property_count']} imoveis - {erro_msg}")

print()
print('=== ULTIMOS SCRAPES (por data) ===')
recentes = supabase.table('auctioneers').select('name, last_scrape, scrape_status, property_count').order('last_scrape', desc=True).limit(5).execute()
for r in recentes.data:
    print(f"  {r['name']}: {r['last_scrape']} ({r['scrape_status']})")
