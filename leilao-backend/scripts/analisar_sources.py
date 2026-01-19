"""
Analisa distribuicao de sources e auctioneer_id nas properties
"""
import os
import sys
import io

# Encoding para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERRO: SUPABASE_URL ou SUPABASE_KEY nao configurados")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 60)
print("ANALISE DE SOURCES E AUCTIONEER_ID")
print("=" * 60)

# 1. Total de imoveis
print("\n[1] TOTAL DE IMOVEIS")
result = supabase.table("properties").select("id", count="exact").execute()
total = result.count
print(f"  Total: {total}")

# 2. Distribuicao por SOURCE
print("\n[2] DISTRIBUICAO POR SOURCE")
# Buscar em batches para não estourar limite
all_sources = {}
offset = 0
batch_size = 1000

while True:
    result = (
        supabase.table("properties")
        .select("source")
        .range(offset, offset + batch_size - 1)
        .execute()
    )
    if not result.data:
        break

    for p in result.data:
        src = p.get("source") or "NULL/VAZIO"
        all_sources[src] = all_sources.get(src, 0) + 1

    offset += batch_size
    if len(result.data) < batch_size:
        break

    # Limitar a 10 batches para teste
    if offset >= 10000:
        print(f"  (Amostra limitada a {offset} registros)")
        break

print(f"  Sources encontrados: {len(all_sources)}")
print("\n  Top 20 sources:")
for src, count in sorted(all_sources.items(), key=lambda x: -x[1])[:20]:
    pct = (count / sum(all_sources.values())) * 100
    print(f"    {src}: {count} ({pct:.1f}%)")

# 3. Distribuicao por AUCTIONEER_ID
print("\n[3] DISTRIBUICAO POR AUCTIONEER_ID")
all_auctioneers = {}
offset = 0

while True:
    result = (
        supabase.table("properties")
        .select("auctioneer_id")
        .range(offset, offset + batch_size - 1)
        .execute()
    )
    if not result.data:
        break

    for p in result.data:
        aid = p.get("auctioneer_id") or "NULL/VAZIO"
        all_auctioneers[aid] = all_auctioneers.get(aid, 0) + 1

    offset += batch_size
    if len(result.data) < batch_size:
        break

    if offset >= 10000:
        print(f"  (Amostra limitada a {offset} registros)")
        break

print(f"  Auctioneer IDs encontrados: {len(all_auctioneers)}")
print("\n  Top 20 auctioneer_id:")
for aid, count in sorted(all_auctioneers.items(), key=lambda x: -x[1])[:20]:
    pct = (count / sum(all_auctioneers.values())) * 100
    print(f"    {aid}: {count} ({pct:.1f}%)")

# 4. Verificar imoveis sem source E sem auctioneer_id
print("\n[4] IMOVEIS SEM IDENTIFICACAO")
result = (
    supabase.table("properties")
    .select("id,title,source_url")
    .is_("source", "null")
    .is_("auctioneer_id", "null")
    .limit(10)
    .execute()
)
print(f"  Imoveis sem source E sem auctioneer_id: {len(result.data)} (amostra)")
if result.data:
    print("\n  Exemplos:")
    for p in result.data[:5]:
        print(f"    - {p.get('title', 'N/A')[:50]}")
        print(f"      URL: {p.get('source_url', 'N/A')[:80]}")

print("\n" + "=" * 60)
print("FIM DA ANALISE")
print("=" * 60)
