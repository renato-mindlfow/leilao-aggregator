"""
Diagnóstico completo do sistema de scraping.
Testa cada componente isoladamente e identifica pontos de falha.
"""
import asyncio
import traceback
import logging
import os
import sys
import time
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Resultados do diagnóstico
DIAGNOSTICO = {
    'timestamp': datetime.now().isoformat(),
    'componentes': {},
    'erros': [],
    'avisos': [],
    'recomendacoes': []
}

def log_resultado(componente: str, sucesso: bool, detalhes: str = ""):
    """Registra resultado de teste de componente"""
    DIAGNOSTICO['componentes'][componente] = {
        'sucesso': sucesso,
        'detalhes': detalhes
    }
    status = "✅" if sucesso else "❌"
    logger.info(f"{status} {componente}: {detalhes}")

def log_erro(erro: str, traceback_str: str = ""):
    """Registra erro encontrado"""
    DIAGNOSTICO['erros'].append({
        'erro': erro,
        'traceback': traceback_str
    })
    logger.error(f"❌ ERRO: {erro}")

def log_recomendacao(rec: str):
    """Registra recomendação de correção"""
    DIAGNOSTICO['recomendacoes'].append(rec)
    logger.info(f"💡 RECOMENDAÇÃO: {rec}")


async def testar_conexao_banco():
    """Testa conexão com o banco de dados"""
    logger.info("\n" + "="*60)
    logger.info("TESTE 1: Conexão com Banco de Dados")
    logger.info("="*60)
    
    # Teste com psycopg2 (síncrono)
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM auctioneers")
        count = cur.fetchone()[0]
        conn.close()
        log_resultado("psycopg2", True, f"{count} leiloeiros")
    except Exception as e:
        log_resultado("psycopg2", False, str(e))
        log_erro(f"Conexão psycopg2 falhou: {e}")
    
    # Teste com psycopg3 (async)
    try:
        import psycopg
        conn = psycopg.connect(os.environ.get('DATABASE_URL'))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM properties")
        count = cur.fetchone()[0]
        conn.close()
        log_resultado("psycopg3", True, f"{count} imóveis")
    except Exception as e:
        log_resultado("psycopg3", False, str(e))
        log_erro(f"Conexão psycopg3 falhou: {e}")


async def testar_servicos():
    """Testa importação e inicialização dos serviços"""
    logger.info("\n" + "="*60)
    logger.info("TESTE 2: Importação de Serviços")
    logger.info("="*60)
    
    servicos = [
        ('postgres_database', 'app.services.postgres_database', 'get_postgres_database'),
        ('ai_normalizer', 'app.services.ai_normalizer', 'ai_normalizer'),
        ('universal_scraper', 'app.services.universal_scraper', 'universal_scraper'),
        ('structure_validator', 'app.services.structure_validator', 'structure_validator'),
        ('site_discovery', 'app.services.site_discovery', 'site_discovery'),
        ('discovery_orchestrator', 'app.services.discovery_orchestrator', 'discovery_orchestrator'),
        ('scraper_orchestrator', 'app.services.scraper_orchestrator', 'scraper_orchestrator'),
    ]
    
    for nome, modulo, obj in servicos:
        try:
            mod = __import__(modulo, fromlist=[obj])
            getattr(mod, obj)
            log_resultado(nome, True, "Importado com sucesso")
        except Exception as e:
            log_resultado(nome, False, str(e))
            log_erro(f"Importação de {nome} falhou: {e}", traceback.format_exc())


async def testar_extracao_isolada():
    """Testa extração de dados isoladamente"""
    logger.info("\n" + "="*60)
    logger.info("TESTE 3: Extração de Dados")
    logger.info("="*60)
    
    from app.services.universal_scraper import universal_scraper
    
    # Leiloeiros de teste
    testes = [
        {
            'auctioneer': {'id': 'test1', 'name': 'Turanileiloes', 'website': 'https://www.turanileiloes.com.br'},
            'config': {'site_type': 'list_based', 'fallback_url': 'https://www.turanileiloes.com.br/imoveis'}
        },
        {
            'auctioneer': {'id': 'test2', 'name': 'Cunhaleiloeiro', 'website': 'https://www.cunhaleiloeiro.com.br'},
            'config': {'site_type': 'filter_based', 'fallback_url': 'https://www.cunhaleiloeiro.com.br/busca?tipo=Imóveis'}
        },
    ]
    
    for teste in testes:
        nome = teste['auctioneer']['name']
        try:
            start = time.time()
            props = await universal_scraper.scrape_with_config(
                teste['auctioneer'], 
                teste['config']
            )
            elapsed = time.time() - start
            log_resultado(
                f"extração_{nome}", 
                len(props) > 0, 
                f"{len(props)} imóveis em {elapsed:.1f}s"
            )
            
            # Salvar amostra para análise
            if props:
                DIAGNOSTICO[f'amostra_{nome}'] = props[0]
                
        except Exception as e:
            log_resultado(f"extração_{nome}", False, str(e))
            log_erro(f"Extração {nome} falhou: {e}", traceback.format_exc())


