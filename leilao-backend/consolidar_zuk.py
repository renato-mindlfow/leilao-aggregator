from dotenv import load_dotenv
import os
load_dotenv()

from supabase import create_client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

print('=== CONSOLIDANDO PORTAL ZUK ===')

# 1. Mover imoveis de portal_zuk para 1
props = supabase.table('properties').select('id').eq('auctioneer_id', 'portal_zuk').execute()
print(f'Imoveis com auctioneer_id=portal_zuk: {len(props.data)}')

if len(props.data) > 0:
    update = supabase.table('properties').update({'auctioneer_id': '1'}).eq('auctioneer_id', 'portal_zuk').execute()
    print(f'  -> Movidos {len(update.data)} imoveis para auctioneer_id=1')

# 2. Recalcular total
props_total = supabase.table('properties').select('id', count='exact').eq('auctioneer_id', '1').execute()
total = props_total.count

# 3. Atualizar contagem no leiloeiro
supabase.table('auctioneers').update({
    'property_count': total,
    'scrape_status': 'success'
}).eq('id', '1').execute()

print(f'TOTAL Portal Zuk: {total} imoveis')
print('=== CONCLUIDO ===')
