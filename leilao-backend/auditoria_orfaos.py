from dotenv import load_dotenv
import os
load_dotenv()

from supabase import create_client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

print('=== AUDITORIA DE IMOVEIS ORFAOS ===')

# Buscar todos os auctioneer_ids unicos das properties
# Limitacao: Supabase nao tem DISTINCT, vamos buscar em batches
props = supabase.table('properties').select('auctioneer_id').limit(1000).execute()

from collections import Counter
ids = [p['auctioneer_id'] for p in props.data]
contagem = Counter(ids)

print(f'Amostra: {len(props.data)} imoveis')
print(f'IDs unicos encontrados: {len(contagem)}')
print()

# Verificar quais IDs existem na tabela auctioneers
orfaos = []
existentes = []

for aid in contagem.keys():
    auc = supabase.table('auctioneers').select('id, name').eq('id', aid).execute()
    if auc.data:
        existentes.append((aid, contagem[aid], auc.data[0]['name']))
    else:
        orfaos.append((aid, contagem[aid]))

print('=== IDS ORFAOS (nao existem em auctioneers) ===')
if orfaos:
    for aid, count in sorted(orfaos, key=lambda x: -x[1]):
        print(f'  {aid}: {count} imoveis')
else:
    print('  Nenhum ID orfao encontrado!')

print()
print('=== RESUMO ===')
print(f'IDs existentes: {len(existentes)}')
print(f'IDs orfaos: {len(orfaos)}')
total_orfaos = sum(c for _, c in orfaos)
print(f'Total imoveis orfaos: {total_orfaos}')
