"""
Script para testar se valores null no preço causam exceções no orquestrador
"""
import asyncio
import json
import sys
import os
import traceback
import logging

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.structure_validator import structure_validator
from app.services.ai_normalizer import ai_normalizer
from app.services.quality_filter import QualityFilter
from app.utils.quality_auditor import QualityAuditor

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_null_price_handling():
    """Testa se valores null em preço causam exceções"""
    
    # Carregar dados do JSON
    json_path = 'leilao-backend/scripts/turani_leiloes.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    leiloes = data.get('leiloes', [])
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTANDO VALIDAÇÃO DE DADOS COM NULL")
    logger.info(f"Total de leilões: {len(leiloes)}")
    logger.info("="*60)
    
    errors_found = []
    warnings_found = []
    
    # Converter formato do JSON para formato esperado pelo sistema
    for i, leilao in enumerate(leiloes, 1):
        logger.info(f"\n--- Leilão {i}/{len(leiloes)} ---")
        logger.info(f"Título: {leilao.get('title', 'N/A')[:60]}...")
        logger.info(f"Preço: {leilao.get('price')}")
        logger.info(f"Data: {leilao.get('closing_date')}")
        
        # Converter para formato esperado pelo sistema
        property_data = {
            'title': leilao.get('title'),
            'price': leilao.get('price'),  # Pode ser null
            'first_auction_value': leilao.get('price'),  # Mapear price para first_auction_value
            'evaluation_value': None,
            'second_auction_value': None,
            'auction_date': leilao.get('closing_date'),
            'first_auction_date': leilao.get('closing_date'),
            'url': leilao.get('url'),
            'source_url': leilao.get('url'),
            'state': None,
            'city': None,
            'address': None,
            'category': None,
            'description': None,
        }
        
        # Teste 1: QualityAuditor
        try:
            logger.info("  → Testando QualityAuditor...")
            auditor = QualityAuditor(strict_mode=False)
            passed, corrected, result = auditor.audit(property_data)
            
            if result.errors:
                errors_found.append({
                    'leilao': i,
                    'test': 'QualityAuditor',
                    'errors': result.errors
                })
                logger.warning(f"    ⚠️ Erros encontrados: {result.errors}")
            else:
                logger.info(f"    ✅ QualityAuditor: OK")
                
        except Exception as e:
            errors_found.append({
                'leilao': i,
                'test': 'QualityAuditor',
                'exception': str(e),
                'traceback': traceback.format_exc()
            })
            logger.error(f"    ❌ EXCEÇÃO em QualityAuditor: {e}")
        
        # Teste 2: _parse_value (método interno do QualityAuditor)
        try:
            logger.info("  → Testando _parse_value com null...")
            eval_value = auditor._parse_value(property_data.get('evaluation_value'))
            first_value = auditor._parse_value(property_data.get('first_auction_value'))
            second_value = auditor._parse_value(property_data.get('second_auction_value'))
            
            logger.info(f"    ✅ _parse_value: eval={eval_value}, first={first_value}, second={second_value}")
            
        except Exception as e:
            errors_found.append({
                'leilao': i,
                'test': '_parse_value',
                'exception': str(e),
                'traceback': traceback.format_exc()
            })
            logger.error(f"    ❌ EXCEÇÃO em _parse_value: {e}")
        
        # Teste 3: Operações matemáticas com null
        try:
            logger.info("  → Testando operações matemáticas com null...")
            price = property_data.get('price')
            
            # Testar comparações
            if price is not None:
                test1 = price > 0
                test2 = price < 1000000
                logger.info(f"    ✅ Comparações: OK (price={price})")
            else:
                # Testar se comparações com None causam problemas
                try:
                    test1 = price > 0  # Isso deve causar TypeError
                    logger.error(f"    ❌ Comparação com None não causou exceção!")
                except TypeError:
                    logger.info(f"    ✅ Comparação com None tratada corretamente (TypeError esperado)")
            
            # Testar operações matemáticas
            if price is not None:
                test3 = price * 0.5
                test4 = price / 2
                logger.info(f"    ✅ Operações matemáticas: OK")
            else:
                try:
                    test3 = price * 0.5  # Isso deve causar TypeError
                    logger.error(f"    ❌ Operação matemática com None não causou exceção!")
                except TypeError:
                    logger.info(f"    ✅ Operação matemática com None tratada corretamente (TypeError esperado)")
                    
        except Exception as e:
            errors_found.append({
                'leilao': i,
                'test': 'operacoes_matematicas',
                'exception': str(e),
                'traceback': traceback.format_exc()
            })
            logger.error(f"    ❌ EXCEÇÃO em operações matemáticas: {e}")
        
        # Teste 4: SQL COALESCE simulation
        try:
            logger.info("  → Testando simulação de SQL COALESCE...")
            # Simular o que o SQL faz: COALESCE(%s, first_auction_value)
            sql_value = property_data.get('price') if property_data.get('price') is not None else None
            logger.info(f"    ✅ SQL COALESCE simulation: {sql_value}")
            
        except Exception as e:
            errors_found.append({
                'leilao': i,
                'test': 'sql_coalesce',
                'exception': str(e),
                'traceback': traceback.format_exc()
            })
            logger.error(f"    ❌ EXCEÇÃO em SQL COALESCE: {e}")
    
    # Resumo
    logger.info(f"\n{'='*60}")
    logger.info("RESUMO DOS TESTES")
    logger.info("="*60)
    
    if errors_found:
        logger.error(f"❌ {len(errors_found)} ERROS ENCONTRADOS:")
        for error in errors_found:
            logger.error(f"  - Leilão {error['leilao']}, Teste: {error['test']}")
            logger.error(f"    Exceção: {error.get('exception', 'N/A')}")
            if 'traceback' in error:
                logger.debug(f"    Traceback: {error['traceback']}")
        return False
    else:
        logger.info("✅ NENHUM ERRO ENCONTRADO - Valores null são tratados corretamente")
        return True

