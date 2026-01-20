#!/usr/bin/env python3
"""
Persistência direta no Supabase usando psycopg2
Usa DATABASE_URL do .env ou variável de ambiente
"""
import json
import os
import hashlib
import sys
from datetime import datetime
from typing import List, Dict
import logging

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Carregar do .env
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL não encontrada no .env")
    logger.error("   Adicione no arquivo leilao-backend/.env:")
    logger.error("   DATABASE_URL=postgresql://usuario:senha@host:porta/database")
    sys.exit(1)

def gerar_id_unico(imovel: Dict) -> str:
    """Gera ID único baseado na URL ou título+localização."""
    url = imovel.get('source_url', '')
    if url:
        return hashlib.md5(url.encode()).hexdigest()[:32]
    
    chave = f"{imovel.get('title', '')}|{imovel.get('city', '')}|{imovel.get('state', '')}"
    return hashlib.md5(chave.encode()).hexdigest()[:32]

def mapear_para_schema(imovel: Dict) -> tuple:
    """Mapeia imóvel para tupla de valores para INSERT."""
    now = datetime.utcnow()
    
    id_unico = gerar_id_unico(imovel)
    
    return (
        id_unico,  # id
        imovel.get('title'),  # title
        imovel.get('category', 'Outro'),  # category
        imovel.get('auction_type', 'Extrajudicial'),  # auction_type
        imovel.get('state'),  # state
        imovel.get('city'),  # city
        imovel.get('neighborhood'),  # neighborhood
        imovel.get('address'),  # address
        imovel.get('description', imovel.get('texto_card')),  # description
        imovel.get('area_total'),  # area_total
        imovel.get('area_privativa'),  # area_privativa
        imovel.get('evaluation_value'),  # evaluation_value
        imovel.get('first_auction_value'),  # first_auction_value
        imovel.get('first_auction_date'),  # first_auction_date
        imovel.get('second_auction_value'),  # second_auction_value
        imovel.get('second_auction_date'),  # second_auction_date
        imovel.get('discount_percentage'),  # discount_percentage
        imovel.get('image_url'),  # image_url
        imovel.get('auctioneer_id'),  # auctioneer_id
        imovel.get('auctioneer_name', imovel.get('dominio')),  # auctioneer_name
        imovel.get('auctioneer_url', imovel.get('url_base')),  # auctioneer_url
        imovel.get('source_url'),  # source_url
        imovel.get('source', 'scraper_fase2'),  # source
        True,  # is_active
        False,  # is_duplicate
        now,  # created_at
        now,  # updated_at
        now,  # last_seen_at
    )

def inserir_no_supabase_direto(imoveis: List[Dict], batch_size: int = 100):
    """Insere imóveis no Supabase usando psycopg2 direto."""
    
    try:
        import psycopg2
        from psycopg2.extras import execute_batch
    except ImportError:
        logger.error("❌ psycopg2 não instalado. Execute: pip install psycopg2-binary")
        return 0, 0
    
    total = len(imoveis)
    inseridos = 0
    atualizados = 0
    erros = 0
    
    logger.info(f"🔌 Conectando ao Supabase...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        logger.info("✅ Conectado ao Supabase (PostgreSQL)")
        
        # SQL de UPSERT (INSERT ... ON CONFLICT DO UPDATE)
        insert_sql = """
        INSERT INTO properties (
            id, title, category, auction_type, state, city, neighborhood, 
            address, description, area_total, area_privativa, evaluation_value,
            first_auction_value, first_auction_date, second_auction_value, 
            second_auction_date, discount_percentage, image_url,
            auctioneer_id, auctioneer_name, auctioneer_url, source_url, source,
            is_active, is_duplicate, created_at, updated_at, last_seen_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            state = EXCLUDED.state,
            city = EXCLUDED.city,
            first_auction_value = EXCLUDED.first_auction_value,
            updated_at = EXCLUDED.updated_at,
            last_seen_at = EXCLUDED.last_seen_at
        """
        
        logger.info(f"\n🚀 Iniciando inserção de {total} imóveis em lotes de {batch_size}...")
        
        for i in range(0, total, batch_size):
            batch = imoveis[i:i+batch_size]
            registros = [mapear_para_schema(im) for im in batch]
            
            try:
                execute_batch(cur, insert_sql, registros)
                conn.commit()
                
                inseridos += len(batch)
                logger.info(f"✅ Lote {i//batch_size + 1}: {len(batch)} imóveis ({inseridos}/{total})")
                
            except Exception as e:
                conn.rollback()
                erros += len(batch)
                logger.error(f"❌ Erro no lote {i//batch_size + 1}: {e}")
        
        # Verificar quantos registros temos no total
        cur.execute("SELECT COUNT(*) FROM properties WHERE source = 'scraper_fase2'")
        total_db = cur.fetchone()[0]
        
        logger.info(f"\n📊 Resultado final:")
        logger.info(f"   ✅ Processados: {inseridos}")
        logger.info(f"   ❌ Erros: {erros}")
        logger.info(f"   📊 Total no banco (source=scraper_fase2): {total_db}")
        
        cur.close()
        conn.close()
        
        return inseridos, erros
        
    except Exception as e:
        logger.error(f"❌ Erro ao conectar/inserir: {e}")
        return 0, 0

def main():
    logger.info("="*80)
    logger.info("🚀 PERSISTÊNCIA DIRETA NO SUPABASE")
    logger.info("="*80)
    
    # Carregar arquivo consolidado
    input_file = "logs/extracao_fase2/imoveis_consolidados_final.json"
    
    logger.info(f"\n📂 Carregando arquivo: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        imoveis = data.get('imoveis', [])
        logger.info(f"✅ Carregados: {len(imoveis)} imóveis")
        
    except FileNotFoundError:
        logger.error(f"❌ Arquivo não encontrado: {input_file}")
        logger.error("   Execute primeiro: python scripts/consolidar_e_persistir.py")
        return
    except Exception as e:
        logger.error(f"❌ Erro ao carregar arquivo: {e}")
        return
    
    # Persistir no Supabase
    inseridos, erros = inserir_no_supabase_direto(imoveis)
    
    logger.info("\n" + "="*80)
    logger.info("✅ PROCESSO CONCLUÍDO!")
    logger.info("="*80)

if __name__ == "__main__":
    main()
