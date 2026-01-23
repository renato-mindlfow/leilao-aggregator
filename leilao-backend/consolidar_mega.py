from dotenv import load_dotenv
import os
load_dotenv()

from supabase import create_client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

print('=== CONSOLIDANDO MEGA LEILOES ===')

# IDs duplicados a serem removidos
ids_duplicados = ['2', '289']
id_principal = 'megaleiloes'

# 1. Mover imoveis dos duplicados para o principal
for dup_id in ids_duplicados:
    props = supabase.table('properties').select('id').eq('auctioneer_id', dup_id).execute()
    print(f'ID {dup_id}: {len(props.data)} imoveis encontrados')
    
    if len(props.data) > 0:
        update = supabase.table('properties').update({'auctioneer_id': id_principal}).eq('auctioneer_id', dup_id).execute()
        print(f'  -> Movidos {len(update.data)} para {id_principal}')

# 2. Deletar leiloeiros duplicados
for dup_id in ids_duplicados:
    try:
        result = supabase.table('auctioneers').delete().eq('id', dup_id).execute()
        print(f'Leiloeiro ID={dup_id} deletado')
    except Exception as e:
        print(f'Erro ao deletar {dup_id}: {e}')

# 3. Recalcular total
props_total = supabase.table('properties').select('id').eq('auctioneer_id', id_principal).execute()
supabase.table('auctioneers').update({'property_count': len(props_total.data)}).eq('id', id_principal).execute()

print(f'TOTAL Mega Leiloes: {len(props_total.data)} imoveis')
print('=== CONCLUIDO ===')
