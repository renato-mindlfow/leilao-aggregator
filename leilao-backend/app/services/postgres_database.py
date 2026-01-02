"""
PostgreSQL database for the auction aggregator using Supabase.
Provides persistent storage that survives restarts and works with multiple instances.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from app.models.property import Property, PropertyCreate, PropertyFilter, PropertyCategory, AuctionType
from app.models.auctioneer import Auctioneer, AuctioneerCreate
from app.utils.image_blacklist import clean_image_url, get_source_url_or_fallback
from app.utils.text_normalizer import normalize_city_name, normalize_neighborhood

# Carregar .env ANTES de qualquer outra coisa
load_dotenv()

logger = logging.getLogger(__name__)

# Database URL from environment - NO FALLBACK, must be in .env
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não configurada no .env")

# SQL to create tables
CREATE_PROPERTIES_TABLE = """
CREATE TABLE IF NOT EXISTS properties (
    id VARCHAR(255) PRIMARY KEY,
    title TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    auction_type VARCHAR(50) NOT NULL,
    state VARCHAR(2) NOT NULL,
    city VARCHAR(255) NOT NULL,
    neighborhood VARCHAR(255),
    address TEXT,
    description TEXT,
    area_total FLOAT,
    area_privativa FLOAT,
    evaluation_value FLOAT,
    first_auction_value FLOAT,
    first_auction_date TIMESTAMP,
    second_auction_value FLOAT,
    second_auction_date TIMESTAMP,
    discount_percentage FLOAT,
    image_url TEXT,
    auctioneer_id VARCHAR(255) NOT NULL,
    source_url TEXT NOT NULL,
    accepts_financing BOOLEAN,
    accepts_fgts BOOLEAN,
    accepts_installments BOOLEAN,
    occupation_status VARCHAR(255),
    pending_debts TEXT,
    auctioneer_name VARCHAR(255),
    auctioneer_url TEXT,
    source VARCHAR(255),
    latitude FLOAT,
    longitude FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dedup_key VARCHAR(255),
    is_duplicate BOOLEAN DEFAULT FALSE,
    original_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    last_seen_at TIMESTAMP,
    deactivated_at TIMESTAMP,
    value_changed_at TIMESTAMP,
    previous_first_auction_value FLOAT,
    previous_second_auction_value FLOAT
);

