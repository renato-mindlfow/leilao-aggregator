#!/usr/bin/env python3
"""
Script para sincronização diária.

Execute com: python scripts/run_daily_sync.py

Pode ser configurado no crontab (Linux) ou Task Scheduler (Windows).
"""

import asyncio
import logging
import sys
from pathlib import Path

# Adiciona diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/sync_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """
    Executa sincronização completa.
    """
    logger.info("=" * 60)
    logger.info("INICIANDO SINCRONIZAÇÃO DIÁRIA")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        from app.services.sync_service import run_full_sync
        
        report = await run_full_sync()
        
        logger.info("\n" + "=" * 60)
        logger.info("RELATÓRIO DE SINCRONIZAÇÃO")
        logger.info("=" * 60)
        logger.info(f"Início: {report.get('start_time')}")
        logger.info(f"Fim: {report.get('end_time')}")
        logger.info(f"Duração: {report.get('duration_seconds', 0):.1f} segundos")
        logger.info(f"Total extraído: {report.get('total_scraped', 0)}")
        logger.info(f"Inseridos: {report.get('total_inserted', 0)}")
        logger.info(f"Atualizados: {report.get('total_updated', 0)}")
        logger.info(f"Ignorados: {report.get('total_skipped', 0)}")
        logger.info(f"Erros: {report.get('total_errors', 0)}")
        
        if report.get('errors'):
            logger.warning("\nErros encontrados:")
            for error in report['errors'][:10]:
                logger.warning(f"  - {error}")
        
        logger.info("=" * 60)
        logger.info("SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"ERRO CRÍTICO: {e}")
        sys.exit(1)
    
    end_time = datetime.now()
    logger.info(f"Tempo total: {(end_time - start_time).total_seconds():.1f} segundos")

if __name__ == "__main__":
    # Cria diretório de logs se não existir
    Path("logs").mkdir(exist_ok=True)
    
    asyncio.run(main())

