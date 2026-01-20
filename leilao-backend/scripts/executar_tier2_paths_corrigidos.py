#!/usr/bin/env python3
"""Execução completa do TIER 2 com paths corrigidos - 15 sites"""
import asyncio, json, sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extractors.extrator_tier2_stealth import ExtratorTier2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 15 SITES COM PATHS CORRIGIDOS
SITES_EXECUTAR = [
    "agenciadeleiloes.com.br",
    "bianchileiloes.com.br",
    "ckleiloes.com.br",
    "duxleiloes.com.br",
    "gtleiloes.com.br",
    "juleiloes.com.br",
    "leffaleiloes.com.br",
    "leiloesfederal.com.br",
    "marceloleiloeiro.com.br",
    "marquesbarretoleiloes.com.br",
    "michellileiloes.com.br",
    "pbcastro.com.br",
    "rangelleiloes.com.br",
    "renovarleiloes.com.br",
    "sold.com.br"
]

async def main():
    logger.info(f"\n{'='*80}")
    logger.info(f"🚀 TIER 2 - EXECUÇÃO COMPLETA COM PATHS CORRIGIDOS")
    logger.info(f"{'='*80}")
    logger.info(f"Sites a processar: {len(SITES_EXECUTAR)}")
    logger.info(f"Estimativa: 1.000-3.000 imóveis adicionais")
    logger.info(f"Tempo estimado: ~20-30 minutos\n")
    
    extrator = ExtratorTier2()
    await extrator.setup_browser()
    
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Iniciando extração de {len(SITES_EXECUTAR)} sites")
        logger.info(f"{'='*60}\n")
        
        for i, dominio in enumerate(SITES_EXECUTAR, 1):
            logger.info(f"\n[{i}/{len(SITES_EXECUTAR)}] {'-'*40}")
            resultado = await extrator.extrair_site(dominio, None)
            
            if resultado["sucesso"]:
                extrator.resultados.append(resultado)
                logger.info(f"   ✅ Sucesso: {resultado['total_imoveis']} imóveis")
            else:
                extrator.falhas.append(resultado)
                erro = resultado.get('erro') or resultado.get('bloqueio_detectado') or 'Nenhum imóvel'
                logger.warning(f"   ❌ Falha: {erro}")
            
            await asyncio.sleep(2)
        
        # Salvar resultados
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path("logs/extracao_fase2/tier2")
        output_file = output_dir / f"tier2_paths_corrigidos_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "tier": "TIER_2_PATHS_CORRIGIDOS",
                "timestamp": datetime.now().isoformat(),
                "sites_processados": SITES_EXECUTAR,
                "total_sites": len(SITES_EXECUTAR),
                "sucesso": len(extrator.resultados),
                "falhas": len(extrator.falhas),
                "total_imoveis": sum(r["total_imoveis"] for r in extrator.resultados),
                "resultados": extrator.resultados,
                "falhas_detalhes": extrator.falhas
            }, f, ensure_ascii=False, indent=2)
        
        # Relatório final
        total = len(SITES_EXECUTAR)
        sucessos = len(extrator.resultados)
        taxa = (sucessos / total * 100) if total > 0 else 0
        total_imoveis = sum(r["total_imoveis"] for r in extrator.resultados)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 RELATÓRIO FINAL")
        logger.info(f"{'='*80}")
        logger.info(f"Sites processados: {total}")
        logger.info(f"Sucessos: {sucessos}")
        logger.info(f"Falhas: {len(extrator.falhas)}")
        logger.info(f"Taxa de sucesso: {taxa:.1f}%")
        logger.info(f"Total de imóveis: {total_imoveis}")
        logger.info(f"Custo: $0 (grátis!)")
        logger.info(f"{'='*80}\n")
        
        if extrator.resultados:
            logger.info(f"✅ SITES COM SUCESSO ({sucessos}):")
            for r in extrator.resultados:
                logger.info(f"   {r['dominio']}: {r['total_imoveis']} imóveis")
        
        if extrator.falhas:
            logger.info(f"\n❌ SITES COM FALHA ({len(extrator.falhas)}):")
            for f in extrator.falhas:
                erro = f.get('erro') or f.get('bloqueio_detectado') or 'Nenhum imóvel'
                logger.info(f"   {f['dominio']}: {erro}")
        
        logger.info(f"\n📁 Resultados salvos em: {output_file}")
        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 EXECUÇÃO COMPLETA!")
        logger.info(f"{'='*80}\n")
        
    finally:
        if extrator.browser:
            await extrator.browser.close()

if __name__ == "__main__":
    asyncio.run(main())
