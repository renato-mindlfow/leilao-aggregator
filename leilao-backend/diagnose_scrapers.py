"""
Script de diagnóstico dos scrapers - PARTE 2 da TAREFA MASTER
Executa consultas SQL no Supabase para mapear o estado atual dos leiloeiros
"""

import psycopg
from psycopg.rows import dict_row
import json
from datetime import datetime

DATABASE_URL = "postgresql://postgres.nawbptwbmdgrkbpbwxzl:LeiloHub2025Pass@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

def execute_query(query, description):
    """Executa uma query e retorna os resultados"""
    print(f"\n{'='*80}")
    print(f">>> {description}")
    print(f"{'='*80}\n")
    
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                results = cur.fetchall()
                
                if results:
                    print(f"Total de registros: {len(results)}\n")
                    for i, row in enumerate(results[:50], 1):  # Limitar a 50 primeiros
                        print(f"{i}. {dict(row)}")
                    
                    if len(results) > 50:
                        print(f"\n... e mais {len(results) - 50} registros")
                    
                    return results
                else:
                    print("ERRO: Nenhum resultado encontrado")
                    return []
    except Exception as e:
        print(f"ERRO ao executar query: {e}")
        return []

def main():
    print("\n" + "="*80)
    print("DIAGNOSTICO DOS SCRAPERS - LeiloHub")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # FASE 2.1: Resumo geral
    query1 = """
    SELECT 
        scrape_status,
        COUNT(*) as total
    FROM auctioneers
    GROUP BY scrape_status
    ORDER BY total DESC;
    """
    results_status = execute_query(query1, "FASE 2.1.1 - Resumo Geral por Status")
    
    # FASE 2.1: Leiloeiros com erro
    query2 = """
    SELECT id, name, website, scrape_status, scrape_error
    FROM auctioneers
    WHERE scrape_status = 'error'
    ORDER BY name
    LIMIT 50;
    """
    results_errors = execute_query(query2, "FASE 2.1.2 - Leiloeiros com ERRO (primeiros 50)")
    
    # FASE 2.1: Leiloeiros pendentes
    query3 = """
    SELECT id, name, website, scrape_status
    FROM auctioneers
    WHERE scrape_status = 'pending' OR scrape_status IS NULL
    ORDER BY name
    LIMIT 50;
    """
    results_pending = execute_query(query3, "FASE 2.1.3 - Leiloeiros PENDENTES (primeiros 50)")
    
    # FASE 2.1: Leiloeiros funcionando
    query4 = """
    SELECT id, name, website, property_count, last_scrape
    FROM auctioneers
    WHERE scrape_status = 'success'
    ORDER BY property_count DESC;
    """
    results_success = execute_query(query4, "FASE 2.1.4 - Leiloeiros FUNCIONANDO")
    
    # FASE 2.1: Distribuição de imóveis por fonte
    query5 = """
    SELECT 
        a.name as leiloeiro,
        COUNT(p.id) as total_imoveis
    FROM properties p
    JOIN auctioneers a ON p.auctioneer_id = a.id
    GROUP BY a.name
    ORDER BY total_imoveis DESC
    LIMIT 20;
    """
    results_properties = execute_query(query5, "FASE 2.1.5 - Top 20 Leiloeiros por Número de Imóveis")
    
    # FASE 2.2: Classificar erros
    query6 = """
    SELECT 
        scrape_error,
        COUNT(*) as total
    FROM auctioneers
    WHERE scrape_status = 'error'
    GROUP BY scrape_error
    ORDER BY total DESC
    LIMIT 20;
    """
    results_error_types = execute_query(query6, "FASE 2.2 - Tipos de Erros Mais Comuns")
    
    # Salvar resultados em arquivo JSON
    report = {
        "timestamp": datetime.now().isoformat(),
        "resumo_status": [dict(r) for r in results_status],
        "leiloeiros_com_erro": [dict(r) for r in results_errors],
        "leiloeiros_pendentes": [dict(r) for r in results_pending],
        "leiloeiros_funcionando": [dict(r) for r in results_success],
        "distribuicao_imoveis": [dict(r) for r in results_properties],
        "tipos_de_erros": [dict(r) for r in results_error_types]
    }
    
    report_file = f"diagnostico_scrapers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n{'='*80}")
    print(f"OK - Diagnostico completo salvo em: {report_file}")
    print(f"{'='*80}\n")
    
    # RESUMO EXECUTIVO
    print("\n" + "="*80)
    print("RESUMO EXECUTIVO")
    print("="*80)
    
    if results_status:
        print("\nStatus dos Leiloeiros:")
        for row in results_status:
            status = row['scrape_status'] or 'null'
            total = row['total']
            print(f"  {status.upper()}: {total} leiloeiros")
    
    if results_properties:
        print("\nTop 5 Fontes de Imoveis:")
        for i, row in enumerate(results_properties[:5], 1):
            print(f"  {i}. {row['leiloeiro']}: {row['total_imoveis']:,} imoveis")
    
    if results_error_types:
        print("\nTop 5 Erros Mais Comuns:")
        for i, row in enumerate(results_error_types[:5], 1):
            error = row['scrape_error'] or 'null/None'
            total = row['total']
            print(f"  {i}. {error[:80]}: {total} ocorrencias")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
