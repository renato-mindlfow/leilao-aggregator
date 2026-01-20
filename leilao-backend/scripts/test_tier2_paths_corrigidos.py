#!/usr/bin/env python3
"""Teste do TIER 2 com paths corrigidos - 5 sites para validação"""
import asyncio, json, sys
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extractors.extrator_tier2_stealth import ExtratorTier2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 5 SITES PARA TESTE (variedade de paths)
SITES_TESTE = [
    "bianchileiloes.com.br",       # /busca - 189 links
    "renovarleiloes.com.br",       # /busca - 186 links
    "marceloleiloeiro.com.br",     # /busca - 188 links
    "leiloesfederal.com.br",       # /leiloes - 16 links
    "pbcastro.com.br"              # /imoveis - 28 links (único com /imoveis)
]

async def main():
    logger.info(f"\n{'='*80}")
    logger.info(f"🧪 TESTE TIER 2 - PATHS CORRIGIDOS")
    logger.info(f"{'='*80}")
    logger.info(f"Sites no teste: {len(SITES_TESTE)}")
    logger.info(f"Objetivo: Validar paths descobertos automaticamente\n")
    
    extrator = ExtratorTier2()
    await extrator.setup_browser()
    
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Iniciando extração de {len(SITES_TESTE)} sites")
        logger.info(f"{'='*60}\n")
        
        for i, dominio in enumerate(SITES_TESTE, 1):
            logger.info(f"\n[{i}/{len(SITES_TESTE)}] {'-'*40}")
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
        output_file = output_dir / f"teste_paths_corrigidos_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "teste": "paths_corrigidos",
                "timestamp": datetime.now().isoformat(),
                "sites_testados": SITES_TESTE,
                "total_sites": len(SITES_TESTE),
                "sucesso": len(extrator.resultados),
                "falhas": len(extrator.falhas),
                "total_imoveis": sum(r["total_imoveis"] for r in extrator.resultados),
                "resultados": extrator.resultados,
                "falhas_detalhes": extrator.falhas
            }, f, ensure_ascii=False, indent=2)
        
        # Relatório
        total = len(SITES_TESTE)
        sucessos = len(extrator.resultados)
        taxa = (sucessos / total * 100) if total > 0 else 0
        total_imoveis = sum(r["total_imoveis"] for r in extrator.resultados)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 RELATÓRIO DO TESTE")
        logger.info(f"{'='*80}")
        logger.info(f"Sites testados: {total}")
        logger.info(f"Sucessos: {sucessos}")
        logger.info(f"Falhas: {len(extrator.falhas)}")
        logger.info(f"Taxa de sucesso: {taxa:.1f}%")
        logger.info(f"Total de imóveis: {total_imoveis}")
        logger.info(f"{'='*80}\n")
        
        if extrator.resultados:
            logger.info(f"✅ SITES COM SUCESSO:")
            for r in extrator.resultados:
                logger.info(f"   {r['dominio']}: {r['total_imoveis']} imóveis")
        
        if extrator.falhas:
            logger.info(f"\n❌ SITES COM FALHA:")
            for f in extrator.falhas:
                erro = f.get('erro') or f.get('bloqueio_detectado') or 'Nenhum imóvel'
                logger.info(f"   {f['dominio']}: {erro}")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🎯 RECOMENDAÇÃO:")
        logger.info(f"{'='*80}")
        
        if taxa >= 60:
            logger.info(f"✅ Taxa de {taxa:.1f}% é BOA!")
            logger.info(f"✅ APROVAR execução completa dos 15 sites")
            logger.info(f"✅ Expectativa: +1.000-3.000 imóveis adicionais")
        elif taxa >= 40:
            logger.info(f"⚠️ Taxa de {taxa:.1f}% é RAZOÁVEL")
            logger.info(f"⚠️ Considere executar, mas com expectativas ajustadas")
        else:
            logger.info(f"❌ Taxa de {taxa:.1f}% é BAIXA")
            logger.info(f"❌ Investigar problemas antes de executar completo")
        
        logger.info(f"\n📁 Resultados salvos em: {output_file}")
        logger.info(f"{'='*80}\n")
        
    finally:
        if extrator.browser:
            await extrator.browser.close()

if __name__ == "__main__":
    asyncio.run(main())
