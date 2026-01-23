import os
import sys
from dotenv import load_dotenv
load_dotenv()

print("=== DIAGNOSTICO RAPIDO LEILOHUB ===")
print()

# 1. Verificar variaveis de ambiente
print("1. VARIAVEIS DE AMBIENTE:")
for var in ["DATABASE_URL", "SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY"]:
    val = os.getenv(var)
    if val:
        print(f"   OK: {var} = {val[:15]}...")
    else:
        print(f"   ERRO: {var} NAO CONFIGURADO!")

# 2. Verificar imports
print()
print("2. IMPORTS DA APLICACAO:")
try:
    from app.main import app
    print("   OK: app.main importado")
except Exception as e:
    print(f"   ERRO: {e}")

# 3. Verificar banco
print()
print("3. CONEXAO COM BANCO:")
try:
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    result = supabase.table("auctioneers").select("id, name, property_count").execute()
    print(f"   OK: {len(result.data)} leiloeiros no banco")
    
    # Verificar duplicados Mega
    mega = [r for r in result.data if "mega" in r.get("name", "").lower()]
    if len(mega) > 1:
        print(f"   ATENCAO: {len(mega)} entradas 'Mega' encontradas:")
        for m in mega:
            print(f"      - {m['id']}: {m['name']} ({m.get('property_count', 0)} imoveis)")
    
    # Verificar Portal Zuk
    zuk = [r for r in result.data if "zuk" in r.get("name", "").lower()]
    for z in zuk:
        print(f"   Portal Zuk: {z.get('property_count', 0)} imoveis")
        
except Exception as e:
    print(f"   ERRO: {e}")

print()
print("=== FIM DO DIAGNOSTICO ===")
