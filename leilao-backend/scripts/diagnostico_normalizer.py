"""
Script de diagnóstico para identificar exatamente qual campo causa o erro 'NoneType' object has no attribute 'replace'
"""
import asyncio
import traceback
import logging
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.universal_scraper import universal_scraper
from app.services.ai_normalizer import ai_normalizer

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def diagnostico():
    """Identifica exatamente qual campo causa o erro de None.replace()"""
    
    # 1. Extrair dados reais
    auctioneer = {
        'id': 'test', 
        'name': 'Turanileiloes', 
        'website': 'https://www.turanileiloes.com.br'
    }
    config = {
        'site_type': 'list_based', 
        'fallback_url': 'https://www.turanileiloes.com.br/imoveis'
    }
    
    logger.info("Extraindo imóveis...")
    try:
        props = await universal_scraper.scrape_with_config(auctioneer, config)
        logger.info(f"Extraídos: {len(props)} imóveis")
    except Exception as e:
        logger.error(f"Erro ao extrair imóveis: {e}")
        traceback.print_exc()
        return
    
    if not props:
        logger.error("Nenhum imóvel extraído!")
        return
    
    # 2. Tentar normalizar cada imóvel
    logger.info("\n=== TESTANDO NORMALIZAÇÃO ===")
    for i, prop in enumerate(props):
        logger.info(f"\n--- Imóvel {i+1} ---")
        logger.info(f"Dados brutos: {prop}")
        
        try:
            # Testar cada campo individualmente
            test_fields = ['title', 'address', 'city', 'state', 'category', 'area', 'description', 'price']
            
            for field in test_fields:
                value = prop.get(field)
                logger.info(f"  {field}: {repr(value)} (tipo: {type(value).__name__})")
                
                # Simular operações de replace
                if value is not None and hasattr(value, 'replace'):
                    try:
                        _ = value.replace('x', 'y')
                    except Exception as e:
                        logger.error(f"    ERRO em {field}.replace(): {e}")
            
            # Testar normalização completa
            normalized = await ai_normalizer.normalize_property(prop)
            logger.info(f"  ✅ Normalização OK")
            
        except Exception as e:
            logger.error(f"  ❌ ERRO na normalização: {e}")
            traceback.print_exc()
            
            # Identificar método específico que falhou
            logger.info("\n  Testando métodos individuais:")
            
            # Testar _normalize_price
            try:
                ai_normalizer._clean_price(prop.get('price'))
                logger.info("    _clean_price: OK")
            except Exception as e:
                logger.error(f"    _clean_price: ERRO - {e}")
                traceback.print_exc()
            
            # Testar _clean_area
            try:
                ai_normalizer._clean_area(prop.get('area'))
                logger.info("    _clean_area: OK")
            except Exception as e:
                logger.error(f"    _clean_area: ERRO - {e}")
                traceback.print_exc()
            
            # Testar _normalize_category
            try:
                ai_normalizer._normalize_category(prop.get('category'))
                logger.info("    _normalize_category: OK")
            except Exception as e:
                logger.error(f"    _normalize_category: ERRO - {e}")
                traceback.print_exc()
            
            # Testar _normalize_state
            try:
                ai_normalizer._normalize_state(prop.get('state'))
                logger.info("    _normalize_state: OK")
            except Exception as e:
                logger.error(f"    _normalize_state: ERRO - {e}")
                traceback.print_exc()
            
            # Testar _normalize_city
            try:
                ai_normalizer._normalize_city(prop.get('city'))
                logger.info("    _normalize_city: OK")
            except Exception as e:
                logger.error(f"    _normalize_city: ERRO - {e}")
                traceback.print_exc()
            
            break  # Parar no primeiro erro para análise

if __name__ == "__main__":
    asyncio.run(diagnostico())

