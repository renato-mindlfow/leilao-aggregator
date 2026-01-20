#!/usr/bin/env python3
"""ORQUESTRADOR FASE 2: Executa extração em 3 tiers"""
import asyncio, json, subprocess, sys, codecs
from datetime import datetime
from pathlib import Path
import logging

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def executar_tier(tier: int, script_name: str):
    logger.info(f"\n{'='*70}\n🚀 EXECUTANDO TIER {tier}\n{'='*70}\n")
    script_path = Path(f"scripts/extractors/{script_name}")
    
    if not script_path.exists():
        logger.error(f"❌ Script não encontrado: {script_path}")
        return False
    
    try:
        result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True, timeout=7200)
        if result.returncode == 0:
            logger.info(f"✅ TIER {tier} completado com sucesso")
            return True
        else:
            logger.error(f"❌ TIER {tier} falhou: {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"❌ TIER {tier} timeout (2h)")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao executar TIER {tier}: {e}")
        return False

async def consolidar_resultados():
    logger.info(f"\n{'='*70}\n📊 CONSOLIDANDO RESULTADOS\n{'='*70}\n")
    todos_imoveis, estatisticas = [], {"timestamp": datetime.now().isoformat(), "tiers": {}}
    
    for tier in [1, 2, 3]:
        tier_dir = Path(f"logs/extracao_fase2/tier{tier}")
        if not tier_dir.exists(): continue
        
        arquivos = list(tier_dir.glob(f"tier{tier}_resultados_*.json"))
        if not arquivos: continue
        
        arquivo_recente = max(arquivos, key=lambda x: x.stat().st_mtime)
        with open(arquivo_recente, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        estatisticas["tiers"][f"tier_{tier}"] = {
            "sucesso": dados.get("sucesso", 0), "falhas": dados.get("falhas", 0),
            "total_imoveis": dados.get("total_imoveis", 0)}
        
        for resultado in dados.get("resultados", []):
            todos_imoveis.extend(resultado.get("imoveis", []))
    
    output_dir = Path("logs/extracao_fase2")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    estatisticas["total_imoveis"] = len(todos_imoveis)
    estatisticas_file = output_dir / f"estatisticas_consolidadas_{timestamp}.json"
    with open(estatisticas_file, 'w', encoding='utf-8') as f:
        json.dump(estatisticas, f, ensure_ascii=False, indent=2)
    
    imoveis_file = output_dir / f"todos_imoveis_{timestamp}.json"
    with open(imoveis_file, 'w', encoding='utf-8') as f:
        json.dump(todos_imoveis, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n📊 RESUMO FINAL:")
    logger.info(f"   Total de imóveis extraídos: {len(todos_imoveis)}")
    for tier, stats in estatisticas.get("tiers", {}).items():
        logger.info(f"   {tier}: {stats['total_imoveis']} imóveis de {stats['sucesso']} sites")
    logger.info(f"\n📁 Arquivos salvos:\n   {estatisticas_file}\n   {imoveis_file}")
    return todos_imoveis

async def main():
    logger.info(f"\n{'='*70}\n🎯 FASE 2: EXTRAÇÃO INTELIGENTE COM ROTEAMENTO\n{'='*70}")
    logger.info(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*70}\n")
    inicio = datetime.now()
    
    await executar_tier(1, "extrator_tier1_http.py")
    await executar_tier(2, "extrator_tier2_stealth.py")
    await executar_tier(3, "extrator_tier3_scrapingbee.py")
    
    todos_imoveis = await consolidar_resultados()
    fim = datetime.now()
    
    logger.info(f"\n{'='*70}\n🎉 FASE 2 COMPLETA!\n{'='*70}")
    logger.info(f"Duração: {fim - inicio}")
    logger.info(f"Total de imóveis: {len(todos_imoveis)}\n{'='*70}\n")

if __name__ == "__main__":
    asyncio.run(main())
