"""
API de Propriedades com ordenação, filtros e paginação.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import os
from supabase import create_client, Client

router = APIRouter(prefix="/api/properties", tags=["properties"])

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

# Inicializa cliente Supabase apenas se as variáveis estiverem configuradas
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao inicializar cliente Supabase: {e}")
        supabase = None
else:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("SUPABASE_URL ou SUPABASE_KEY não configurados. API pode não funcionar.")

# Modelos de resposta
class PropertyResponse(BaseModel):
    id: str
    title: str
    category: str
    auction_type: str
    state: str
    city: str
    neighborhood: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    area_total: Optional[float] = None
    evaluation_value: Optional[float] = None
    first_auction_value: Optional[float] = None
    first_auction_date: Optional[datetime] = None
    second_auction_value: Optional[float] = None
    second_auction_date: Optional[datetime] = None
    discount_percentage: Optional[float] = None
    image_url: Optional[str] = None
    source_url: str
    auctioneer_name: Optional[str] = None
    created_at: Optional[datetime] = None

class PaginatedResponse(BaseModel):
    data: List[PropertyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class StatsResponse(BaseModel):
    total_properties: int
    total_active: int
    by_category: dict
    by_state: dict
    by_auction_type: dict
    avg_discount: Optional[float]
    last_update: Optional[datetime]

# Campos válidos para ordenação
VALID_SORT_FIELDS = [
    'first_auction_date',
    'second_auction_date',
    'first_auction_value',
    'second_auction_value',
    'evaluation_value',
    'discount_percentage',
    'created_at',
    'city',
    'state'
]

# Categorias válidas
VALID_CATEGORIES = ['Apartamento', 'Casa', 'Terreno', 'Comercial', 'Outros']

@router.get("", response_model=PaginatedResponse)
async def list_properties(
    # Paginação
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    
    # Filtros
    category: Optional[str] = Query(None, description="Filtrar por categoria"),
    state: Optional[str] = Query(None, description="Filtrar por estado (sigla)"),
    city: Optional[str] = Query(None, description="Filtrar por cidade"),
    auction_type: Optional[str] = Query(None, description="Filtrar por tipo de leilão"),
    min_value: Optional[float] = Query(None, description="Valor mínimo"),
    max_value: Optional[float] = Query(None, description="Valor máximo"),
    min_discount: Optional[float] = Query(None, description="Desconto mínimo (%)"),
    auctioneer_id: Optional[str] = Query(None, description="Filtrar por leiloeiro"),
    
    # Ordenação
    sort_by: str = Query('first_auction_date', description="Campo para ordenação"),
    order: str = Query('desc', description="Direção: asc ou desc"),
    
    # Busca
    search: Optional[str] = Query(None, description="Busca no título")
):
    """
    Lista propriedades com filtros, ordenação e paginação.
    """
    
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase não configurado. Configure SUPABASE_URL e SUPABASE_KEY."
        )
    
    # Valida campo de ordenação
    if sort_by not in VALID_SORT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Campo de ordenação inválido. Válidos: {VALID_SORT_FIELDS}"
        )
    
    # Valida direção
    if order.lower() not in ['asc', 'desc']:
        raise HTTPException(
            status_code=400,
            detail="Direção de ordenação deve ser 'asc' ou 'desc'"
        )
    
    # Monta query base
    query = supabase.table('properties').select(
        '*',
        count='exact'
    )
    
    # Aplica filtros
    query = query.eq('is_active', True)
    
    if category:
        # Normaliza categoria
        from app.utils.normalizer import normalize_category
        normalized_cat = normalize_category(category)
        query = query.eq('category', normalized_cat)
    
    if state:
        # Normaliza estado
        from app.utils.normalizer import normalize_state
        normalized_state = normalize_state(state)
        if normalized_state:
            query = query.eq('state', normalized_state)
    
    if city:
        query = query.ilike('city', f'%{city}%')
    
    if auction_type:
        query = query.eq('auction_type', auction_type)
    
    if auctioneer_id:
        query = query.eq('auctioneer_id', auctioneer_id)
    
    if min_value is not None:
        query = query.gte('first_auction_value', min_value)
    
    if max_value is not None:
        query = query.lte('first_auction_value', max_value)
    
    if min_discount is not None:
        query = query.gte('discount_percentage', min_discount)
    
    if search:
        query = query.ilike('title', f'%{search}%')
    
    # Aplica ordenação
    query = query.order(sort_by, desc=(order.lower() == 'desc'))
    
    # Aplica paginação
    offset = (page - 1) * page_size
    query = query.range(offset, offset + page_size - 1)
    
    # Executa query
    response = query.execute()
    
    # Calcula total de páginas
    total = response.count or 0
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    return PaginatedResponse(
        data=response.data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Retorna estatísticas gerais das propriedades.
    """
    
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase não configurado. Configure SUPABASE_URL e SUPABASE_KEY."
        )
    
    # Total de propriedades
    total_response = supabase.table('properties') \
        .select('id', count='exact') \
        .execute()
    total = total_response.count or 0
    
    # Total de ativos
    active_response = supabase.table('properties') \
        .select('id', count='exact') \
        .eq('is_active', True) \
        .execute()
    total_active = active_response.count or 0
    
    # Por categoria
    cat_response = supabase.table('properties') \
        .select('category') \
        .eq('is_active', True) \
        .execute()
    
    by_category = {}
    for row in cat_response.data:
        cat = row.get('category', 'Outros')
        by_category[cat] = by_category.get(cat, 0) + 1
    
    # Por estado
    state_response = supabase.table('properties') \
        .select('state') \
        .eq('is_active', True) \
        .execute()
    
    by_state = {}
    for row in state_response.data:
        state = row.get('state', 'N/A')
        by_state[state] = by_state.get(state, 0) + 1
    
    # Por tipo de leilão
    type_response = supabase.table('properties') \
        .select('auction_type') \
        .eq('is_active', True) \
        .execute()
    
    by_auction_type = {}
    for row in type_response.data:
        atype = row.get('auction_type', 'N/A')
        by_auction_type[atype] = by_auction_type.get(atype, 0) + 1
    
    # Desconto médio
    discount_response = supabase.table('properties') \
        .select('discount_percentage') \
        .eq('is_active', True) \
        .not_.is_('discount_percentage', 'null') \
        .execute()
    
    discounts = [r['discount_percentage'] for r in discount_response.data if r.get('discount_percentage')]
    avg_discount = sum(discounts) / len(discounts) if discounts else None
    
    # Última atualização
    last_update_response = supabase.table('properties') \
        .select('updated_at') \
        .order('updated_at', desc=True) \
        .limit(1) \
        .execute()
    
    last_update = None
    if last_update_response.data:
        last_update = last_update_response.data[0].get('updated_at')
    
    return StatsResponse(
        total_properties=total,
        total_active=total_active,
        by_category=by_category,
        by_state=by_state,
        by_auction_type=by_auction_type,
        avg_discount=avg_discount,
        last_update=last_update
    )

