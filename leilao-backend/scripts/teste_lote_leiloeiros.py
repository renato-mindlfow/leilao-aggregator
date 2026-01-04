"""
Testa scraping em lote e identifica padrões de sucesso/falha
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def testar_descoberta_lote(limite: int = 20):
    """Testa descoberta de estrutura em lote"""
    from app.services.discovery_orchestrator import discovery_orchestrator
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTE: Descoberta em lote ({limite} leiloeiros)")
    logger.info("="*60)
    
    result = await discovery_orchestrator.run_discovery(limit=limite)
    
    logger.info(f"Sucesso: {result['success']}/{result['total']}")
    logger.info(f"Falhas: {result['failed']}")
    
    return result

async def testar_scraping_lote(limite: int = 10):
    """Testa scraping em lote"""
    from app.services.scraper_orchestrator import scraper_orchestrator
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTE: Scraping em lote ({limite} leiloeiros)")
    logger.info("="*60)
    
    result = await scraper_orchestrator.run_all_smart(
        skip_geocoding=True,
        limit=limite
    )
    
    logger.info(f"Sucesso: {result['successful']}/{result['total_auctioneers']}")
    logger.info(f"Imóveis: {result['total_properties']}")
    
    if result.get('errors'):
        logger.info("\nErros:")
        for err in result['errors']:
            logger.info(f"  - {err['name']}: {err['error'][:60]}")
    
    return result

def analisar_resultados():
    """Analisa resultados e identifica padrões"""
    logger.info(f"\n{'='*60}")
    logger.info("ANÁLISE DE PADRÕES")
    logger.info("="*60)
    
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Sites com sucesso vs falha
    cur.execute("""
        SELECT 
            CASE 
                WHEN scrape_status = 'success' THEN 'sucesso'
                WHEN scrape_status = 'error' THEN 'erro'
                ELSE 'pendente'
            END as status,
            COUNT(*) as count
        FROM auctioneers
        GROUP BY 1
    """)
    
    logger.info("\nDistribuição de status:")
    for row in cur.fetchall():
        logger.info(f"  {row['status']}: {row['count']}")
    
    # Tipos de config vs sucesso
    cur.execute("""
        SELECT 
            scrape_config->>'site_type' as tipo,
            scrape_status,
            COUNT(*) as count
        FROM auctioneers
        WHERE scrape_config IS NOT NULL
        GROUP BY 1, 2
    """)
    
    logger.info("\nTipo de site vs status:")
    for row in cur.fetchall():
        logger.info(f"  {row['tipo']} + {row['scrape_status']}: {row['count']}")
    
    # Erros mais frequentes
    cur.execute("""
        SELECT 
            SUBSTRING(scrape_error, 1, 50) as erro,
            COUNT(*) as count
        FROM auctioneers
        WHERE scrape_error IS NOT NULL
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 5
    """)
    
    logger.info("\nTop 5 erros:")
    for row in cur.fetchall():
        logger.info(f"  ({row['count']}x) {row['erro']}")
    
    conn.close()

async def main():
    # Primeiro: descoberta
    await testar_descoberta_lote(limite=10)
    
    # Depois: scraping
    await testar_scraping_lote(limite=5)
    
    # Análise
    analisar_resultados()

if __name__ == "__main__":
    asyncio.run(main())

