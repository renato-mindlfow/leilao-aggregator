"""
Script para corrigir scrapers com duplicate key errors
PARTE 3 da TAREFA MASTER
"""

import psycopg
from psycopg.rows import dict_row
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.nawbptwbmdgrkbpbwxzl:LeiloHub2025Pass@aws-1-sa-east-1.pooler.supabase.com:6543/postgres")

def check_duplicate_properties():
    """Verifica propriedades com IDs duplicados"""
    print("\n" + "="*80)
    print("INVESTIGANDO PROPRIEDADES COM IDs DUPLICADOS")
    print("="*80 + "\n")
    
    # IDs com problemas identificados
    problem_ids = [
        'Correaleiloes_Lote 1',
        'Centraljudicial_352',
        'Marangonileiloes_Lote 1',
        'Lancenoleilao_24090'
    ]
    
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                for prop_id in problem_ids:
                    print(f"\n{'='*60}")
                    print(f"Buscando: {prop_id}")
                    print(f"{'='*60}")
                    
                    # Buscar propriedade
                    cur.execute("""
                        SELECT id, title, auctioneer_id, source_url, created_at
                        FROM properties
                        WHERE id = %s
                    """, (prop_id,))
                    
                    result = cur.fetchone()
                    if result:
                        prop = dict(result)
                        print(f"ENCONTRADO:")
                        print(f"  ID: {prop['id']}")
                        print(f"  Title: {prop['title']}")
                        print(f"  Auctioneer: {prop['auctioneer_id']}")
                        print(f"  Source: {prop['source_url']}")
                        print(f"  Created: {prop['created_at']}")
                    else:
                        print(f"NÃO ENCONTRADO no banco")
                
                # Buscar padrão de IDs por leiloeiro
                print(f"\n{'='*80}")
                print("ANALISANDO PADRÃO DE IDs POR LEILOEIRO")
                print(f"{'='*80}\n")
                
                for auctioneer_id in ['117', '62', '226', '25']:  # IDs dos leiloeiros problemáticos
                    cur.execute("""
                        SELECT name FROM auctioneers WHERE id = %s
                    """, (auctioneer_id,))
                    
                    auctioneer = cur.fetchone()
                    if auctioneer:
                        auctioneer_name = auctioneer['name']
                        print(f"\n{auctioneer_name} (ID: {auctioneer_id}):")
                        
                        # Buscar todas as propriedades deste leiloeiro
                        cur.execute("""
                            SELECT id, title, source_url
                            FROM properties
                            WHERE auctioneer_id = %s
                            LIMIT 5
                        """, (auctioneer_id,))
                        
                        props = cur.fetchall()
                        if props:
                            print(f"  Total de propriedades: {len(props)}")
                            print(f"  Exemplos de IDs:")
                            for p in props:
                                print(f"    - {p['id']}")
                        else:
                            print(f"  Nenhuma propriedade encontrada")
                            
    except Exception as e:
        print(f"\nERRO: {e}")

def find_scrapers_using_configurable():
    """Encontra quais scrapers usam o configurable_scraper"""
    print("\n" + "="*80)
    print("PROCURANDO CONFIGURAÇÕES DE SCRAPERS")
    print("="*80 + "\n")
    
    import os
    import json
    
    # Procurar por arquivos de configuração
    backend_path = os.path.dirname(os.path.abspath(__file__))
    config_dirs = [
        os.path.join(backend_path, 'config'),
        os.path.join(backend_path, 'app', 'config'),
        os.path.join(backend_path, 'scrapers'),
        os.path.join(backend_path, 'app', 'scrapers'),
    ]
    
    for config_dir in config_dirs:
        if os.path.exists(config_dir):
            print(f"\n Verificando: {config_dir}")
            for file in os.listdir(config_dir):
                if file.endswith('.json'):
                    filepath = os.path.join(config_dir, file)
                    print(f"  Encontrado: {file}")
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            if isinstance(config, dict):
                                if 'Correaleiloes' in str(config) or 'Centraljudicial' in str(config):
                                    print(f"    -> Contém leiloeiro problemático!")
                    except:
                        pass

if __name__ == "__main__":
    print("INICIANDO DIAGNÓSTICO DE DUPLICATE KEY ERRORS\n")
    
    check_duplicate_properties()
    find_scrapers_using_configurable()
    
    print("\n" + "="*80)
    print("DIAGNÓSTICO CONCLUÍDO")
    print("="*80 + "\n")
