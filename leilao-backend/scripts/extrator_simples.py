#!/usr/bin/env python3
"""Extrator simples usando paths descobertos"""
import json
from pathlib import Path

print("\n" + "="*70)
print("EXTRATOR SIMPLES - PATHS DESCOBERTOS")
print("="*70 + "\n")

# Carregar checkpoint
checkpoint = Path(__file__).parent.parent / "logs" / "descoberta_paths" / "checkpoint_10.json"

if not checkpoint.exists():
    print(f"❌ Checkpoint não encontrado: {checkpoint}")
    exit(1)

print(f"📋 Carregando: {checkpoint.name}")

with open(checkpoint, 'r', encoding='utf-8') as f:
    data = json.load(f)

sites_sucesso = [r for r in data['resultados'] if r['sucesso']]

print(f"✅ {len(sites_sucesso)} sites com paths descobertos:\n")

for i, site in enumerate(sites_sucesso, 1):
    print(f"{i}. {site['nome']}")
    print(f"   URL: {site['url_completa_descoberta']}")
    print(f"   Path: {site['path_descoberto']}")
    print(f"   Links: {site['links_encontrados']}")
    print()

print("="*70)
print(f"Total: {len(sites_sucesso)} sites prontos para extração")
print("="*70 + "\n")
