#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificação de Alertas - Identifica problemas críticos no sistema
"""

import os
import sys
from datetime import datetime, timedelta
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
    print("VERIFICAÇÃO DE ALERTAS")
    print("="*70)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
    
    alerts = []
    warnings = []
    
    # 1. Verificar scrapers com erro
    result = supabase.table("auctioneers").select("*").eq("scrape_status", "error").execute()
    if result.data:
        for auc in result.data:
            alerts.append({
                "tipo": "ERRO",
                "scraper": auc.get("id"),
                "mensagem": f"Scraper {auc.get('id')} falhou no último scrape"
            })
    
    # 2. Verificar scrapers sem execução recente (> 48h)
    now = datetime.now()
    result = supabase.table("auctioneers").select("*").neq("scrape_status", "pending").execute()
    
    for auc in result.data:
        last_scrape = auc.get("last_scrape")
        if last_scrape:
            try:
                last_dt = datetime.fromisoformat(last_scrape.replace("Z", "+00:00").replace("+00:00", ""))
                delta = now - last_dt
                if delta.days > 2:
                    warnings.append({
                        "tipo": "AVISO",
                        "scraper": auc.get("id"),
                        "mensagem": f"Scraper {auc.get('id')} não executou há {delta.days} dias"
                    })
            except:
                pass
    
    # 3. Verificar imóveis sem dados críticos
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).or_("city.is.null,city.eq.").execute()
    sem_cidade = result.count or 0
    if sem_cidade > 100:
        warnings.append({
            "tipo": "QUALIDADE",
            "mensagem": f"{sem_cidade} imóveis ativos sem cidade"
        })
    
    # 4. Verificar se há imóveis novos nas últimas 24h
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    result = supabase.table("properties").select("id", count="exact").gte("created_at", yesterday).execute()
    novos_24h = result.count or 0
    if novos_24h == 0:
        warnings.append({
            "tipo": "ATENÇÃO",
            "mensagem": "Nenhum imóvel novo nas últimas 24h - verificar pipeline"
        })
    
    # 5. Verificar taxa de dados completos
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).execute()
    total = result.count or 0
    
    if total > 0:
        result = supabase.table("properties").select("id", count="exact").eq("is_active", True).not_.is_("first_auction_value", "null").execute()
        com_preco = result.count or 0
        taxa_preco = com_preco * 100 // total
        
        if taxa_preco < 50:
            warnings.append({
                "tipo": "QUALIDADE",
                "mensagem": f"Apenas {taxa_preco}% dos imóveis têm preço"
            })
    
    # Exibir alertas
    if alerts:
        print("🚨 ALERTAS CRÍTICOS:")
        for alert in alerts:
            print(f"   [{alert['tipo']}] {alert['mensagem']}")
        print()
    
    if warnings:
        print("⚠️ AVISOS:")
        for warning in warnings:
            print(f"   [{warning['tipo']}] {warning['mensagem']}")
        print()
    
    if not alerts and not warnings:
        print("✅ NENHUM ALERTA ENCONTRADO - Sistema funcionando normalmente")
        print()
    
    # Retornar resumo
    return {
        "alerts": len(alerts),
        "warnings": len(warnings),
        "details": alerts + warnings
    }

if __name__ == "__main__":
    main()