@router.get("/categories")
async def list_categories():
    """
    Lista todas as categorias disponíveis.
    """
    return {"categories": VALID_CATEGORIES}

@router.get("/states")
async def list_states():
    """
    Lista todos os estados com propriedades.
    """
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase não configurado. Configure SUPABASE_URL e SUPABASE_KEY."
        )
    
    response = supabase.table('properties') \
        .select('state') \
        .eq('is_active', True) \
        .execute()
    
    states = set()
    for row in response.data:
        if row.get('state'):
            states.add(row['state'])
    
    return {"states": sorted(list(states))}

@router.get("/cities")
async def list_cities(state: Optional[str] = Query(None, description="Filtrar por estado")):
    """
    Lista todas as cidades com propriedades.
    """
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase não configurado. Configure SUPABASE_URL e SUPABASE_KEY."
        )
    
    query = supabase.table('properties') \
        .select('city, state') \
        .eq('is_active', True)
    
    if state:
        from app.utils.normalizer import normalize_state
        normalized_state = normalize_state(state)
        if normalized_state:
            query = query.eq('state', normalized_state)
    
    response = query.execute()
    
    cities = set()
    for row in response.data:
        if row.get('city'):
            cities.add(row['city'])
    
    return {"cities": sorted(list(cities))}

@router.get("/{property_id}")
async def get_property(property_id: str):
    """
    Retorna detalhes de uma propriedade específica.
    """
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase não configurado. Configure SUPABASE_URL e SUPABASE_KEY."
        )
    
    response = supabase.table('properties') \
        .select('*') \
        .eq('id', property_id) \
        .single() \
        .execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada")
    
    return response.data

