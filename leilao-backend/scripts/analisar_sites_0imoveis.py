#!/usr/bin/env python3
"""Análise dos sites com 0 imóveis no TIER 2"""
import json
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Ler resultados do TIER 2
with open('logs/extracao_fase2/tier2/tier2_resultados_20260120_165411.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Filtrar sites com 0 imóveis e sem CloudFlare
sites_0_imoveis = []

for resultado in data['resultados']:
    if resultado['total_imoveis'] == 0 and resultado.get('sucesso') == False:
        sites_0_imoveis.append(resultado)

for falha in data.get('falhas_detalhes', []):
    if falha.get('total_imoveis', 0) == 0 and 'CLOUDFLARE' not in str(falha.get('erro', '')):
        sites_0_imoveis.append(falha)

print("=" * 80)
print(f"SITES COM 0 IMÓVEIS NO TIER 2 (sem CloudFlare)")
print("=" * 80)
print(f"Total: {len(sites_0_imoveis)} sites\n")

for i, site in enumerate(sites_0_imoveis, 1):
    dominio = site.get('dominio', 'N/A')
    url = site.get('url_base', 'N/A')
    erro = site.get('erro') or site.get('bloqueio_detectado') or 'Nenhum imóvel encontrado'
    
    print(f"{i}. {dominio}")
    print(f"   URL: {url}")
    print(f"   Status: {erro}")
    print()

# Salvar lista em JSON
output = {
    "total": len(sites_0_imoveis),
    "sites": [
        {
            "dominio": s.get('dominio'),
            "url_base": s.get('url_base'),
            "url_testada": s.get('url_base', '') + '/imoveis',
            "erro": s.get('erro') or s.get('bloqueio_detectado')
        }
        for s in sites_0_imoveis
    ]
}

with open('logs/extracao_fase2/tier2/sites_0_imoveis.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"📁 Lista salva em: logs/extracao_fase2/tier2/sites_0_imoveis.json")
