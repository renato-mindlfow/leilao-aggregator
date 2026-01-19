"""
Verifica duplicatas no banco de dados do LeiloHub
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
from collections import Counter

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 60)
print("VERIFICANDO DUPLICATAS NO BANCO")
print("=" * 60)

# 1. Verificar duplicatas por source_url
print("\n[1] Duplicatas por source_url:")
try:
    # Buscar todas as properties com source_url
    result = supabase.table("properties").select("id,source_url,source,title").execute()
    properties = result.data
    
    url_counter = Counter(p['source_url'] for p in properties if p.get('source_url'))
    duplicates = {url: count for url, count in url_counter.items() if count > 1}
    
    if duplicates:
        print(f"  ⚠️  {len(duplicates)} URLs duplicadas!")
        for url, count in list(duplicates.items())[:5]:
            print(f"    {url[:60]}: {count} vezes")
        if len(duplicates) > 5:
            print(f"    ... e mais {len(duplicates) - 5} URLs duplicadas")
    else:
        print("  ✓ Nenhuma URL duplicada encontrada")
except Exception as e:
    print(f"  ❌ Erro ao verificar duplicatas: {e}")

# 2. Verificar sobreposição Zukerman/PortalZuk
print("\n[2] Imoveis Zukerman vs Portal Zuk:")
try:
    zuk = supabase.table("properties").select("id,source_url,title").eq("source", "zukerman").execute()
    pzuk = supabase.table("properties").select("id,source_url,title").eq("source", "portal_zuk").execute()
    
    zuk_urls = {p['source_url']: p for p in zuk.data if p.get('source_url')}
    pzuk_urls = {p['source_url']: p for p in pzuk.data if p.get('source_url')}
    
    print(f"  Zukerman: {len(zuk_urls)} imoveis")
    print(f"  Portal Zuk: {len(pzuk_urls)} imoveis")
    
    overlap = set(zuk_urls.keys()) & set(pzuk_urls.keys())
    print(f"  Sobreposicao: {len(overlap)} URLs em comum")
    
    if overlap:
        print("\n  Exemplos de URLs duplicadas:")
        for url in list(overlap)[:3]:
            print(f"    {url[:70]}")
            print(f"      Zukerman ID: {zuk_urls[url]['id']}")
            print(f"      Portal Zuk ID: {pzuk_urls[url]['id']}")
    
    # 3. Amostra de URLs para comparar domínios
    print("\n[3] Dominios das URLs:")
    if zuk_urls:
        print("  Zukerman (amostra):")
        for url in list(zuk_urls.keys())[:3]:
            print(f"    {url[:70]}")
    else:
        print("  Zukerman: nenhum imovel")
    
    if pzuk_urls:
        print("  Portal Zuk (amostra):")
        for url in list(pzuk_urls.keys())[:3]:
            print(f"    {url[:70]}")
    else:
        print("  Portal Zuk: nenhum imovel")
        
except Exception as e:
    print(f"  ❌ Erro ao verificar Zukerman/Portal Zuk: {e}")

# 4. Estatisticas por source
print("\n[4] Estatisticas por source (scrapers ativos):")
try:
    sources = [
        "megaleiloes", "portal_zuk", "zukerman", "sodresantoro",
        "superbid", "pestana_leiloes", "lancejudicial", "flexleiloes", "sold"
    ]
    
    for source in sources:
        result = supabase.table("properties").select("id", count="exact").eq("source", source).execute()
        count = result.count if hasattr(result, 'count') else len(result.data)
        print(f"  {source}: {count} imoveis")
        
except Exception as e:
    print(f"  ❌ Erro ao verificar estatisticas: {e}")

# 5. Verificar duplicatas por title + city + state
print("\n[5] Duplicatas por title + city + state:")
try:
    result = supabase.table("properties").select("title,city,state").execute()
    properties = result.data
    
    key_counter = Counter(
        (p.get('title', ''), p.get('city', ''), p.get('state', ''))
        for p in properties
        if p.get('title') and p.get('city') and p.get('state')
    )
    
    duplicates = {key: count for key, count in key_counter.items() if count > 1}
    
    if duplicates:
        print(f"  ⚠️  {len(duplicates)} combinacoes duplicadas!")
        for key, count in list(duplicates.items())[:5]:
            title, city, state = key
            print(f"    {title[:40]} | {city}, {state}: {count} vezes")
        if len(duplicates) > 5:
            print(f"    ... e mais {len(duplicates) - 5} combinacoes duplicadas")
    else:
        print("  ✓ Nenhuma combinacao duplicada encontrada")
        
except Exception as e:
    print(f"  ❌ Erro ao verificar duplicatas por combinacao: {e}")

print("\n" + "=" * 60)
print("FIM DA VERIFICACAO")
print("=" * 60)
