"""
Diagnostico de scrapers - versao sem emojis para Windows
"""
import io
import os
import sys

from dotenv import load_dotenv


# Forcar UTF-8 no console do Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Carregar .env
load_dotenv()

# Verificar variaveis
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

print("=" * 60)
print("DIAGNOSTICO DE SCRAPERS - LEILOHUB")
print("=" * 60)

# Verificar configuracao
print("\n[1] VERIFICANDO CONFIGURACAO")
print(f"  SUPABASE_URL: {'OK' if SUPABASE_URL else 'FALTANDO'}")
print(f"  SUPABASE_KEY: {'OK' if SUPABASE_KEY else 'FALTANDO'}")
print(f"  DATABASE_URL: {'OK' if DATABASE_URL else 'FALTANDO'}")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("\n[ERRO] Variaveis Supabase nao configuradas!")
    print("Adicione ao .env:")
    print("  SUPABASE_URL=https://xxx.supabase.co")
    print("  SUPABASE_KEY=eyJ...")
    sys.exit(1)

# Conectar ao Supabase
try:
    from supabase import create_client

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("  Conexao Supabase: OK")
except Exception as exc:
    print(f"  Conexao Supabase: ERRO - {exc}")
    sys.exit(1)

# Consultar auctioneers
print("\n[2] CONSULTANDO LEILOEIROS")
try:
    result = supabase.table("auctioneers").select("*").execute()
    auctioneers = result.data
    print(f"  Total de leiloeiros: {len(auctioneers)}")

    # Contar por status
    status_count = {}
    for a in auctioneers:
        status = a.get("scrape_status", "unknown")
        status_count[status] = status_count.get(status, 0) + 1

    print("\n  Status dos scrapers:")
    for status, count in sorted(status_count.items()):
        print(f"    {status}: {count}")

except Exception as exc:
    print(f"  ERRO ao consultar: {exc}")
    sys.exit(1)

# Consultar propriedades
print("\n[3] CONSULTANDO PROPRIEDADES")
try:
    # Total
    result = supabase.table("properties").select("id", count="exact").execute()
    total = result.count
    print(f"  Total de imoveis: {total}")

    # Por fonte
    result = supabase.table("properties").select("source").execute()
    sources = {}
    for p in result.data:
        src = p.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    print("\n  Imoveis por fonte:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1])[:10]:
        pct = (count / total * 100) if total > 0 else 0
        print(f"    {src}: {count} ({pct:.1f}%)")

except Exception as exc:
    print(f"  ERRO ao consultar: {exc}")

# Listar leiloeiros com erro
print("\n[4] LEILOEIROS COM ERRO")
try:
    result = (
        supabase.table("auctioneers")
        .select("name,website,scrape_status,scrape_error")
        .eq("scrape_status", "error")
        .limit(20)
        .execute()
    )

    if result.data:
        for a in result.data[:10]:
            print(f"  - {a.get('name', 'N/A')}")
            print(f"    Website: {a.get('website', 'N/A')}")
            print(f"    Erro: {a.get('scrape_error', 'N/A')[:100]}...")
            print()
    else:
        print("  Nenhum leiloeiro com erro encontrado")

except Exception as exc:
    print(f"  ERRO: {exc}")

# Listar leiloeiros pendentes
print("\n[5] LEILOEIROS PENDENTES (nunca executados)")
try:
    result = (
        supabase.table("auctioneers")
        .select("name,website")
        .eq("scrape_status", "pending")
        .limit(20)
        .execute()
    )

    if result.data:
        print(f"  Total pendentes: {len(result.data)} (mostrando 10)")
        for a in result.data[:10]:
            print(f"  - {a.get('name', 'N/A')}: {a.get('website', 'N/A')}")
    else:
        print("  Nenhum leiloeiro pendente")

except Exception as exc:
    print(f"  ERRO: {exc}")

print("\n" + "=" * 60)
print("FIM DO DIAGNOSTICO")
print("=" * 60)
