#!/usr/bin/env python3
"""Re-executa top sites COM PAGINACAO para multiplicar imoveis"""
import requests
import time
import json

API_BASE = "https://leilao-backend-solitary-haze-9882.fly.dev"

# Top sites (excluindo Caixa) que devem ter paginacao
top_sites = [
    'megaleiloes',  # 1.549 -> esperado 5k+
    '2',  # Megaleiloes: 481
    '166',  # Turanileiloes: 397
    '150',  # Trileiloes: 367
    '46',  # Lancejudicial: 307
    'realiza_leiloes',  # 123
    '32',  # Lut: 114
    'sodresantoro',  # 111
    'isaias_leiloes',  # 56
    'arg_leiloes',  # 54
    '39',  # Allianceleiloes: 54
]

print("="*80)
print(f"RE-EXECUTANDO TOP {len(top_sites)} SITES COM PAGINACAO")
print("="*80)

# Obter dados atuais
print(f"\n[1] Obtendo dados atuais dos sites...")
current_data = {}
for site_id in top_sites:
    try:
        response = requests.get(
            f"{API_BASE}/api/diagnostics/auctioneers/{site_id}",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json().get('data', {})
            current_data[site_id] = {
                'name': data.get('name', site_id),
                'current_properties': data.get('property_count', 0)
            }
            print(f"  {data.get('name', site_id)}: {data.get('property_count', 0)} imoveis")
    except Exception as e:
        print(f"  ERROR {site_id}: {e}")

print(f"\n[2] Resetando para needs_playwright...")
for site_id in top_sites:
    try:
        response = requests.post(
            f"{API_BASE}/api/diagnostics/scrapers/{site_id}/reset",
            params={'status': 'needs_playwright'},
            timeout=10
        )
        if response.status_code == 200:
            print(f"  OK {site_id}")
    except Exception as e:
        print(f"  ERROR {site_id}: {e}")

time.sleep(3)

print(f"\n[3] Executando com PAGINACAO (pode demorar 15-30min)...")
print("AGUARDE... Processando em background...")

# Executar em lote (iniciar e não esperar)
try:
    response = requests.post(
        f"{API_BASE}/api/diagnostics/run-cloudflare-sites-full",
        params={'limit': len(top_sites)},
        timeout=5  # Apenas iniciar, nao esperar
    )
except requests.exceptions.Timeout:
    print("Comando iniciado em background (timeout esperado)")
except Exception as e:
    print(f"Iniciado: {e}")

print(f"\n[4] Aguardando 5 minutos antes de verificar resultados...")
print("(sites grandes com paginacao demoram mais)")

for i in range(30):
    time.sleep(10)
    print(f"  {(i+1)*10}s / 300s...")

print(f"\n[5] Verificando resultados parciais...")
try:
    response = requests.get(
        f"{API_BASE}/api/diagnostics/properties/distribution",
        params={'limit': 15},
        timeout=15
    )
    if response.status_code == 200:
        data = response.json().get('data', [])
        print(f"\nTOP 15 APOS PAGINACAO:")
        for i, item in enumerate(data[:15], 1):
            site_id = item.get('auctioneer_id')
            name = item.get('leiloeiro', '')
            total = item.get('total_imoveis', 0)
            
            # Comparar com anterior
            old_total = 0
            if site_id in current_data:
                old_total = current_data[site_id].get('current_properties', 0)
            
            diff = total - old_total if old_total > 0 else 0
            symbol = f"+{diff}" if diff > 0 else ""
            
            print(f"  {i:2d}. {name[:30]:<30} {total:>6} {symbol}")
except Exception as e:
    print(f"Erro ao verificar: {e}")

print(f"\n{'='*80}")
print("PROCESSO INICIADO!")
print("Aguarde mais 10-15 min e verifique o status final")
print(f"{'='*80}\n")
