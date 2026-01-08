#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validação de Qualidade dos Dados
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def main():
    print("\n" + "="*70)
    print("VALIDAÇÃO DE QUALIDADE DOS DADOS")
    print("="*70)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
    
    # Total de imóveis ativos
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).execute()
    total = result.count or 0
    
    if total == 0:
        print("⚠️ Nenhum imóvel ativo encontrado")
        return
    
    print(f"📊 Total de imóveis ativos: {total:,}\n")
    
    metrics = {}
    
    # 1. Imóveis com preço
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).not_.is_("first_auction_value", "null").execute()
    com_preco = result.count or 0
    pct_preco = (com_preco * 100) / total if total > 0 else 0
    metrics['com_preco'] = {'count': com_preco, 'pct': pct_preco}
    
    # 2. Imóveis com imagem
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).not_.is_("image_url", "null").neq("image_url", "").execute()
    com_imagem = result.count or 0
    pct_imagem = (com_imagem * 100) / total if total > 0 else 0
    metrics['com_imagem'] = {'count': com_imagem, 'pct': pct_imagem}
    
    # 3. Imóveis com coordenadas
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).not_.is_("latitude", "null").execute()
    com_coords = result.count or 0
    pct_coords = (com_coords * 100) / total if total > 0 else 0
    metrics['com_coordenadas'] = {'count': com_coords, 'pct': pct_coords}
    
    # 4. Imóveis com cidade
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).not_.is_("city", "null").neq("city", "").execute()
    com_cidade = result.count or 0
    pct_cidade = (com_cidade * 100) / total if total > 0 else 0
    metrics['com_cidade'] = {'count': com_cidade, 'pct': pct_cidade}
    
    # 5. Imóveis com estado
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).not_.is_("state", "null").neq("state", "").execute()
    com_estado = result.count or 0
    pct_estado = (com_estado * 100) / total if total > 0 else 0
    metrics['com_estado'] = {'count': com_estado, 'pct': pct_estado}
    
    # 6. Imóveis com descrição
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).not_.is_("description", "null").neq("description", "").execute()
    com_desc = result.count or 0
    pct_desc = (com_desc * 100) / total if total > 0 else 0
    metrics['com_descricao'] = {'count': com_desc, 'pct': pct_desc}
    
    # Exibir resultados
    print("📈 MÉTRICAS DE QUALIDADE:\n")
    print("-" * 70)
    print(f"{'Métrica':<30} {'Quantidade':<15} {'Percentual':<15}")
    print("-" * 70)
    
    for key, value in metrics.items():
        label = key.replace('_', ' ').title()
        count = value['count']
        pct = value['pct']
        icon = "✅" if pct >= 80 else "⚠️" if pct >= 50 else "❌"
        print(f"{icon} {label:<27} {count:<15,} {pct:<14.1f}%")
    
    print("-" * 70)
    
    # Calcular score geral
    scores = [v['pct'] for v in metrics.values()]
    score_geral = sum(scores) / len(scores) if scores else 0
    
    print(f"\n🎯 SCORE GERAL DE QUALIDADE: {score_geral:.1f}%")
    
    if score_geral >= 80:
        print("✅ Qualidade EXCELENTE")
    elif score_geral >= 60:
        print("⚠️ Qualidade BOA - há espaço para melhoria")
    elif score_geral >= 40:
        print("⚠️ Qualidade REGULAR - atenção necessária")
    else:
        print("❌ Qualidade BAIXA - ação corretiva urgente")
    
    # Identificar problemas
    problemas = []
    if pct_cidade < 90:
        problemas.append(f"Apenas {pct_cidade:.1f}% têm cidade")
    if pct_preco < 50:
        problemas.append(f"Apenas {pct_preco:.1f}% têm preço")
    if pct_imagem < 50:
        problemas.append(f"Apenas {pct_imagem:.1f}% têm imagem")
    if pct_coords < 30:
        problemas.append(f"Apenas {pct_coords:.1f}% têm coordenadas")
    
    if problemas:
        print(f"\n⚠️ ÁREAS QUE PRECISAM DE ATENÇÃO:")
        for prob in problemas:
            print(f"   - {prob}")
    
    return metrics

if __name__ == "__main__":
    main()

