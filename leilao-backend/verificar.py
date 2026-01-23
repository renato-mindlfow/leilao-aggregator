from dotenv import load_dotenv
import os
load_dotenv()

from supabase import create_client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

print('=== VERIFICANDO MEGA LEILOES ===')
mega = supabase.table('auctioneers').select('id, name, property_count').ilike('name', '%mega%').execute()
print(f'Entradas encontradas: {len(mega.data)}')
for m in mega.data:
    print(f"  - ID: {m['id']}, Nome: {m['name']}, Imoveis: {m.get('property_count', 0)}")

print()
print('=== VERIFICANDO PORTAL ZUK ===')
zuk = supabase.table('auctioneers').select('id, name, property_count, scrape_status').ilike('name', '%zuk%').execute()
for z in zuk.data:
    print(f"  - ID: {z['id']}, Nome: {z['name']}, Imoveis: {z.get('property_count', 0)}, Status: {z.get('scrape_status', 'N/A')}")