async def testar_normalizacao():
    """Testa normalização de dados"""
    logger.info("\n" + "="*60)
    logger.info("TESTE 4: Normalização de Dados")
    logger.info("="*60)
    
    from app.services.ai_normalizer import ai_normalizer
    
    # Casos de teste
    casos = [
        # Caso normal
        {
            'title': 'Apartamento 2 quartos',
            'price': 150000,
            'area': '80m²',
            'city': 'São Paulo',
            'state': 'SP',
            'category': 'Apartamento'
        },
        # Caso com None
        {
            'title': 'Casa',
            'price': None,
            'area': None,
            'city': None,
            'state': None,
            'category': None
        },
        # Caso com strings vazias
        {
            'title': '',
            'price': '',
            'area': '',
            'city': '',
            'state': '',
            'category': ''
        },
        # Caso com tipos errados
        {
            'title': 123,
            'price': 'abc',
            'area': ['100'],
            'city': {'nome': 'SP'},
            'state': True,
            'category': 456
        },
    ]
    
    for i, caso in enumerate(casos):
        try:
            result = ai_normalizer.normalize_property(caso)
            log_resultado(f"normalize_caso_{i+1}", True, "OK")
        except Exception as e:
            log_resultado(f"normalize_caso_{i+1}", False, str(e))
            log_erro(f"Normalização caso {i+1} falhou: {e}", traceback.format_exc())
            log_recomendacao(f"Corrigir normalize_property para tratar: {caso}")
    
    # Testar normalize_batch
    try:
        from app.services.universal_scraper import universal_scraper
        auctioneer = {'id': 'test', 'name': 'Turanileiloes', 'website': 'https://www.turanileiloes.com.br'}
        config = {'site_type': 'list_based', 'fallback_url': 'https://www.turanileiloes.com.br/imoveis'}
        
        props = await universal_scraper.scrape_with_config(auctioneer, config)
        if props:
            normalized = await ai_normalizer.normalize_batch(props)
            log_resultado("normalize_batch", True, f"{len(normalized)} imóveis")
        else:
            log_resultado("normalize_batch", False, "Sem dados para normalizar")
    except Exception as e:
        log_resultado("normalize_batch", False, str(e))
        log_erro(f"normalize_batch falhou: {e}", traceback.format_exc())


async def testar_validation_metrics():
    """Testa atualização de métricas de validação"""
    logger.info("\n" + "="*60)
    logger.info("TESTE 5: Validation Metrics")
    logger.info("="*60)
    
    from app.services.structure_validator import structure_validator
    
    # Usar psycopg2 para buscar um leiloeiro real
    import psycopg2
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cur = conn.cursor()
    cur.execute("SELECT id FROM auctioneers LIMIT 1")
    row = cur.fetchone()
    conn.close()
    
    if not row:
        log_resultado("validation_metrics", False, "Nenhum leiloeiro encontrado")
        return
    
    auctioneer_id = row[0]
    
    # Testar com timeout
    try:
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Timeout após 10 segundos")
        
        # Configurar timeout (só funciona em Unix)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)
        
        structure_validator.update_validation_metrics(
            auctioneer_id=auctioneer_id,
            success=True,
            properties_count=5
        )
        
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)
        
        log_resultado("validation_metrics", True, "OK")
        
    except TimeoutError:
        log_resultado("validation_metrics", False, "TIMEOUT - possível deadlock")
        log_erro("update_validation_metrics travou (timeout 10s)")
        log_recomendacao("Revisar update_validation_metrics - possível deadlock no banco")
    except Exception as e:
        log_resultado("validation_metrics", False, str(e))
        log_erro(f"validation_metrics falhou: {e}", traceback.format_exc())


async def testar_save_properties():
    """Testa salvamento de propriedades"""
    logger.info("\n" + "="*60)
    logger.info("TESTE 6: Salvamento de Propriedades")
    logger.info("="*60)
    
    from app.services.scraper_orchestrator import scraper_orchestrator
    
    # Criar propriedade de teste
    prop_teste = {
        'title': 'TESTE DIAGNÓSTICO - Apartamento',
        'price': 100000,
        'evaluation_value': 150000,
        'city': 'São Paulo',
        'state': 'SP',
        'category': 'Apartamento',
        'source_url': 'https://teste.diagnostico/12345',
        'external_id': f'DIAG_{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'auctioneer_id': 'diagnostico',
        'auctioneer_name': 'Diagnóstico'
    }
    
    try:
        # Testar _save_properties diretamente
        new_count, updated_count = scraper_orchestrator._save_properties(
            [prop_teste], 
            'diagnostico', 
            'Diagnóstico'
        )
        log_resultado("save_properties", True, f"new={new_count}, updated={updated_count}")
    except Exception as e:
        log_resultado("save_properties", False, str(e))
        log_erro(f"save_properties falhou: {e}", traceback.format_exc())


