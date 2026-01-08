#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VERIFICAÇÃO MATINAL DO SISTEMA"""

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

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def main():
    print("\n" + "="*70)
    print(f"VERIFICAÇÃO MATINAL - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*70)
    
    issues = []
    stats = {}
    
    # 1. Total de imóveis
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).execute()
    total = result.count or 0
    stats['total_ativos'] = total
    print(f"\n📊 Total de imóveis ativos: {total:,}")
    
    # 2. Novos nas últimas 24h
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    result = supabase.table("properties").select("id", count="exact").gte("created_at", yesterday).execute()
    new_24h = result.count or 0
    stats['novos_24h'] = new_24h
    print(f"📊 Novos nas últimas 24h: {new_24h}")
    
    if new_24h == 0:
        issues.append("⚠️ ATENÇÃO: Nenhum imóvel novo nas últimas 24h")
    
    # 3. Status dos scrapers
    print("\n📋 STATUS DOS SCRAPERS:")
    
    scrapers = ["megaleiloes", "sodresantoro", "flexleiloes", "lancetotal", "lancenoleilao", "caixa"]
    
    for scraper in scrapers:
        result = supabase.table("auctioneers").select("*").eq("id", scraper).execute()
        
        if result.data:
            auc = result.data[0]
            status = auc.get("scrape_status", "pending")
            last_scrape = auc.get("last_scrape", "")
            count = auc.get("property_count", 0)
            
            status_icon = "✅" if status == "success" else "❌" if status == "error" else "⏳"
            
            # Verificar se scrape é recente (últimas 24h)
            is_recent = False
            if last_scrape:
                try:
                    last_dt = datetime.fromisoformat(last_scrape.replace("Z", "+00:00").replace("+00:00", ""))
                    is_recent = (datetime.now() - last_dt) < timedelta(hours=24)
                except:
                    try:
                        last_dt = datetime.fromisoformat(last_scrape)
                        is_recent = (datetime.now() - last_dt) < timedelta(hours=24)
                    except:
                        pass
            
            recent_icon = "🕐" if not is_recent else ""
            
            print(f"   {status_icon} {scraper}: {count} imóveis | {status} {recent_icon}")
            
            if status == "error":
                issues.append(f"❌ ERRO: {scraper} falhou no último scrape")
            
            if not is_recent and status != "pending":
                issues.append(f"⚠️ ATENÇÃO: {scraper} não executou nas últimas 24h")
        else:
            print(f"   ⏳ {scraper}: não configurado")
    
    # 4. Verificar Caixa (fonte principal)
    result = supabase.table("properties").select("id", count="exact").eq("auctioneer_id", "caixa").eq("is_active", True).execute()
    caixa_count = result.count or 0
    stats['caixa_count'] = caixa_count
    print(f"\n📊 Imóveis da Caixa: {caixa_count:,}")
    
    # 5. Qualidade
    print("\n📈 QUALIDADE:")
    
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).not_.is_("first_auction_value", "null").execute()
    with_price = result.count or 0
    pct_price = with_price * 100 // total if total else 0
    stats['com_preco'] = pct_price
    print(f"   Com preço: {pct_price}%")
    
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).not_.is_("image_url", "null").neq("image_url", "").execute()
    with_image = result.count or 0
    pct_image = with_image * 100 // total if total else 0
    stats['com_imagem'] = pct_image
    print(f"   Com imagem: {pct_image}%")
    
    result = supabase.table("properties").select("id", count="exact").eq("is_active", True).not_.is_("latitude", "null").execute()
    with_coords = result.count or 0
    pct_coords = with_coords * 100 // total if total else 0
    stats['com_coordenadas'] = pct_coords
    print(f"   Com coordenadas: {pct_coords}%")
    
    # 6. Resumo
    print("\n" + "="*70)
    print("RESUMO")
    print("="*70)
    
    if issues:
        print("\n⚠️ PROBLEMAS ENCONTRADOS:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ TUDO OK! Sistema funcionando normalmente.")
    
    # 7. Salvar
    filename = f"verificacao_matinal_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    filepath = Path(__file__).parent / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Verificação Matinal - {datetime.now()}\n")
        f.write(f"="*70 + "\n\n")
        f.write(f"Total Ativos: {total}\n")
        f.write(f"Novos 24h: {new_24h}\n")
        f.write(f"Caixa: {caixa_count}\n")
        f.write(f"Com Preço: {pct_price}%\n")
        f.write(f"Com Imagem: {pct_image}%\n")
        f.write(f"Com Coordenadas: {pct_coords}%\n")
        f.write(f"\nIssues: {len(issues)}\n")
        for issue in issues:
            f.write(f"  {issue}\n")
    
    print(f"\n📄 Relatório salvo: {filename}")
    
    return {"issues": issues, "stats": stats}

if __name__ == "__main__":
    main()

