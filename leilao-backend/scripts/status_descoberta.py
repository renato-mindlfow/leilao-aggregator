#!/usr/bin/env python3
"""Monitor status of path discovery"""
import re
from pathlib import Path

def main():
    terminal_file = Path(r"C:\Users\renat\.cursor\projects\c-LeiloHub\terminals\951326.txt")
    
    if not terminal_file.exists():
        print("Terminal file not found")
        return
    
    with open(terminal_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Count discoveries
    paths_encontrados = len(re.findall(r"Path encontrado:", content))
    nenhum_path = len(re.findall(r"Nenhum path descoberto", content))
    total_processados = paths_encontrados + nenhum_path
    
    print(f"\n{'='*60}")
    print(f"STATUS DA DESCOBERTA DE PATHS")
    print(f"{'='*60}\n")
    print(f"Sites processados: {total_processados} / 261 ({total_processados/261*100:.1f}%)")
    print(f"Paths descobertos: {paths_encontrados} ({paths_encontrados/total_processados*100:.1f}%)")
    print(f"Sem path:          {nenhum_path} ({nenhum_path/total_processados*100:.1f}%)")
    
    # Show recent discoveries
    print(f"\n{'='*60}")
    print("ULTIMAS DESCOBERTAS:")
    print(f"{'='*60}\n")
    
    discoveries = re.findall(r"Path encontrado: ([^\s]+) \((\d+) links\)", content)
    for i, (path, links) in enumerate(discoveries[-5:], start=len(discoveries)-4):
        path_display = path if path else "/ (homepage)"
        print(f"  {i}. {path_display} - {links} links")
    
    print(f"\n{'='*60}\n")
    
    # Estimate time remaining
    if total_processados > 0:
        # Find timestamps
        timestamps = re.findall(r"2026-01-20 (\d+):(\d+):(\d+)", content)
        if len(timestamps) >= 2:
            first_h, first_m, first_s = map(int, timestamps[0])
            last_h, last_m, last_s = map(int, timestamps[-1])
            
            segundos = (last_h * 3600 + last_m * 60 + last_s) - (first_h * 3600 + first_m * 60 + first_s)
            
            if total_processados > 1:
                seg_por_site = segundos / total_processados
                sites_restantes = 261 - total_processados
                seg_restantes = seg_por_site * sites_restantes
                
                horas = int(seg_restantes // 3600)
                minutos = int((seg_restantes % 3600) // 60)
                
                print(f"ESTIMATIVA:")
                print(f"  Tempo por site:   ~{seg_por_site:.0f}s")
                print(f"  Tempo restante:   ~{horas}h {minutos}min")
                print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
