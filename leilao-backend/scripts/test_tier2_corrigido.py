#!/usr/bin/env python3
"""Teste do TIER 2 corrigido com 5 sites"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'extractors'))

from extrator_tier2_stealth import ExtratorTier2
import json
from pathlib import Path

async def main():
    # Carregar config
    config_path = Path("config/roteamento_sites.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Pegar 5 sites do TIER 2 (variados - alguns com CloudFlare, alguns sem)
    sites_teste = [
        "agenciadeleiloes.com.br",      # Falhou com 0 imóveis antes
        "alexiusleiloes.com.br",        # Falhou com 0 imóveis antes
        "amtleiloes.com.br",            # Falhou com 0 imóveis antes
        "megaleiloes.com.br",           # Reclassificado, tem config de paginação
        "sold.com.br"                   # Reclassificado, Next.js
    ]
    
    config_paginacao = config.get("PAGINACAO", {}).get("sites", {})
    
    print(f"\n{'='*70}")
    print(f"🧪 TESTE TIER 2 CORRIGIDO")
    print(f"{'='*70}")
    print(f"Sites: {', '.join(sites_teste)}\n")
    
    extrator = ExtratorTier2()
    await extrator.processar_lista(sites_teste, config_paginacao)
    
    # Resumo
    print(f"\n\n{'='*70}")
    print(f"📊 RESUMO DO TESTE:")
    print(f"{'='*70}")
    print(f"✅ Sucessos: {len(extrator.resultados)}")
    print(f"❌ Falhas: {len(extrator.falhas)}")
    print(f"📦 Total imóveis: {sum(r['total_imoveis'] for r in extrator.resultados)}")
    print(f"☁️ Promovidos p/ TIER 3: {len(extrator.promocoes_tier3)}")
    print(f"🎯 Taxa de sucesso: {len(extrator.resultados)/len(sites_teste)*100:.1f}%")
    
    if extrator.resultados:
        print(f"\n🏆 SITES COM SUCESSO:")
        for r in extrator.resultados:
            print(f"   {r['dominio']}: {r['total_imoveis']} imóveis")
    
    if extrator.promocoes_tier3:
        print(f"\n⚠️ SITES PROMOVIDOS PARA TIER 3 (CloudFlare):")
        for site in extrator.promocoes_tier3:
            print(f"   {site}")
    
    print(f"{'='*70}\n")

if __name__ == "__main__":
    asyncio.run(main())