async def testar_fluxo_completo():
    """Testa fluxo completo de scraping"""
    logger.info("\n" + "="*60)
    logger.info("TESTE 7: Fluxo Completo (run_all_smart)")
    logger.info("="*60)
    
    from app.services.scraper_orchestrator import scraper_orchestrator
    
    try:
        result = await scraper_orchestrator.run_all_smart(
            skip_geocoding=True,
            limit=2
        )
        
        sucesso = result.get('successful', 0)
        falhas = result.get('failed', 0)
        total = result.get('total_auctioneers', 0)
        
        taxa = sucesso / max(total, 1)
        
        log_resultado(
            "fluxo_completo", 
            taxa >= 0.5,
            f"{sucesso}/{total} sucesso ({taxa:.0%})"
        )
        
        if result.get('errors'):
            for err in result['errors']:
                log_erro(f"{err['name']}: {err['error']}")
                
    except Exception as e:
        log_resultado("fluxo_completo", False, str(e))
        log_erro(f"Fluxo completo falhou: {e}", traceback.format_exc())


async def identificar_padroes():
    """Identifica padrões de sucesso e falha"""
    logger.info("\n" + "="*60)
    logger.info("ANÁLISE: Identificação de Padrões")
    logger.info("="*60)
    
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Padrões de sucesso
    cur.execute("""
        SELECT scrape_status, COUNT(*) as count
        FROM auctioneers
        GROUP BY scrape_status
        ORDER BY count DESC
    """)
    
    logger.info("\nStatus de scraping:")
    for row in cur.fetchall():
        logger.info(f"  {row['scrape_status']}: {row['count']}")
    
    # Erros mais comuns
    cur.execute("""
        SELECT scrape_error, COUNT(*) as count
        FROM auctioneers
        WHERE scrape_error IS NOT NULL
        GROUP BY scrape_error
        ORDER BY count DESC
        LIMIT 10
    """)
    
    logger.info("\nErros mais comuns:")
    for row in cur.fetchall():
        erro = row['scrape_error'][:80] if row['scrape_error'] else 'N/A'
        logger.info(f"  ({row['count']}x) {erro}")
    
    # Sites com config descoberto
    cur.execute("""
        SELECT name, discovery_status, 
               scrape_config->>'site_type' as site_type
        FROM auctioneers
        WHERE scrape_config IS NOT NULL
    """)
    
    logger.info("\nLeiloeiros com config descoberto:")
    for row in cur.fetchall():
        logger.info(f"  {row['name']}: {row['site_type']} ({row['discovery_status']})")
    
    conn.close()


def gerar_relatorio():
    """Gera relatório final do diagnóstico"""
    logger.info("\n" + "="*60)
    logger.info("RELATÓRIO FINAL DO DIAGNÓSTICO")
    logger.info("="*60)
    
    # Resumo de componentes
    total = len(DIAGNOSTICO['componentes'])
    sucesso = sum(1 for c in DIAGNOSTICO['componentes'].values() if c['sucesso'])
    
    logger.info(f"\nComponentes testados: {sucesso}/{total} OK")
    
    # Componentes com falha
    falhas = [k for k, v in DIAGNOSTICO['componentes'].items() if not v['sucesso']]
    if falhas:
        logger.info(f"\nComponentes com FALHA:")
        for f in falhas:
            logger.info(f"  ❌ {f}: {DIAGNOSTICO['componentes'][f]['detalhes']}")
    
    # Erros encontrados
    if DIAGNOSTICO['erros']:
        logger.info(f"\nErros encontrados: {len(DIAGNOSTICO['erros'])}")
        for err in DIAGNOSTICO['erros'][:5]:
            logger.info(f"  - {err['erro']}")
    
    # Recomendações
    if DIAGNOSTICO['recomendacoes']:
        logger.info(f"\nRecomendações de correção:")
        for rec in DIAGNOSTICO['recomendacoes']:
            logger.info(f"  💡 {rec}")
    
    # Salvar relatório em arquivo
    import json
    output_path = os.path.join(os.path.dirname(__file__), '..', 'diagnostico_resultado.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(DIAGNOSTICO, f, indent=2, default=str, ensure_ascii=False)
    
    logger.info(f"\nRelatório salvo em: {output_path}")


async def main():
    """Executa diagnóstico completo"""
    logger.info("="*60)
    logger.info("DIAGNÓSTICO COMPLETO DO SISTEMA DE SCRAPING")
    logger.info(f"Iniciado em: {datetime.now().isoformat()}")
    logger.info("="*60)
    
    await testar_conexao_banco()
    await testar_servicos()
    await testar_extracao_isolada()
    await testar_normalizacao()
    await testar_validation_metrics()
    await testar_save_properties()
    await testar_fluxo_completo()
    await identificar_padroes()
    gerar_relatorio()
    
    logger.info("\n" + "="*60)
    logger.info("DIAGNÓSTICO CONCLUÍDO")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())

