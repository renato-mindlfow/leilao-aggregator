#!/usr/bin/env python3
"""Re-executa sites com 0 imóveis"""
import requests
import time

API_BASE = "https://leilao-backend-solitary-haze-9882.fly.dev"

# IDs dos 19 sites com 0 imóveis
site_ids = [
    '116', '119', '147', '107', '108', '114', '152', '120', '128', '131',
    '137', '153', '106', '134', '104', '148', '145', '149', '111'
]

print("="*80)
print(f"RE-EXECUTANDO {len(site_ids)} SITES COM 0 IMÓVEIS")
print("="*80)

# 1. Resetar status para needs_playwright
print(f"\n[1] Resetando status dos sites...")
for site_id in site_ids:
    try:
        response = requests.post(
            f"{API_BASE}/api/diagnostics/scrapers/{site_id}/reset",
            params={'status': 'needs_playwright'},
            timeout=10
        )
        if response.status_code == 200:
            print(f"OK {site_id} resetado")
        else:
            print(f"WARN {site_id} - Status: {response.status_code}")
    except Exception as e:
        print(f"ERROR {site_id} - Erro: {e}")

print(f"\n[2] Aguardando 5 segundos...")
time.sleep(5)

# 2. Executar batch nos sites
print(f"\n[3] Executando Playwright Stealth nos 19 sites...")
try:
    response = requests.post(
        f"{API_BASE}/api/diagnostics/run-cloudflare-sites-full",
        params={'limit': 19},
        timeout=900  # 15 minutos
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nSUCESSO!")
        print(f"Sites processados: {result.get('summary', {}).get('total_sites_processed', 0)}")
        print(f"Sites com sucesso: {result.get('summary', {}).get('successful_sites', 0)}")
        print(f"Total de imoveis salvos: {result.get('summary', {}).get('total_properties_saved', 0)}")
    else:
        print(f"ERRO: Status {response.status_code}")
        print(response.text[:500])
        
except Exception as e:
    print(f"ERRO na execucao: {e}")

print(f"\n{'='*80}")
print("CONCLUÍDO!")
print(f"{'='*80}\n")
