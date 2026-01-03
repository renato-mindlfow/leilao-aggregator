"""
Script para aplicar migração de descoberta de estrutura.
Executa o SQL necessário para adicionar as colunas na tabela auctioneers.
"""

import os
import sys
import logging
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar .env
load_dotenv()

def apply_migration():
    """Aplica a migração de descoberta"""
    
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL não configurada")
        return False
    
    # Ler SQL do arquivo de migração
    migration_file = os.path.join(os.path.dirname(__file__), "..", "migrations", "002_add_discovery_columns.sql")
    
    if not os.path.exists(migration_file):
        logger.error(f"Arquivo de migração não encontrado: {migration_file}")
        return False
    
    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()
    
    try:
        conn = psycopg.connect(database_url, row_factory=dict_row)
        conn.autocommit = True
        
        with conn.cursor() as cur:
            # Executar SQL
            logger.info("Aplicando migração de descoberta...")
            cur.execute(sql)
            logger.info("✅ Migração aplicada com sucesso!")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao aplicar migração: {e}")
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)

