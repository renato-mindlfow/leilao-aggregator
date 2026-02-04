"""
Endpoints para estatisticas de leiloeiros.
API de somente leitura para visualizacao de dados.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from collections import Counter
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auctioneers", tags=["auctioneers"])

# Lazy import do Supabase para evitar erro se variaveis nao estiverem configuradas
_supabase = None

def get_supabase():
    global _supabase
    if _supabase is None:
        from supabase import create_client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
        if not url or not key:
            raise HTTPException(status_code=500, detail="Supabase not configured")
        _supabase = create_client(url, key)
    return _supabase


@router.get("/stats")
async def get_auctioneers_stats() -> Dict[str, Any]:
    """
    Retorna estatisticas de todos os leiloeiros.
    Agrega dados da tabela properties por leiloeiro.
    """
    try:
        supabase = get_supabase()

        # Buscar todos os imoveis com informacoes do leiloeiro
        result = supabase.table('properties').select(
            'auctioneer_id, auctioneer_name, auctioneer_url, is_active, created_at, updated_at'
        ).execute()

        # Agregar por leiloeiro
        leiloeiros = {}

        for prop in result.data:
            auctioneer_id = prop.get('auctioneer_id') or 'unknown'
            auctioneer_name = prop.get('auctioneer_name') or auctioneer_id

            if auctioneer_id not in leiloeiros:
                leiloeiros[auctioneer_id] = {
                    'id': auctioneer_id,
                    'name': auctioneer_name,
                    'url': prop.get('auctioneer_url'),
                    'total_properties': 0,
                    'active_properties': 0,
                    'last_update': None,
                }

            leiloeiros[auctioneer_id]['total_properties'] += 1

            if prop.get('is_active'):
                leiloeiros[auctioneer_id]['active_properties'] += 1

            # Atualizar nome se for mais descritivo
            if prop.get('auctioneer_name') and len(str(prop.get('auctioneer_name'))) > len(str(leiloeiros[auctioneer_id]['name'])):
                leiloeiros[auctioneer_id]['name'] = prop.get('auctioneer_name')

            # Atualizar ultima atualizacao
            updated = prop.get('updated_at') or prop.get('created_at')
            if updated:
                if not leiloeiros[auctioneer_id]['last_update'] or updated > leiloeiros[auctioneer_id]['last_update']:
                    leiloeiros[auctioneer_id]['last_update'] = updated

        # Converter para lista ordenada por total
        lista = sorted(
            leiloeiros.values(),
            key=lambda x: x['total_properties'],
            reverse=True
        )

        # Estatisticas gerais
        total_leiloeiros = len(lista)
        total_imoveis = sum(l['total_properties'] for l in lista)
        total_ativos = sum(l['active_properties'] for l in lista)

        return {
            'summary': {
                'total_auctioneers': total_leiloeiros,
                'total_properties': total_imoveis,
                'active_properties': total_ativos,
            },
            'auctioneers': lista
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar estatisticas de leiloeiros: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_auctioneers() -> List[Dict[str, Any]]:
    """
    Lista simples de leiloeiros com contagem de imoveis.
    """
    try:
        stats = await get_auctioneers_stats()
        return stats['auctioneers']

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar leiloeiros: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_auctioneers() -> List[Dict[str, Any]]:
    """
    Lista de leiloeiros no formato esperado pelo AdminDashboard.
    Retorna lista com: id, name, website, is_active, property_count, scrape_status, last_scrape
    """
    try:
        supabase = get_supabase()

        # Buscar todos os imoveis com informacoes do leiloeiro
        result = supabase.table('properties').select(
            'auctioneer_id, auctioneer_name, auctioneer_url, is_active, updated_at'
        ).execute()

        # Agregar por leiloeiro
        leiloeiros = {}

        for prop in result.data:
            auctioneer_id = prop.get('auctioneer_id') or 'unknown'
            auctioneer_name = prop.get('auctioneer_name') or auctioneer_id

            if auctioneer_id not in leiloeiros:
                leiloeiros[auctioneer_id] = {
                    'id': auctioneer_id,
                    'name': auctioneer_name,
                    'website': prop.get('auctioneer_url'),
                    'is_active': True,
                    'property_count': 0,
                    'scrape_status': 'ok',
                    'scrape_error': None,
                    'last_scrape': None,
                }

            leiloeiros[auctioneer_id]['property_count'] += 1

            # Atualizar nome se for mais descritivo
            if prop.get('auctioneer_name') and len(str(prop.get('auctioneer_name'))) > len(str(leiloeiros[auctioneer_id]['name'])):
                leiloeiros[auctioneer_id]['name'] = prop.get('auctioneer_name')

            # Atualizar ultima atualizacao
            updated = prop.get('updated_at')
            if updated:
                if not leiloeiros[auctioneer_id]['last_scrape'] or updated > leiloeiros[auctioneer_id]['last_scrape']:
                    leiloeiros[auctioneer_id]['last_scrape'] = updated

        # Converter para lista ordenada por property_count
        lista = sorted(
            leiloeiros.values(),
            key=lambda x: x['property_count'],
            reverse=True
        )

        return lista

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar leiloeiros: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{auctioneer_id}")
async def get_auctioneer_detail(auctioneer_id: str) -> Dict[str, Any]:
    """
    Retorna detalhes de um leiloeiro especifico.
    """
    try:
        supabase = get_supabase()

        # Buscar imoveis deste leiloeiro
        result = supabase.table('properties').select(
            'id, title, city, state, category, is_active, first_auction_value, created_at, updated_at'
        ).eq('auctioneer_id', auctioneer_id).limit(100).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail=f"Leiloeiro '{auctioneer_id}' nao encontrado")

        # Calcular estatisticas
        total = len(result.data)
        ativos = sum(1 for p in result.data if p.get('is_active'))

        # Categorias
        categorias = Counter(p.get('category') for p in result.data if p.get('category'))

        # Estados
        estados = Counter(p.get('state') for p in result.data if p.get('state'))

        return {
            'id': auctioneer_id,
            'total_properties': total,
            'active_properties': ativos,
            'categories': dict(categorias.most_common(10)),
            'states': dict(estados.most_common(10)),
            'sample_properties': result.data[:10]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do leiloeiro {auctioneer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
