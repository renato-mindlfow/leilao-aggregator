#!/usr/bin/env python3
"""TESTE RAPIDO - Validar consolidacao sem inserir no banco"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
EXTRACTIONS_DIR = BASE_DIR / "logs" / "extracao_paths_descobertos"

def main():
    print("\n" + "="*70)
    print("TESTE RAPIDO - CONSOLIDACAO")
    print("="*70 + "\n")
    
    # Listar arquivos
    arquivos = sorted(EXTRACTIONS_DIR.glob("extracao_*.json"))
    
    if not arquivos:
        print("X Nenhum arquivo encontrado")
        return
    
    print(f"Encontrados {len(arquivos)} arquivo(s):\n")
    
    total_sites = 0
    total_sucessos = 0
    total_imoveis = 0
    total_urls = set()
    
    for arquivo in arquivos:
        with open(arquivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        sites = len(data.get('resultados', []))
        sucessos = data.get('sucessos', 0)
        imoveis = data.get('total_imoveis', 0)
        
        total_sites += sites
        total_sucessos += sucessos
        total_imoveis += imoveis
        
        print(f"  * {arquivo.name}")
        print(f"    Sites: {sites} | Sucessos: {sucessos} | Imoveis: {imoveis}")
        
        # Contar URLs únicas
        for resultado in data.get('resultados', []):
            if resultado.get('sucesso'):
                for url in resultado.get('imoveis', []):
                    total_urls.add(url)
        print()
    
    print("="*70)
    print("TOTAIS:")
    print(f"   Sites processados:  {total_sites}")
    print(f"   Sites com sucesso:  {total_sucessos}")
    print(f"   Imoveis extraidos:  {total_imoveis}")
    print(f"   URLs unicas:        {len(total_urls)}")
    print("="*70 + "\n")
    
    # Análise por site
    print("TOP 10 SITES POR IMOVEIS:\n")
    
    todos_sites = []
    for arquivo in arquivos:
        with open(arquivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for resultado in data.get('resultados', []):
            if resultado.get('sucesso'):
                todos_sites.append({
                    'nome': resultado.get('nome'),
                    'imoveis': resultado.get('total_imoveis', 0)
                })
    
    top_sites = sorted(todos_sites, key=lambda x: x['imoveis'], reverse=True)[:10]
    
    for i, site in enumerate(top_sites, 1):
        print(f"  {i:2}. {site['nome']:<30} {site['imoveis']:>5} imoveis")
    
    print("\n" + "="*70 + "\n")
    print("Teste completado!")
    print("   Execute: python scripts/consolidar_e_persistir_lote2.py")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