CREATE INDEX IF NOT EXISTS idx_properties_state ON properties(state);
CREATE INDEX IF NOT EXISTS idx_properties_city ON properties(city);
CREATE INDEX IF NOT EXISTS idx_properties_category ON properties(category);
CREATE INDEX IF NOT EXISTS idx_properties_auctioneer_id ON properties(auctioneer_id);
CREATE INDEX IF NOT EXISTS idx_properties_is_active ON properties(is_active);
CREATE INDEX IF NOT EXISTS idx_properties_is_duplicate ON properties(is_duplicate);
CREATE INDEX IF NOT EXISTS idx_properties_dedup_key ON properties(dedup_key);
CREATE INDEX IF NOT EXISTS idx_properties_source_url ON properties(source_url);
"""

CREATE_AUCTIONEERS_TABLE = """
CREATE TABLE IF NOT EXISTS auctioneers (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    website TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    property_count INTEGER DEFAULT 0,
    scrape_status VARCHAR(50) DEFAULT 'pending',
    scrape_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scrape TIMESTAMP
);
"""


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        query_params = sorted(parse_qsl(parsed.query))
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip('/'),
            parsed.params,
            urlencode(query_params),
            ''
        ))
        return normalized
    except Exception:
        return url.lower().strip()


class PostgresDatabase:
    def __init__(self):
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        self._init_db()
        
        # Cache for auctioneers (small dataset, OK to keep in memory)
        self._auctioneers_cache: Dict[str, Auctioneer] = {}
        self._load_auctioneers_cache()
        
        logger.info("PostgreSQL database initialized")
    
    def _get_connection(self):
        """Get a database connection."""
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    
    def _init_db(self):
        """Initialize database tables."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(CREATE_PROPERTIES_TABLE)
                    cur.execute(CREATE_AUCTIONEERS_TABLE)
                conn.commit()
            logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def _load_auctioneers_cache(self):
        """Load auctioneers into memory cache."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM auctioneers")
                    rows = cur.fetchall()
                    for row in rows:
                        auctioneer = self._row_to_auctioneer(row)
                        self._auctioneers_cache[auctioneer.id] = auctioneer
            logger.info(f"Loaded {len(self._auctioneers_cache)} auctioneers into cache")
        except Exception as e:
            logger.error(f"Error loading auctioneers cache: {e}")
    
    def _row_to_property(self, row: dict) -> Property:
        """Convert database row to Property model."""
        return Property(
            id=row['id'],
            title=row['title'],
            category=PropertyCategory(row['category']) if row['category'] else PropertyCategory.OUTRO,
            auction_type=AuctionType(row['auction_type']) if row['auction_type'] else AuctionType.OUTROS,
            state=row['state'],
            city=row['city'],
            neighborhood=row.get('neighborhood'),
            address=row.get('address'),
            description=row.get('description'),
            area_total=row.get('area_total'),
            area_privativa=row.get('area_privativa'),
            evaluation_value=row.get('evaluation_value'),
            first_auction_value=row.get('first_auction_value'),
            first_auction_date=row.get('first_auction_date'),
            second_auction_value=row.get('second_auction_value'),
            second_auction_date=row.get('second_auction_date'),
            discount_percentage=row.get('discount_percentage'),
            image_url=row.get('image_url'),
            auctioneer_id=row['auctioneer_id'],
            source_url=row['source_url'],
            accepts_financing=row.get('accepts_financing'),
            accepts_fgts=row.get('accepts_fgts'),
            accepts_installments=row.get('accepts_installments'),
            occupation_status=row.get('occupation_status'),
            pending_debts=row.get('pending_debts'),
            auctioneer_name=row.get('auctioneer_name'),
            auctioneer_url=row.get('auctioneer_url'),
            source=row.get('source'),
            latitude=row.get('latitude'),
            longitude=row.get('longitude'),
            created_at=row.get('created_at') or datetime.utcnow(),
            updated_at=row.get('updated_at') or datetime.utcnow(),
            dedup_key=row.get('dedup_key'),
            is_duplicate=row.get('is_duplicate', False),
            original_id=row.get('original_id'),
            is_active=row.get('is_active', True),
            last_seen_at=row.get('last_seen_at'),
            deactivated_at=row.get('deactivated_at'),
            value_changed_at=row.get('value_changed_at'),
            previous_first_auction_value=row.get('previous_first_auction_value'),
            previous_second_auction_value=row.get('previous_second_auction_value')
        )
    
    def _row_to_auctioneer(self, row: dict) -> Auctioneer:
        """Convert database row to Auctioneer model."""
        return Auctioneer(
            id=row['id'],
            name=row['name'],
            website=row.get('website'),
            is_active=row.get('is_active', True),
            property_count=row.get('property_count', 0),
            scrape_status=row.get('scrape_status') or "pending",
            scrape_error=row.get('scrape_error'),
            created_at=row.get('created_at') or datetime.utcnow(),
            updated_at=row.get('updated_at') or datetime.utcnow(),
            last_scrape=row.get('last_scrape')
        )
    
    # Property methods
    def add_property(self, prop: Property, upsert: bool = True) -> Property:
        """Add or update a property."""
        # TODO: Implementar Layer de Auditoria de Qualidade IA antes do commit final
        # Ver documentação: ESTRATEGIA_AUDITORIA_QUALIDADE_IA.md
        # Validações necessárias:
        # - Datas de leilão lógicas e cronológicas
        # - Valores de 1ª e 2ª praça respeitando regra de desconto
        # - Campo 'Estado' não pode ser 'XX' ou inválido
        
        # Limpar e validar image_url
        prop.image_url = clean_image_url(prop.image_url)
        
        # Validar e limpar source_url
        prop.source_url = get_source_url_or_fallback(prop.source_url, prop.auctioneer_url)
        
        # Normalizar cidade e bairro
        prop.city = normalize_city_name(prop.city)
        prop.neighborhood = normalize_neighborhood(prop.neighborhood)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    if upsert:
                        # Use INSERT ... ON CONFLICT for upsert
                        cur.execute("""
                            INSERT INTO properties (
                                id, title, category, auction_type, state, city, neighborhood, address,
                                description, area_total, area_privativa, evaluation_value,
                                first_auction_value, first_auction_date, second_auction_value, second_auction_date,
                                discount_percentage, image_url, auctioneer_id, source_url,
                                accepts_financing, accepts_fgts, accepts_installments, occupation_status,
                                pending_debts, auctioneer_name, auctioneer_url, source, latitude, longitude,
                                created_at, updated_at, dedup_key, is_duplicate, original_id,
                                is_active, last_seen_at, deactivated_at, value_changed_at,
                                previous_first_auction_value, previous_second_auction_value
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            ON CONFLICT (id) DO UPDATE SET
                                title = EXCLUDED.title,
                                category = EXCLUDED.category,
                                auction_type = EXCLUDED.auction_type,
                                state = EXCLUDED.state,
                                city = EXCLUDED.city,
                                neighborhood = EXCLUDED.neighborhood,
                                address = EXCLUDED.address,
                                description = EXCLUDED.description,
                                area_total = EXCLUDED.area_total,
                                area_privativa = EXCLUDED.area_privativa,
                                evaluation_value = EXCLUDED.evaluation_value,
                                first_auction_value = EXCLUDED.first_auction_value,
                                first_auction_date = EXCLUDED.first_auction_date,
                                second_auction_value = EXCLUDED.second_auction_value,
                                second_auction_date = EXCLUDED.second_auction_date,
                                discount_percentage = EXCLUDED.discount_percentage,
                                image_url = EXCLUDED.image_url,
                                source_url = EXCLUDED.source_url,
                                accepts_financing = EXCLUDED.accepts_financing,
                                accepts_fgts = EXCLUDED.accepts_fgts,
                                accepts_installments = EXCLUDED.accepts_installments,
                                occupation_status = EXCLUDED.occupation_status,
                                pending_debts = EXCLUDED.pending_debts,
                                auctioneer_name = EXCLUDED.auctioneer_name,
                                auctioneer_url = EXCLUDED.auctioneer_url,
                                source = EXCLUDED.source,
                                latitude = EXCLUDED.latitude,
                                longitude = EXCLUDED.longitude,
                                updated_at = CURRENT_TIMESTAMP,
                                is_active = EXCLUDED.is_active,
                                last_seen_at = EXCLUDED.last_seen_at
                        """, (
                            prop.id, prop.title, prop.category.value if prop.category else None,
                            prop.auction_type.value if prop.auction_type else None,
                            prop.state, prop.city, prop.neighborhood, prop.address,
                            prop.description, prop.area_total, prop.area_privativa, prop.evaluation_value,
                            prop.first_auction_value, prop.first_auction_date,
                            prop.second_auction_value, prop.second_auction_date,
                            prop.discount_percentage, prop.image_url, prop.auctioneer_id, prop.source_url,
                            prop.accepts_financing, prop.accepts_fgts, prop.accepts_installments,
                            prop.occupation_status, prop.pending_debts, prop.auctioneer_name,
                            prop.auctioneer_url, prop.source, prop.latitude, prop.longitude,
                            prop.created_at, prop.updated_at, prop.dedup_key, prop.is_duplicate,
                            prop.original_id, prop.is_active, prop.last_seen_at, prop.deactivated_at,
                            prop.value_changed_at, prop.previous_first_auction_value,
                            prop.previous_second_auction_value
                        ))
                    else:
                        # Simple insert
                        cur.execute("""
                            INSERT INTO properties (
                                id, title, category, auction_type, state, city, neighborhood, address,
                                description, area_total, area_privativa, evaluation_value,
                                first_auction_value, first_auction_date, second_auction_value, second_auction_date,
                                discount_percentage, image_url, auctioneer_id, source_url,
                                accepts_financing, accepts_fgts, accepts_installments, occupation_status,
                                pending_debts, auctioneer_name, auctioneer_url, source, latitude, longitude,
                                created_at, updated_at, dedup_key, is_duplicate, original_id,
                                is_active, last_seen_at, deactivated_at, value_changed_at,
                                previous_first_auction_value, previous_second_auction_value
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """, (
                            prop.id, prop.title, prop.category.value if prop.category else None,
                            prop.auction_type.value if prop.auction_type else None,
                            prop.state, prop.city, prop.neighborhood, prop.address,
                            prop.description, prop.area_total, prop.area_privativa, prop.evaluation_value,
                            prop.first_auction_value, prop.first_auction_date,
                            prop.second_auction_value, prop.second_auction_date,
                            prop.discount_percentage, prop.image_url, prop.auctioneer_id, prop.source_url,
                            prop.accepts_financing, prop.accepts_fgts, prop.accepts_installments,
                            prop.occupation_status, prop.pending_debts, prop.auctioneer_name,
                            prop.auctioneer_url, prop.source, prop.latitude, prop.longitude,
                            prop.created_at, prop.updated_at, prop.dedup_key, prop.is_duplicate,
                            prop.original_id, prop.is_active, prop.last_seen_at, prop.deactivated_at,
                            prop.value_changed_at, prop.previous_first_auction_value,
                            prop.previous_second_auction_value
                        ))
                conn.commit()
            return prop
        except Exception as e:
            logger.error(f"Error adding property {prop.id}: {e}")
            raise
    
    def get_property(self, prop_id: str) -> Optional[Property]:
        """Get a property by ID."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM properties WHERE id = %s", (prop_id,))
                    row = cur.fetchone()
                    if row:
                        return self._row_to_property(row)
            return None
        except Exception as e:
            logger.error(f"Error getting property {prop_id}: {e}")
            return None
    
    def get_properties(
        self,
        filters: Optional[PropertyFilter] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Property], int]:
        """Get properties with filtering and pagination."""
        try:
            conditions = []
            params = []
            
            # Always exclude duplicates unless explicitly requested
            if filters is None or not filters.include_duplicates:
                conditions.append("is_duplicate = FALSE")
            
            if filters:
                if filters.state:
                    conditions.append("state = %s")
                    params.append(filters.state)
                if filters.city:
                    conditions.append("city = %s")
                    params.append(filters.city)
                if filters.neighborhood:
                    conditions.append("neighborhood ILIKE %s")
                    params.append(f"%{filters.neighborhood}%")
                if filters.category:
                    conditions.append("category = %s")
                    params.append(filters.category.value)
                if filters.auction_type:
                    conditions.append("auction_type = %s")
                    params.append(filters.auction_type.value)
                if filters.min_value is not None:
                    conditions.append("(first_auction_value >= %s OR second_auction_value >= %s)")
                    params.extend([filters.min_value, filters.min_value])
                if filters.max_value is not None:
                    conditions.append("(first_auction_value <= %s OR second_auction_value <= %s)")
                    params.extend([filters.max_value, filters.max_value])
                if filters.min_discount is not None:
                    conditions.append("discount_percentage >= %s")
                    params.append(filters.min_discount)
                if filters.auctioneer_id:
                    conditions.append("auctioneer_id = %s")
                    params.append(filters.auctioneer_id)
                if filters.search_term:
                    conditions.append("(title ILIKE %s OR description ILIKE %s OR address ILIKE %s)")
                    search = f"%{filters.search_term}%"
                    params.extend([search, search, search])
            
            # If sorting by discount_percentage, filter out NULLs and invalid values
            if sort_by == "discount_percentage":
                conditions.append("discount_percentage IS NOT NULL")
                conditions.append("discount_percentage > 0")
                conditions.append("discount_percentage <= 100")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Validate sort_by to prevent SQL injection
            valid_sort_columns = ["created_at", "updated_at", "first_auction_value", "second_auction_value", "discount_percentage", "state", "city"]
            if sort_by not in valid_sort_columns:
                sort_by = "created_at"
            sort_order = "DESC" if sort_order.lower() == "desc" else "ASC"
            
            # Add NULLS LAST for DESC, NULLS FIRST for ASC
            nulls_position = "NULLS LAST" if sort_order == "DESC" else "NULLS FIRST"
            
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Get total count
                    cur.execute(f"SELECT COUNT(*) as count FROM properties WHERE {where_clause}", params)
                    total = cur.fetchone()['count']
                    
                    # Get paginated results with NULLS positioning
                    cur.execute(
                        f"SELECT * FROM properties WHERE {where_clause} ORDER BY {sort_by} {sort_order} {nulls_position} LIMIT %s OFFSET %s",
                        params + [limit, skip]
                    )
                    rows = cur.fetchall()
                    properties = [self._row_to_property(row) for row in rows]
            
            return properties, total
        except Exception as e:
            logger.error(f"Error getting properties: {e}")
            return [], 0
    
    def get_property_count(self) -> int:
        """Get total property count."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as count FROM properties")
                    return cur.fetchone()['count']
        except Exception as e:
            logger.error(f"Error getting property count: {e}")
            return 0
    
    def get_unique_property_count(self) -> int:
        """Get count of non-duplicate properties."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as count FROM properties WHERE is_duplicate = FALSE")
                    return cur.fetchone()['count']
        except Exception as e:
            logger.error(f"Error getting unique property count: {e}")
            return 0
    
    def get_category_counts(self) -> Dict[str, int]:
        """Get property counts by category."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT category, COUNT(*) as count 
                        FROM properties 
                        WHERE is_duplicate = FALSE 
                        GROUP BY category
                    """)
                    rows = cur.fetchall()
                    return {row['category']: row['count'] for row in rows if row['category']}
        except Exception as e:
            logger.error(f"Error getting category counts: {e}")
            return {}
    
    def get_state_counts(self) -> Dict[str, int]:
        """Get property counts by state."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT state, COUNT(*) as count 
                        FROM properties 
                        WHERE is_duplicate = FALSE 
                        GROUP BY state
                        ORDER BY count DESC
                    """)
                    rows = cur.fetchall()
                    return {row['state']: row['count'] for row in rows if row['state']}
        except Exception as e:
            logger.error(f"Error getting state counts: {e}")
            return {}
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Total properties
                    cur.execute("SELECT COUNT(*) as count FROM properties")
                    total = cur.fetchone()['count']
                    
                    # Unique properties (non-duplicates)
                    cur.execute("SELECT COUNT(*) as count FROM properties WHERE is_duplicate = FALSE")
                    unique = cur.fetchone()['count']
                    
                    # Duplicates
                    duplicates = total - unique
                    
                    # Category counts
                    cur.execute("""
                        SELECT category, COUNT(*) as count 
                        FROM properties 
                        WHERE is_duplicate = FALSE
                        GROUP BY category
                        ORDER BY count DESC
                    """)
                    category_counts = {row['category']: row['count'] for row in cur.fetchall() if row['category']}
                    
                    # State counts
                    cur.execute("""
                        SELECT state, COUNT(*) as count 
                        FROM properties 
                        WHERE is_duplicate = FALSE
                        GROUP BY state
                        ORDER BY count DESC
                    """)
                    state_counts = {row['state']: row['count'] for row in cur.fetchall() if row['state']}
                    
                    # Auctioneer counts
                    total_auctioneers = len(self._auctioneers_cache)
                    active_auctioneers = len([a for a in self._auctioneers_cache.values() if a.is_active])
                    
                    return {
                        "total_properties": total,
                        "unique_properties": unique,
                        "duplicate_properties": duplicates,
                        "total_auctioneers": total_auctioneers,
                        "active_auctioneers": active_auctioneers,
                        "category_counts": category_counts,
                        "state_counts": state_counts
                    }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "total_properties": 0,
                "unique_properties": 0,
                "duplicate_properties": 0,
                "total_auctioneers": 0,
                "active_auctioneers": 0,
                "category_counts": {},
                "state_counts": {}
            }
    
    def delete_property(self, prop_id: str) -> bool:
        """Delete a property."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM properties WHERE id = %s", (prop_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting property {prop_id}: {e}")
            return False
    
    def save_to_disk(self):
        """No-op for PostgreSQL (data is already persisted)."""
        pass
    
    # Auctioneer methods
    def add_auctioneer(self, auctioneer: Auctioneer) -> Auctioneer:
        """Add or update an auctioneer."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO auctioneers (id, name, website, is_active, property_count, scrape_status, scrape_error, created_at, updated_at, last_scrape)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            website = EXCLUDED.website,
                            is_active = EXCLUDED.is_active,
                            property_count = EXCLUDED.property_count,
                            scrape_status = EXCLUDED.scrape_status,
                            scrape_error = EXCLUDED.scrape_error,
                            updated_at = CURRENT_TIMESTAMP,
                            last_scrape = EXCLUDED.last_scrape
                    """, (
                        auctioneer.id, auctioneer.name, auctioneer.website, auctioneer.is_active,
                        auctioneer.property_count, auctioneer.scrape_status, auctioneer.scrape_error,
                        auctioneer.created_at, auctioneer.updated_at, auctioneer.last_scrape
                    ))
                conn.commit()
            self._auctioneers_cache[auctioneer.id] = auctioneer
            return auctioneer
        except Exception as e:
            logger.error(f"Error adding auctioneer {auctioneer.id}: {e}")
            raise
    
    def get_auctioneer(self, auctioneer_id: str) -> Optional[Auctioneer]:
        """Get an auctioneer by ID."""
        return self._auctioneers_cache.get(auctioneer_id)
    
    def get_auctioneers(self) -> List[Auctioneer]:
        """Get all auctioneers."""
        return list(self._auctioneers_cache.values())
    
    def get_active_auctioneers(self) -> List[Auctioneer]:
        """Get active auctioneers."""
        return [a for a in self._auctioneers_cache.values() if a.is_active]
    
    def get_unique_states(self) -> List[str]:
        """Get list of unique states from non-duplicate properties."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT DISTINCT state FROM properties WHERE is_duplicate = FALSE AND state IS NOT NULL ORDER BY state")
                    return [row['state'] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Error getting unique states: {e}")
            return []
    
    def get_unique_cities(self, state: Optional[str] = None) -> List[str]:
        """Get list of unique cities, optionally filtered by state."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    if state:
                        cur.execute("SELECT DISTINCT city FROM properties WHERE is_duplicate = FALSE AND city IS NOT NULL AND LOWER(state) = LOWER(%s) ORDER BY city", (state,))
                    else:
                        cur.execute("SELECT DISTINCT city FROM properties WHERE is_duplicate = FALSE AND city IS NOT NULL ORDER BY city")
                    return [row['city'] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Error getting unique cities: {e}")
            return []
    
    def get_unique_neighborhoods(self, state: Optional[str] = None, city: Optional[str] = None) -> List[str]:
        """Get list of unique neighborhoods, optionally filtered by state and city."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    conditions = ["is_duplicate = FALSE", "neighborhood IS NOT NULL"]
                    params = []
                    if state:
                        conditions.append("LOWER(state) = LOWER(%s)")
                        params.append(state)
                    if city:
                        conditions.append("LOWER(city) = LOWER(%s)")
                        params.append(city)
                    where_clause = " AND ".join(conditions)
                    cur.execute(f"SELECT DISTINCT neighborhood FROM properties WHERE {where_clause} ORDER BY neighborhood", params)
                    return [row['neighborhood'] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Error getting unique neighborhoods: {e}")
            return []
    
    def get_properties_by_source(self, source: str, include_duplicates: bool = False) -> Tuple[List[Property], int]:
        """Get properties filtered by source."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    conditions = ["source = %s"]
                    if not include_duplicates:
                        conditions.append("is_duplicate = FALSE")
                    where_clause = " AND ".join(conditions)
                    cur.execute(f"SELECT COUNT(*) as count FROM properties WHERE {where_clause}", (source,))
                    count = cur.fetchone()['count']
                    return [], count
        except Exception as e:
            logger.error(f"Error getting properties by source: {e}")
            return [], 0
    
    @property
    def properties(self) -> Dict[str, Property]:
        """Property dict interface - WARNING: Returns empty dict to avoid OOM. Use get_properties() instead."""
        logger.warning("properties property accessed - this returns empty dict to avoid OOM. Use get_properties() instead.")
        return {}
    
    @property
    def auctioneers(self) -> Dict[str, Auctioneer]:
        """Auctioneer dict interface for compatibility."""
        return self._auctioneers_cache
    
    def get_auctioneer_by_website(self, website: str) -> Optional[Auctioneer]:
        """Get an auctioneer by website URL."""
        for auctioneer in self._auctioneers_cache.values():
            if auctioneer.website and website.lower() in auctioneer.website.lower():
                return auctioneer
        return None
    
    def update_auctioneer_scrape_status(
        self,
        auctioneer_id: str,
        status: str,
        error: Optional[str] = None,
        property_count: Optional[int] = None
    ) -> None:
        """Update auctioneer scrape status and optionally property count."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    update_fields = ["scrape_status = %s", "updated_at = CURRENT_TIMESTAMP"]
                    params = [status]
                    
                    if error is not None:
                        update_fields.append("scrape_error = %s")
                        params.append(error)
                    
                    if property_count is not None:
                        update_fields.append("property_count = %s")
                        params.append(property_count)
                    
                    update_fields.append("last_scrape = CURRENT_TIMESTAMP")
                    params.append(auctioneer_id)
                    
                    cur.execute(
                        f"UPDATE auctioneers SET {', '.join(update_fields)} WHERE id = %s",
                        params
                    )
                conn.commit()
            
            # Update cache
            if auctioneer_id in self._auctioneers_cache:
                self._auctioneers_cache[auctioneer_id].scrape_status = status
                if error is not None:
                    self._auctioneers_cache[auctioneer_id].scrape_error = error
                if property_count is not None:
                    self._auctioneers_cache[auctioneer_id].property_count = property_count
                self._auctioneers_cache[auctioneer_id].last_scrape = datetime.utcnow()
        except Exception as e:
            logger.error(f"Error updating auctioneer scrape status {auctioneer_id}: {e}")
            raise
    
    def get_auctioneer_property_count(self, auctioneer_id: str) -> int:
        """Get the count of properties for an auctioneer."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) as count FROM properties WHERE auctioneer_id = %s AND is_duplicate = FALSE",
                        (auctioneer_id,)
                    )
                    row = cur.fetchone()
                    return row['count'] if row else 0
        except Exception as e:
            logger.error(f"Error getting property count for auctioneer {auctioneer_id}: {e}")
            return 0


# Singleton instance
_postgres_db: Optional[PostgresDatabase] = None


def get_postgres_database() -> PostgresDatabase:
    """Get the singleton PostgreSQL database instance."""
    global _postgres_db
    if _postgres_db is None:
        _postgres_db = PostgresDatabase()
    return _postgres_db
