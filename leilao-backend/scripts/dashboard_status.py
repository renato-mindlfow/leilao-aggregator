#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard de Status - Status dos Leiloeiros no Banco
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
    print("DASHBOARD DE STATUS - LEILOEIROS")
    print("="*70)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
    
    # Buscar todos os leiloeiros
    result = supabase.table("auctioneers").select("*").order("property_count", desc=True).execute()
    
    if not result.data:
        print("⚠️ Nenhum leiloeiro encontrado no banco")
        return
    
    print(f"Total de leiloeiros: {len(result.data)}\n")
    print("-" * 70)
    print(f"{'ID':<20} {'Status':<12} {'Imóveis':<10} {'Último Scrape':<20}")
    print("-" * 70)
    
    now = datetime.now()
    
    for auc in result.data:
        auc_id = auc.get("id", "N/A")
        status = auc.get("scrape_status", "pending")
        count = auc.get("property_count", 0)
        last_scrape = auc.get("last_scrape", "")
        
        # Calcular tempo desde último scrape
        time_since = ""
        if last_scrape:
            try:
                last_dt = datetime.fromisoformat(last_scrape.replace("Z", "+00:00").replace("+00:00", ""))
                delta = now - last_dt
                if delta.days > 0:
                    time_since = f"{delta.days}d atrás"
                elif delta.seconds > 3600:
                    time_since = f"{delta.seconds // 3600}h atrás"
                elif delta.seconds > 60:
                    time_since = f"{delta.seconds // 60}m atrás"
                else:
                    time_since = "agora"
            except:
                time_since = "N/A"
        
        status_icon = "✅" if status == "success" else "❌" if status == "error" else "⏳"
        
        print(f"{auc_id:<20} {status_icon} {status:<10} {count:<10} {time_since:<20}")
    
    print("-" * 70)
    
    # Estatísticas resumidas
    total_imoveis = sum(auc.get("property_count", 0) for auc in result.data)
    sucesso = sum(1 for auc in result.data if auc.get("scrape_status") == "success")
    erro = sum(1 for auc in result.data if auc.get("scrape_status") == "error")
    pendente = sum(1 for auc in result.data if auc.get("scrape_status") == "pending" or not auc.get("scrape_status"))
    
    print(f"\n📊 RESUMO:")
    print(f"   Total de imóveis: {total_imoveis:,}")
    print(f"   Scrapers com sucesso: {sucesso}")
    print(f"   Scrapers com erro: {erro}")
    print(f"   Scrapers pendentes: {pendente}")

if __name__ == "__main__":
    main()

