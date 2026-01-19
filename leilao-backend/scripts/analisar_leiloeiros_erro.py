"""
Analisa leiloeiros com erro e categoriza por tipo de problema
"""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 70)
print("ANALISE DE LEILOEIROS COM ERRO")
print("=" * 70)

# Buscar leiloeiros com erro
result = supabase.table("auctioneers").select("*").eq("scrape_status", "error").execute()
leiloeiros = result.data

print(f"\nTotal com erro: {len(leiloeiros)}")

# Categorizar por tipo de erro
categorias = {
    "nenhum_imovel": [],      # "Nenhum imóvel encontrado"
    "timeout": [],             # Timeout
    "cloudflare": [],          # Cloudflare/bloqueio
    "404": [],                 # Site não existe
    "duplicate_key": [],       # Erro de duplicata
    "connection": [],          # Erro de conexão
    "parsing": [],             # Erro de parsing
    "outros": []               # Outros erros
}

for l in leiloeiros:
    erro = (l.get("scrape_error") or "").lower()
    nome = l.get("name", "N/A")
    website = l.get("website", "N/A")
    
    erro_completo = l.get("scrape_error") or ""
    item = {"nome": nome, "website": website, "erro": erro_completo[:100]}
    
    if "nenhum" in erro or "no properties" in erro or "0 imóveis" in erro or "0 imoveis" in erro:
        categorias["nenhum_imovel"].append(item)
    elif "timeout" in erro or "timed out" in erro:
        categorias["timeout"].append(item)
    elif "cloudflare" in erro or "403" in erro or "bloqueado" in erro:
        categorias["cloudflare"].append(item)
    elif "404" in erro or "not found" in erro or "não existe" in erro or "nao existe" in erro:
        categorias["404"].append(item)
    elif "duplicate" in erro:
        categorias["duplicate_key"].append(item)
    elif "connection" in erro or "connect" in erro:
        categorias["connection"].append(item)
    elif "parsing" in erro or "parse" in erro or "extract" in erro:
        categorias["parsing"].append(item)
    else:
        categorias["outros"].append(item)

# Mostrar resumo
print("\n" + "=" * 70)
print("CATEGORIAS DE ERROS")
print("=" * 70)

for cat, items in categorias.items():
    print(f"\n[{cat.upper()}] - {len(items)} leiloeiros")
    for item in items[:5]:  # Mostrar até 5 exemplos
        print(f"  - {item['nome']}")
        print(f"    {item['website']}")
        print(f"    Erro: {item['erro'][:60]}...")

# Identificar candidatos para correção
print("\n" + "=" * 70)
print("CANDIDATOS PARA CORRECAO")
print("=" * 70)

# Prioridade 1: "Nenhum imóvel" - pode ser paginação ou seletores
print(f"\n[PRIORIDADE 1] Nenhum imovel encontrado ({len(categorias['nenhum_imovel'])})")
print("Acao: Verificar se site tem imoveis e ajustar seletores")

# Prioridade 2: Timeout - pode precisar de Playwright
print(f"\n[PRIORIDADE 2] Timeout ({len(categorias['timeout'])})")
print("Acao: Usar Playwright ou aumentar timeout")

# Prioridade 3: Cloudflare - precisa ScrapingBee
print(f"\n[PRIORIDADE 3] Cloudflare/Bloqueio ({len(categorias['cloudflare'])})")
print("Acao: Usar ScrapingBee ou Playwright com stealth")

# Baixa prioridade: 404 - site não existe mais
print(f"\n[BAIXA PRIORIDADE] Site 404 ({len(categorias['404'])})")
print("Acao: Marcar como 'disabled' no banco")

# Salvar lista para processamento
print("\n" + "=" * 70)
print("EXPORTANDO LISTA PARA PROCESSAMENTO")
print("=" * 70)

import json
output_path = os.path.join(os.path.dirname(__file__), "leiloeiros_erro_categorizados.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(categorias, f, ensure_ascii=False, indent=2)
print(f"Salvo em: {output_path}")
