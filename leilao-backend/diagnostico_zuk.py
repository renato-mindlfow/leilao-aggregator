from dotenv import load_dotenv
import os
load_dotenv()

from supabase import create_client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

print('=== DIAGNOSTICO COMPLETO PORTAL ZUK ===')

zuk = supabase.table('auctioneers').select('*').eq('id', '1').execute()
if zuk.data:
    z = zuk.data[0]
    print(f"ID: {z.get('id')}")
    print(f"Nome: {z.get('name')}")
    print(f"Website: {z.get('website')}")
    print(f"Property Count: {z.get('property_count')}")
    print(f"Scrape Status: {z.get('scrape_status')}")
    print(f"Scrape Error: {z.get('scrape_error')}")
    print(f"Last Scrape: {z.get('last_scrape')}")

print()

all_zuk = supabase.table('auctioneers').select('id, name, property_count').ilike('name', '%zuk%').execute()
print(f'Entradas com Zuk no nome: {len(all_zuk.data)}')
for z in all_zuk.data:
    print(f'  - {z}')

print()

props = supabase.table('properties').select('id, title, auctioneer_id').eq('auctioneer_id', '1').execute()
print(f'Imoveis com auctioneer_id=1: {len(props.data)}')

props2 = supabase.table('properties').select('id, title, auctioneer_id').ilike('auctioneer_id', '%zuk%').execute()
print(f'Imoveis com zuk no auctioneer_id: {len(props2.data)}')

props3 = supabase.table('properties').select('id, title').eq('auctioneer_id', 'portalzuk').execute()
print(f'Imoveis com auctioneer_id=portalzuk: {len(props3.data)}')

print()
print('=== TOP 10 LEILOEIROS POR QUANTIDADE ===')
auctioneers = supabase.table('auctioneers').select('id, name, property_count, scrape_status').order('property_count', desc=True).limit(10).execute()
for a in auctioneers.data:
    print(f"  {a.get('name')}: {a.get('property_count')} imoveis (status: {a.get('scrape_status')})")

print()
print('=== TOTAL DE IMOVEIS NO BANCO ===')
all_props = supabase.table('properties').select('id', count='exact').execute()
print(f'Total de imoveis: {all_props.count}')