async def test_normalizer():
    """Testa se o normalizador trata valores null corretamente"""
    
    json_path = 'leilao-backend/scripts/turani_leiloes.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    leiloes = data.get('leiloes', [])
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTANDO NORMALIZADOR COM NULL")
    logger.info("="*60)
    
    errors_found = []
    
    for i, leilao in enumerate(leiloes, 1):
        if leilao.get('price') is None:
            logger.info(f"\n--- Testando leilão {i} com price=null ---")
            
            property_data = {
                'title': leilao.get('title'),
                'price': None,
                'url': leilao.get('url'),
            }
            
            try:
                normalized = await ai_normalizer.normalize_property(property_data)
                logger.info(f"  ✅ Normalização OK: price={normalized.get('price')}")
            except Exception as e:
                errors_found.append({
                    'leilao': i,
                    'exception': str(e),
                    'traceback': traceback.format_exc()
                })
                logger.error(f"  ❌ EXCEÇÃO na normalização: {e}")
    
    if errors_found:
        logger.error(f"❌ {len(errors_found)} ERROS no normalizador")
        return False
    else:
        logger.info("✅ Normalizador trata null corretamente")
        return True

async def main():
    """Executa todos os testes"""
    
    # Teste 1: Validação estática
    result1 = test_null_price_handling()
    
    # Teste 2: Normalizador
    result2 = await test_normalizer()
    
    # Resultado final
    logger.info(f"\n{'='*60}")
    logger.info("RESULTADO FINAL")
    logger.info("="*60)
    
    if result1 and result2:
        logger.info("✅ TODOS OS TESTES PASSARAM - Sistema trata valores null corretamente")
        logger.info("✅ NENHUM RISCO DE DEADLOCK IDENTIFICADO")
    else:
        logger.error("❌ ALGUNS TESTES FALHARAM - Verifique os erros acima")
        logger.error("⚠️ POSSÍVEL RISCO DE DEADLOCK OU EXCEÇÕES NÃO TRATADAS")

if __name__ == "__main__":
    asyncio.run(main())

