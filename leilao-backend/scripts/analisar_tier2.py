import json
import sys

# Ler arquivo JSON
with open('logs/extracao_fase2/tier2/tier2_resultados_20260120_165411.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 60)
print("TIER 2 - RESULTADOS FINAIS")
print("=" * 60)
print(f"Total de sites processados: {data['total_sites']}")
print(f"Sucessos: {data['sucesso']}")
print(f"Falhas: {data['falhas']}")
print(f"Total de imóveis: {data['total_imoveis']}")
print(f"Taxa de sucesso: {data['sucesso']/data['total_sites']*100:.1f}%")
print()

print("=" * 60)
print("SITES COM SUCESSO:")
print("=" * 60)
for r in data['resultados']:
    if r['sucesso']:
        print(f"✅ {r['site']}: {r['total_imoveis']} imóveis")
print()

print("=" * 60)
print(f"SITES PROMOVIDOS PARA TIER 3: {len(data['promocoes_tier3'])}")
print("=" * 60)
