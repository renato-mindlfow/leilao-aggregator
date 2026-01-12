"""Testar senha correta do Supabase"""
from dotenv import load_dotenv
import os
import psycopg
from psycopg.rows import dict_row

# URL correta do pooler (porta 6543) conforme instruções do usuário
url_correta = 'postgresql://postgres.nawbptwbmdgrkbpbwxzl:LeiloHub2025Pass@aws-1-sa-east-1.pooler.supabase.com:6543/postgres'

# Também testar URL direta (porta 5432) como alternativa
url_direta = 'postgresql://postgres:LeiloHub2025Pass@db.nawbptwbmdgrkbpbwxzl.supabase.co:5432/postgres'

senhas_teste = [
    ('Pooler (6543) - URL correta', url_correta),
    ('Direta (5432)', url_direta),
]

print("=" * 60)
print("TESTANDO SENHAS DO SUPABASE")
print("=" * 60)

senha_correta = None

for nome_teste, url in senhas_teste:
    print(f"\n[TESTE] {nome_teste}")
    print(f"  URL: {url[:90]}...")
    
    try:
        conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=15)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) as count FROM properties')
        result = cur.fetchone()
        count = result['count']
        print(f"  [OK] SENHA CORRETA! Total de imoveis: {count}")
        
        # Testar se a tabela auctioneers existe
        cur.execute("SELECT COUNT(*) as count FROM auctioneers")
        auctioneers_count = cur.fetchone()['count']
        print(f"  [OK] Total de leiloeiros: {auctioneers_count}")
        
        # Verificar se leiloeiro Caixa existe
        cur.execute("SELECT * FROM auctioneers WHERE id = 'caixa_federal'")
        caixa = cur.fetchone()
        if caixa:
            print(f"  [OK] Leiloeiro Caixa encontrado: {caixa.get('name')}")
        else:
            print(f"  [AVISO] Leiloeiro Caixa NAO encontrado (sera criado no sync)")
        
        conn.close()
        senha_correta = url
        print(f"\n[SUCESSO] Use esta URL: {url}")
        break
    except psycopg.OperationalError as e:
        erro_str = str(e)
        if 'password authentication failed' in erro_str:
            print(f"  [ERRO] Senha incorreta")
        elif 'timeout' in erro_str.lower():
            print(f"  [ERRO] Timeout - host pode estar bloqueado ou senha incorreta")
        else:
            print(f"  [ERRO] {erro_str[:150]}")
    except Exception as e:
        print(f"  [ERRO] {str(e)[:150]}")

print("\n" + "=" * 60)
if senha_correta:
    print(f"[RESULTADO] URL correta encontrada!")
    print(f"[ACAO] Esta URL ja esta no .env - prosseguir com sync")
else:
    print("[RESULTADO] Nenhuma das URLs testadas funcionou")
    print("[ACAO] Verificar/resetar senha no Supabase Dashboard")
print("=" * 60)

