"""
Script para atualizar status dos 11 sites - Quick Wins
PARTE 3.3 - FASE 1
"""

import json

# Carregar resultados da verificação
with open('verificacao_completa_20260122_101237.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Extrair IDs para cada categoria
offline_ids = [s['id'] for s in data['offline']]
no_properties_ids = [s['id'] for s in data['online_no_properties']]
redirected_data = [{'id': s['id'], 'old_url': s['website'], 'new_url': s['final_url']} 
                   for s in data['redirected']]

print("="*70)
print("QUICK WINS - ATUALIZAR STATUS")
print("="*70)

print(f"\n1. OFFLINE ({len(offline_ids)} sites):")
for site in data['offline']:
    print(f"   ID {site['id']}: {site['name']} - {site['error_message']}")
print(f"   IDs: {offline_ids}")

print(f"\n2. SEM IMOVEIS ({len(no_properties_ids)} sites):")
for site in data['online_no_properties']:
    print(f"   ID {site['id']}: {site['name']}")
print(f"   IDs: {no_properties_ids}")

print(f"\n3. REDIRECIONADOS ({len(redirected_data)} sites):")
for r in redirected_data:
    print(f"   ID {r['id']}: {r['old_url']} -> {r['new_url']}")

# Gerar SQL statements
print("\n" + "="*70)
print("SQL STATEMENTS")
print("="*70)

print("\n-- Marcar offline como disabled")
for aid in offline_ids:
    print(f"UPDATE auctioneers SET scrape_status = 'disabled', scrape_error = 'Site offline ou inacessível' WHERE id = '{aid}';")

print("\n-- Marcar sites sem imóveis")
for aid in no_properties_ids:
    print(f"UPDATE auctioneers SET scrape_status = 'no_properties', scrape_error = 'Site online mas sem imóveis disponíveis' WHERE id = '{aid}';")

print("\n-- Atualizar URLs redirecionadas")
for r in redirected_data:
    print(f"UPDATE auctioneers SET website = '{r['new_url']}', scrape_status = 'pending', scrape_error = NULL WHERE id = '{r['id']}';")

print("\n" + "="*70)
