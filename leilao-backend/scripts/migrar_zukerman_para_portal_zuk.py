"""
Migra imóveis do source 'zukerman' para 'portal_zuk' e remove duplicatas
"""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 60)
print("MIGRACAO: ZUKERMAN -> PORTAL ZUK")
print("=" * 60)

# 1. Buscar todos os imóveis Zukerman
print("\n[1] Buscando imóveis Zukerman...")
zuk_result = supabase.table("properties").select("*").eq("source", "zukerman").execute()
zukerman_props = zuk_result.data
print(f"  Encontrados: {len(zukerman_props)} imóveis")

# 2. Buscar todos os imóveis Portal Zuk
print("\n[2] Buscando imóveis Portal Zuk...")
pzuk_result = supabase.table("properties").select("*").eq("source", "portal_zuk").execute()
portal_zuk_props = pzuk_result.data
print(f"  Encontrados: {len(portal_zuk_props)} imóveis")

# 3. Identificar duplicatas e não-duplicatas
portal_zuk_urls = {p['source_url']: p['id'] for p in portal_zuk_props if p.get('source_url')}
duplicates = []
unique_zukerman = []

for zuk_prop in zukerman_props:
    url = zuk_prop.get('source_url')
    if url and url in portal_zuk_urls:
        duplicates.append((zuk_prop['id'], portal_zuk_urls[url]))
    else:
        unique_zukerman.append(zuk_prop)

print(f"\n[3] Análise:")
print(f"  Duplicatas (Zukerman = Portal Zuk): {len(duplicates)}")
print(f"  Únicos Zukerman (não em Portal Zuk): {len(unique_zukerman)}")

# 4. Remover duplicatas Zukerman
if duplicates:
    print(f"\n[4] Removendo {len(duplicates)} duplicatas Zukerman...")
    removed_count = 0
    for zuk_id, pzuk_id in duplicates:
        try:
            supabase.table("properties").delete().eq("id", zuk_id).execute()
            removed_count += 1
        except Exception as e:
            print(f"  ❌ Erro ao remover {zuk_id}: {e}")
    print(f"  ✓ Removidos: {removed_count} imóveis duplicados")

# 5. Migrar únicos Zukerman para Portal Zuk
if unique_zukerman:
    print(f"\n[5] Migrando {len(unique_zukerman)} imóveis únicos Zukerman -> Portal Zuk...")
    migrated_count = 0
    for prop in unique_zukerman:
        try:
            # Atualizar source, auctioneer_id e auctioneer_name
            supabase.table("properties").update({
                "source": "portal_zuk",
                "auctioneer_id": "portal_zuk",
                "auctioneer_name": "Portal Zuk"
            }).eq("id", prop['id']).execute()
            migrated_count += 1
        except Exception as e:
            print(f"  ❌ Erro ao migrar {prop['id']}: {e}")
    print(f"  ✓ Migrados: {migrated_count} imóveis")

# 6. Verificar resultado
print("\n[6] Verificando resultado...")
final_zuk = supabase.table("properties").select("id", count="exact").eq("source", "zukerman").execute()
final_pzuk = supabase.table("properties").select("id", count="exact").eq("source", "portal_zuk").execute()

zuk_count = final_zuk.count if hasattr(final_zuk, 'count') else len(final_zuk.data)
pzuk_count = final_pzuk.count if hasattr(final_pzuk, 'count') else len(final_pzuk.data)

print(f"  Zukerman restantes: {zuk_count}")
print(f"  Portal Zuk atualizados: {pzuk_count}")

print("\n" + "=" * 60)
print("MIGRACAO CONCLUIDA")
print("=" * 60)
