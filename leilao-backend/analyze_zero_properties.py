#!/usr/bin/env python3
"""Analisa sites com 0 imóveis"""
import json

with open('success_scrapers.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

zero_properties = [s for s in data['data'] if s['property_count'] == 0]

print(f"\n{'='*80}")
print(f"SITES COM STATUS=SUCCESS MAS 0 IMÓVEIS: {len(zero_properties)}")
print(f"{'='*80}\n")

for i, site in enumerate(zero_properties, 1):
    print(f"{i:2d}. ID: {site['id']}")
    print(f"    Nome: {site['name']}")
    print(f"    URL: {site['website']}")
    print(f"    Last scrape: {site.get('last_scrape', 'N/A')}")
    print()

# Salvar lista para processamento
with open('sites_zero_properties.txt', 'w', encoding='utf-8') as f:
    for site in zero_properties:
        f.write(f"{site['id']}|{site['name']}|{site['website']}\n")

print(f"\n✅ Lista salva em sites_zero_properties.txt")
