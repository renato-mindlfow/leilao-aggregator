#!/usr/bin/env python3
"""Monitora progresso dos processos em background"""
import requests
import time
import json

API_BASE = "https://leilao-backend-solitary-haze-9882.fly.dev"

def get_stats():
    """Obtem estatisticas atuais"""
    try:
        # Status summary
        r1 = requests.get(f"{API_BASE}/api/diagnostics/scrapers/status-summary", timeout=15)
        status = r1.json() if r1.status_code == 200 else {}
        
        # Properties distribution
        r2 = requests.get(f"{API_BASE}/api/diagnostics/properties/distribution?limit=100", timeout=15)
        dist = r2.json() if r2.status_code == 200 else {}
        
        # Calculate totals
        success = next((d['total'] for d in status.get('data', []) if d['scrape_status'] == 'success'), 0)
        
        total_props = sum(d['total_imoveis'] for d in dist.get('data', []))
        caixa_props = next((d['total_imoveis'] for d in dist.get('data', []) if d['auctioneer_id'] == 'caixa_federal'), 0)
        other_props = total_props - caixa_props
        caixa_pct = (caixa_props / total_props * 100) if total_props > 0 else 0
        
        return {
            'success': success,
            'total_properties': total_props,
            'caixa_properties': caixa_props,
            'other_properties': other_props,
            'caixa_percentage': caixa_pct,
            'timestamp': time.strftime('%H:%M:%S')
        }
    except Exception as e:
        print(f"Erro ao obter stats: {e}")
        return None

print("="*80)
print("MONITORANDO PROGRESSO DOS PROCESSOS EM BACKGROUND")
print("="*80)
print("\nVerificando a cada 3 minutos por 15 minutos...\n")

initial = get_stats()
if initial:
    print(f"[{initial['timestamp']}] INICIAL:")
    print(f"  Scrapers: {initial['success']}")
    print(f"  Imoveis: {initial['total_properties']:,}")
    print(f"  Outros: {initial['other_properties']:,} ({100-initial['caixa_percentage']:.1f}%)")
    print(f"  Caixa: {initial['caixa_properties']:,} ({initial['caixa_percentage']:.1f}%)")

for i in range(5):  # 5 checks x 3 min = 15 min
    time.sleep(180)  # 3 minutos
    
    current = get_stats()
    if current:
        print(f"\n[{current['timestamp']}] Check {i+1}/5:")
        print(f"  Scrapers: {current['success']} ({current['success'] - initial['success']:+d})")
        print(f"  Imoveis: {current['total_properties']:,} ({current['total_properties'] - initial['total_properties']:+,})")
        print(f"  Outros: {current['other_properties']:,} ({current['other_properties'] - initial['other_properties']:+,})")
        print(f"  Caixa%: {current['caixa_percentage']:.1f}% ({current['caixa_percentage'] - initial['caixa_percentage']:+.1f}%)")
        
        # Check if goals reached
        if current['success'] >= 50 and current['total_properties'] >= 50000 and current['caixa_percentage'] < 80:
            print(f"\n{'='*80}")
            print("TODAS AS METAS ATINGIDAS!")
            print(f"{'='*80}")
            break

print(f"\n{'='*80}")
print("MONITORAMENTO CONCLUIDO")
print(f"{'='*80}\n")
