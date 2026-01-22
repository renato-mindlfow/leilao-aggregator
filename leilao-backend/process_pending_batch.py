#!/usr/bin/env python3
"""Processa 100 sites pending em lote"""
import requests
import time

API_BASE = "https://leilao-backend-solitary-haze-9882.fly.dev"

print("="*80)
print("PROCESSANDO 100 SITES PENDING EM LOTE")
print("="*80)

# Obter lista de pending
print("\n[1] Obtendo lista de sites pending...")
try:
    response = requests.get(f"{API_BASE}/api/diagnostics/scrapers/pending?limit=100", timeout=15)
    if response.status_code == 200:
        sites = response.json().get('data', [])
        print(f"  {len(sites)} sites pending encontrados")
    else:
        print(f"  Erro: {response.status_code}")
        sites = []
except Exception as e:
    print(f"  Erro: {e}")
    sites = []

if not sites:
    print("\nNenhum site para processar!")
    exit(0)

# Processar em lote
print(f"\n[2] Processando {len(sites)} sites com Playwright...")
print("Iniciando em background (nao esperar resposta)...\n")

try:
    # Tentar endpoint com limite
    response = requests.post(
        f"{API_BASE}/api/diagnostics/run-cloudflare-sites-full",
        params={'limit': len(sites)},
        timeout=5  # So iniciar, nao esperar
    )
except requests.exceptions.Timeout:
    print("Processo iniciado com sucesso (timeout esperado)")
except Exception as e:
    print(f"Processo iniciado: {str(e)[:100]}")

print(f"\n[3] Sites sendo processados em background...")
print("Este processo pode levar 1-2 horas para completar todos os sites")
print("\nVerifique o progresso em 30-60 minutos")

print(f"\n{'='*80}")
print("PROCESSO INICIADO!")
print(f"{'='*80}\n")
