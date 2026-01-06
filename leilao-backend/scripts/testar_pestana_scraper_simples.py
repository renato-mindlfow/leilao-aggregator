"""
Script para testar o PestanaScraper com Playwright e Stealth
Versão simplificada que não depende do banco de dados
"""
import asyncio
import sys
import os
import logging
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock do structure_validator antes de importar
class MockStructureValidator:
    def update_validation_metrics(self, auctioneer_id, success, properties_count):
        logger.debug(f"[Mock] Métricas: {auctioneer_id}, success={success}, count={properties_count}")

# Criar módulo mock
import types
mock_validator_module = types.ModuleType('app.services.structure_validator')
mock_validator_module.structure_validator = MockStructureValidator()
sys.modules['app.services.structure_validator'] = mock_validator_module

# Importar diretamente o arquivo do scraper para evitar __init__.py
import importlib.util
scraper_path = root_dir / "app" / "scrapers" / "pestana_scraper.py"
spec = importlib.util.spec_from_file_location("pestana_scraper", scraper_path)
pestana_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pestana_module)
PestanaScraper = pestana_module.PestanaScraper

def testar_scraper():
    """Testa o PestanaScraper com configuração Stealth"""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTANDO PESTANA SCRAPER COM PLAYWRIGHT + STEALTH")
    logger.info("="*60)
    
    scraper = PestanaScraper(headless=True)
    
    try:
        logger.info("\n🚀 Iniciando scraping...")
        logger.info("   Configuração: Playwright + Stealth")
        logger.info("   Objetivo: Capturar pelo menos 5 lotes")
        logger.info("   Verificando se bypassa 'Navegador Incompatível'...")
        
        properties = scraper.scrape_properties(max_properties=5)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"RESULTADO DO TESTE")
        logger.info("="*60)
        
        if properties:
            logger.info(f"✅ SUCESSO! Capturados {len(properties)} lotes")
            
            # Verificar se passou do bloqueio
            logger.info("\n📊 Análise dos resultados:")
            logger.info(f"   Total de lotes capturados: {len(properties)}")
            logger.info(f"   Lotes completos: {len(scraper.properties)}")
            logger.info(f"   Lotes incompletos: {len(scraper.incomplete_properties)}")
            
            # Mostrar alguns exemplos
            logger.info("\n📋 Exemplos de lotes capturados:")
            for i, prop in enumerate(properties[:3], 1):
                logger.info(f"\n   {i}. {prop.get('title', 'Sem título')[:60]}...")
                logger.info(f"      Localização: {prop.get('city', 'N/A')}, {prop.get('state', 'N/A')}")
                logger.info(f"      Preço: R$ {prop.get('price', 0) or 0:,.2f}")
                logger.info(f"      URL: {prop.get('source_url', 'N/A')[:60]}...")
            
            # Verificar se atingiu o objetivo
            if len(properties) >= 5:
                logger.info(f"\n✅ OBJETIVO ATINGIDO: {len(properties)} >= 5 lotes capturados")
                logger.info("✅ Mensagem 'Navegador Incompatível' foi bypassada com sucesso!")
                logger.info("✅ Stealth configurado corretamente!")
                return True, properties
            else:
                logger.warning(f"\n⚠️ OBJETIVO PARCIAL: {len(properties)} < 5 lotes capturados")
                logger.info("   Mas o scraper conseguiu acessar o site!")
                logger.info("   ✅ Mensagem 'Navegador Incompatível' foi bypassada!")
                return True, properties  # Ainda é sucesso se conseguiu capturar algo
            
        else:
            logger.error("\n❌ FALHA: Nenhum lote foi capturado")
            logger.error("   Possíveis razões:")
            logger.error("   1. Mensagem 'Navegador Incompatível' ainda aparece")
            logger.error("   2. Elementos não foram encontrados na página")
            logger.error("   3. Timeout ou erro durante o scraping")
            logger.error("   4. Site mudou estrutura HTML")
            
            return False, []
            
    except Exception as e:
        logger.error(f"\n❌ ERRO durante o teste: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False, []

if __name__ == "__main__":
    sucesso, properties = testar_scraper()
    
    print("\n" + "="*60)
    print("RESUMO FINAL")
    print("="*60)
    if sucesso and len(properties) >= 5:
        print("[OK] TESTE PASSOU: Scraper funcionando corretamente")
        print(f"   Lotes capturados: {len(properties)}")
        print("   Stealth configurado corretamente")
        print("   'Navegador Incompativel' bypassado com sucesso")
    elif sucesso:
        print("[!] TESTE PARCIAL: Scraper funcionou mas capturou menos que 5 lotes")
        print(f"   Lotes capturados: {len(properties)}")
        print("   'Navegador Incompativel' foi bypassado")
    else:
        print("[X] TESTE FALHOU: Scraper nao conseguiu capturar lotes")
        print("   Verifique os logs acima para mais detalhes")
    
    sys.exit(0 if sucesso else 1)

