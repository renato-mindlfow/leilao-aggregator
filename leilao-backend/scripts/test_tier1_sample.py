#!/usr/bin/env python3
"""Teste do TIER 1 com amostra pequena para validar otimizações"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'extractors'))

from extrator_tier1_http import ExtratorTier1
import json
from pathlib import Path

async def main():
    # Carregar config
    config_path = Path("config/roteamento_sites.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Pegar primeiros 10 sites do TIER 1
    sites_tier1 = config.get("TIER_1_HTTP", {}).get("sites", [])[:10]
    config_paginacao = config.get("PAGINACAO", {}).get("sites", {})
    
    print(f"\n🧪 TESTE COM AMOSTRA: {len(sites_tier1)} sites")
    print(f"Sites: {', '.join(sites_tier1)}\n")
    
    extrator = ExtratorTier1()
    await extrator.processar_lista(sites_tier1, config_paginacao)
    
    # Resumo
    print(f"\n\n{'='*70}")
    print(f"📊 RESUMO DO TESTE:")
    print(f"{'='*70}")
    print(f"✅ Sucessos: {len(extrator.resultados)}")
    print(f"❌ Falhas: {len(extrator.falhas)}")
    print(f"📦 Total imóveis: {sum(r['total_imoveis'] for r in extrator.resultados)}")
    print(f"🎯 Taxa de sucesso: {len(extrator.resultados)/len(sites_tier1)*100:.1f}%")
    
    if extrator.resultados:
        print(f"\n🏆 SITES COM SUCESSO:")
        for r in extrator.resultados:
            print(f"   {r['dominio']}: {r['total_imoveis']} imóveis")
    
    print(f"{'='*70}\n")

if __name__ == "__main__":
    asyncio.run(main())
