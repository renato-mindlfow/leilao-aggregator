#!/usr/bin/env python3
"""
Simple status checker for the massive attack
Reads the terminal output and provides a summary
"""

import re
from pathlib import Path
import sys

def contar_sites_processados(log_content):
    """Count sites processed from log"""
    # Look for "Extraindo:" lines which indicate a new site
    extraindo_pattern = r"Extraindo: ([\w.-]+)"
    sites = re.findall(extraindo_pattern, log_content)
    return sites

def contar_sucessos(log_content):
    """Count successful extractions"""
    # Look for "TIER X SUCESSO:" lines
    sucesso_pattern = r"TIER \d+ SUCESSO: (\d+) imóveis"
    sucessos = re.findall(sucesso_pattern, log_content)
    return [int(s) for s in sucessos]

def analisar_erros(log_content):
    """Analyze errors"""
    bloqueios = len(re.findall(r"Bloqueio:", log_content))
    tier1_falhou = len(re.findall(r"TIER 1 falhou", log_content))
    tier2_falhou = len(re.findall(r"FALHOU em ambos tiers", log_content))
    return bloqueios, tier1_falhou, tier2_falhou

def main():
    # Find the most recent terminal file
    terminals_dir = Path(r"C:\Users\renat\.cursor\projects\c-LeiloHub\terminals")
    
    # Look for files that might contain our script output
    terminal_files = list(terminals_dir.glob("*.txt"))
    
    if not terminal_files:
        print("Nenhum arquivo de terminal encontrado")
        return
    
    # Read the most recent one
    terminal_file = max(terminal_files, key=lambda f: f.stat().st_mtime)
    
    print(f"\n{'='*70}")
    print(f"STATUS DO ATAQUE MASSIVO")
    print(f"{'='*70}\n")
    print(f"Lendo: {terminal_file.name}")
    print()
    
    with open(terminal_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Check if it's the right terminal
    if "ataque_massivo" not in content.lower() and "leiloeiros carregados" not in content:
        print("Este terminal nao parece conter o ataque massivo")
        print("Procurando por outro terminal...")
        
        for tf in sorted(terminal_files, key=lambda f: f.stat().st_mtime, reverse=True):
            with open(tf, 'r', encoding='utf-8', errors='ignore') as f:
                c = f.read()
            if "leiloeiros carregados" in c or "executar_ataque_massivo" in c:
                terminal_file = tf
                content = c
                print(f"Encontrado: {terminal_file.name}\n")
                break
        else:
            print("Nenhum terminal com ataque massivo encontrado")
            return
    
    # Analyze
    sites = contar_sites_processados(content)
    sucessos = contar_sucessos(content)
    bloqueios, tier1_falhou, tier2_falhou = analisar_erros(content)
    
    total_leiloeiros_match = re.search(r"(\d+) leiloeiros carregados", content)
    total_leiloeiros = int(total_leiloeiros_match.group(1)) if total_leiloeiros_match else 289
    
    # Get last site being processed
    ultimo_site = sites[-1] if sites else "Nenhum"
    
    print(f"PROGRESSO GERAL:")
    print(f"  Total de leiloeiros: {total_leiloeiros}")
    print(f"  Sites processados:   {len(sites)} ({len(sites)/total_leiloeiros*100:.1f}%)")
    print(f"  Ultimo site:         {ultimo_site}")
    print()
    
    print(f"RESULTADOS:")
    print(f"  Sucessos:            {len(sucessos)}")
    if sucessos:
        print(f"  Total de imoveis:    {sum(sucessos)}")
        print(f"  Media por sucesso:   {sum(sucessos)/len(sucessos):.1f}")
    print()
    
    print(f"ERROS:")
    print(f"  Bloqueios (CAPTCHA/CloudFlare): {bloqueios}")
    print(f"  Falhas TIER 1:                  {tier1_falhou}")
    print(f"  Falhas em ambos tiers:          {tier2_falhou}")
    print()
    
    # Estimate time remaining
    if len(sites) > 0:
        # Get timestamps of first and last
        timestamps = re.findall(r"2026-01-20 (\d+):(\d+):(\d+)", content)
        if len(timestamps) >= 2:
            first_h, first_m, first_s = map(int, timestamps[0])
            last_h, last_m, last_s = map(int, timestamps[-1])
            
            segundos_decorridos = (last_h * 3600 + last_m * 60 + last_s) - (first_h * 3600 + first_m * 60 + first_s)
            
            if len(sites) > 1:
                segundos_por_site = segundos_decorridos / len(sites)
                sites_restantes = total_leiloeiros - len(sites)
                segundos_restantes = segundos_por_site * sites_restantes
                
                horas_restantes = int(segundos_restantes // 3600)
                minutos_restantes = int((segundos_restantes % 3600) // 60)
                
                print(f"ESTIMATIVA:")
                print(f"  Tempo por site:      ~{segundos_por_site:.0f}s")
                print(f"  Sites restantes:     {sites_restantes}")
                print(f"  Tempo restante:      ~{horas_restantes}h {minutos_restantes}min")
    
    print(f"\n{'='*70}\n")
    
    # Show recent activity (last 5 sites)
    print("ULTIMOS SITES PROCESSADOS:")
    recent_sites = sites[-5:] if len(sites) > 5 else sites
    for i, site in enumerate(recent_sites, start=len(sites)-len(recent_sites)+1):
        print(f"  {i}. {site}")
    
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
