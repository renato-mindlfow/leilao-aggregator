#!/usr/bin/env python3
"""Encontra sites grandes nos pending"""
import json

with open('pending_full.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

pending = data.get('data', [])

# Sites grandes conhecidos
big_sites_keywords = [
    'zuk', 'superbid', 'vip', 'lance', 'mega', 'portal',
    'brasil', 'nacional', 'central', 'super', 'prime'
]

print(f"\nTotal pending: {len(pending)}")
print(f"\nProcurando sites grandes...")
print("="*80)

found = []
for site in pending:
    name = site.get('name', '').lower()
    site_id = site.get('id', '').lower()
    website = site.get('website', '').lower()
    
    for keyword in big_sites_keywords:
        if keyword in name or keyword in site_id or keyword in website:
            found.append(site)
            break

print(f"\nEncontrados {len(found)} sites potencialmente grandes:\n")
for i, site in enumerate(found[:30], 1):
    print(f"{i:2d}. {site['id']:<30} {site['name']}")
    print(f"    {site['website']}")
    print()

# Salvar IDs para processamento
ids = [s['id'] for s in found[:50]]
with open('big_sites_ids.txt', 'w') as f:
    f.write(','.join(ids))
    
print(f"IDs salvos em big_sites_ids.txt ({len(ids)} sites)")
