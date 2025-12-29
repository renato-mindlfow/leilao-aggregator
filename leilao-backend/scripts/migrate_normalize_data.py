"""
Script de migração para normalizar dados existentes no banco.

Este script:
1. Busca todos os imóveis do banco
2. Normaliza categoria, estado, cidade
3. Atualiza os registros

Execute com: python scripts/migrate_normalize_data.py
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client
from app.utils.normalizer import (
    normalize_category,
    normalize_state,
    normalize_city,
    normalize_title,
    normalize_money
)
import logging
from typing import Dict, Any, List
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL e SUPABASE_KEY são obrigatórios")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def normalize_property(prop: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza um imóvel.
    
    Returns:
        Dicionário com campos atualizados (apenas os que mudaram)
    """
    updates = {}
    
    # Normaliza categoria
    if prop.get('category'):
        normalized = normalize_category(prop['category'])
        if normalized != prop['category']:
            updates['category'] = normalized
    
    # Normaliza estado
    if prop.get('state'):
        normalized = normalize_state(prop['state'])
        if normalized and normalized != prop['state']:
            updates['state'] = normalized
    
    # Normaliza cidade
    if prop.get('city'):
        normalized = normalize_city(prop['city'])
        if normalized != prop['city']:
            updates['city'] = normalized
    
    # Normaliza título
    if prop.get('title'):
        normalized = normalize_title(prop['title'])
        if normalized != prop['title']:
            updates['title'] = normalized
    
    # Normaliza bairro (neighborhood)
    if prop.get('neighborhood'):
        # Aplica Title Case básico
        normalized = ' '.join(word.capitalize() for word in prop['neighborhood'].split())
        if normalized != prop['neighborhood']:
            updates['neighborhood'] = normalized
    
    # Marca como atualizado
    if updates:
        updates['updated_at'] = datetime.utcnow().isoformat()
    
    return updates

def get_all_properties(batch_size: int = 1000) -> List[Dict[str, Any]]:
    """
    Busca todos os imóveis do banco em batches.
    """
    all_properties = []
    offset = 0
    
    while True:
        logger.info(f"Fetching properties {offset} to {offset + batch_size}...")
        
        response = supabase.table('properties') \
            .select('id, category, state, city, title, neighborhood') \
            .range(offset, offset + batch_size - 1) \
            .execute()
        
        if not response.data:
            break
        
        all_properties.extend(response.data)
        offset += batch_size
        
        if len(response.data) < batch_size:
            break
    
    logger.info(f"Total properties fetched: {len(all_properties)}")
    return all_properties

def update_property(prop_id: str, updates: Dict[str, Any]) -> bool:
    """
    Atualiza um imóvel no banco.
    """
    try:
        supabase.table('properties') \
            .update(updates) \
            .eq('id', prop_id) \
            .execute()
        return True
    except Exception as e:
        logger.error(f"Error updating property {prop_id}: {e}")
        return False

def run_migration():
    """
    Executa a migração de normalização.
    """
    logger.info("=" * 60)
    logger.info("MIGRAÇÃO DE NORMALIZAÇÃO DE DADOS")
    logger.info("=" * 60)
    
    # Busca todos os imóveis
    properties = get_all_properties()
    
    if not properties:
        logger.warning("Nenhum imóvel encontrado no banco")
        return
    
    # Estatísticas
    stats = {
        'total': len(properties),
        'updated': 0,
        'skipped': 0,
        'errors': 0,
        'fields_updated': {
            'category': 0,
            'state': 0,
            'city': 0,
            'title': 0,
            'neighborhood': 0
        }
    }
    
    # Processa cada imóvel
    for i, prop in enumerate(properties, 1):
        if i % 100 == 0:
            logger.info(f"Processing {i}/{stats['total']}...")
        
        updates = normalize_property(prop)
        
        if updates:
            # Conta campos atualizados
            for field in ['category', 'state', 'city', 'title', 'neighborhood']:
                if field in updates:
                    stats['fields_updated'][field] += 1
            
            # Atualiza no banco
            if update_property(prop['id'], updates):
                stats['updated'] += 1
            else:
                stats['errors'] += 1
        else:
            stats['skipped'] += 1
    
    # Relatório final
    logger.info("\n" + "=" * 60)
    logger.info("RELATÓRIO DA MIGRAÇÃO")
    logger.info("=" * 60)
    logger.info(f"Total de imóveis: {stats['total']}")
    logger.info(f"Atualizados: {stats['updated']}")
    logger.info(f"Sem alteração: {stats['skipped']}")
    logger.info(f"Erros: {stats['errors']}")
    logger.info("\nCampos atualizados:")
    for field, count in stats['fields_updated'].items():
        logger.info(f"  - {field}: {count}")
    logger.info("=" * 60)

def show_current_stats():
    """
    Mostra estatísticas atuais dos dados.
    """
    logger.info("\n" + "=" * 60)
    logger.info("ESTATÍSTICAS ATUAIS DOS DADOS")
    logger.info("=" * 60)
    
    # Categorias únicas
    response = supabase.table('properties') \
        .select('category') \
        .execute()
    
    categories = {}
    for row in response.data:
        cat = row.get('category', 'NULL')
        categories[cat] = categories.get(cat, 0) + 1
    
    logger.info("\nCategorias:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
        logger.info(f"  - {cat}: {count}")
    
    # Estados únicos
    response = supabase.table('properties') \
        .select('state') \
        .execute()
    
    states = {}
    for row in response.data:
        state = row.get('state', 'NULL')
        states[state] = states.get(state, 0) + 1
    
    logger.info("\nEstados (top 10):")
    for state, count in sorted(states.items(), key=lambda x: -x[1])[:10]:
        logger.info(f"  - {state}: {count}")
    
    # Cidades únicas (amostra)
    response = supabase.table('properties') \
        .select('city') \
        .limit(1000) \
        .execute()
    
    cities = {}
    for row in response.data:
        city = row.get('city', 'NULL')
        cities[city] = cities.get(city, 0) + 1
    
    logger.info("\nCidades (top 10):")
    for city, count in sorted(cities.items(), key=lambda x: -x[1])[:10]:
        logger.info(f"  - {city}: {count}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migração de normalização de dados')
    parser.add_argument('--stats', action='store_true', help='Mostrar estatísticas atuais')
    parser.add_argument('--dry-run', action='store_true', help='Simular sem alterar dados')
    args = parser.parse_args()
    
    if args.stats:
        show_current_stats()
    elif args.dry_run:
        logger.info("MODO DRY-RUN - Nenhum dado será alterado")
        properties = get_all_properties(batch_size=100)
        
        changes = 0
        for prop in properties[:100]:  # Amostra de 100
            updates = normalize_property(prop)
            if updates:
                changes += 1
                logger.info(f"Would update {prop['id']}: {updates}")
        
        logger.info(f"\nTotal que seria atualizado: ~{changes}%")
    else:
        run_migration()

