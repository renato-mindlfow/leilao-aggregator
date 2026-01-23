from dotenv import load_dotenv
import os
load_dotenv()

from supabase import create_client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

print('=== DESCOBRINDO AUCTIONEER_IDS COM ZUK ===')

# Buscar imoveis com zuk no auctioneer_id
props = supabase.table('properties').select('auctioneer_id').ilike('auctioneer_id', '%zuk%').execute()

# Contar por auctioneer_id
from collections import Counter
ids = [p['auctioneer_id'] for p in props.data]
contagem = Counter(ids)

print(f'Total de imoveis com zuk: {len(props.data)}')
print('Distribuicao por auctioneer_id:')
for aid, count in contagem.most_common():
    print(f'  {aid}: {count} imoveis')

# Verificar se esses IDs existem na tabela auctioneers
print()
print('=== VERIFICANDO SE IDS EXISTEM NA TABELA AUCTIONEERS ===')
for aid in contagem.keys():
    auc = supabase.table('auctioneers').select('id, name').eq('id', aid).execute()
    if auc.data:
        print(f'  {aid}: EXISTE -> {auc.data[0]["name"]}')
    else:
        print(f'  {aid}: NAO EXISTE (orfao)')
