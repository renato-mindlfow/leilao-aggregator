"""
SQLite database for the auction aggregator.
Provides persistent storage that survives restarts and handles 28k+ properties efficiently.
"""

import sqlite3
import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from app.models.property import Property, PropertyCreate, PropertyFilter, PropertyCategory, AuctionType
from app.models.auctioneer import Auctioneer, AuctioneerCreate

logger = logging.getLogger(__name__)

# Database file path
DATA_DIR = os.environ.get("DATA_DIR", "/tmp/leilohub_data")
DB_FILE = os.path.join(DATA_DIR, "leilohub.db")


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication purposes."""
    if not url:
        return ""
    url = url.strip()
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        query_params = []
        for k, v in parse_qsl(parsed.query, keep_blank_values=True):
            if not k.lower().startswith("utm_"):
                query_params.append((k, v))
        query = urlencode(query_params, doseq=True)
        normalized = urlunparse((scheme, netloc, path, "", query, ""))
        return normalized
    except Exception:
        return url.lower().strip().rstrip("/")


class SQLiteDatabase:
    def __init__(self):
        # Ensure data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        # Cache for auctioneers (small dataset, OK to keep in memory)
        self._auctioneers_cache: Dict[str, Auctioneer] = {}
        self._load_auctioneers_cache()
        
        logger.info(f"SQLite database initialized at {DB_FILE}")
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper settings."""
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            # Properties table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS properties (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    auction_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    city TEXT NOT NULL,
                    neighborhood TEXT,
                    address TEXT,
                    description TEXT,
                    area_total REAL,
                    area_privativa REAL,
                    evaluation_value REAL,
                    first_auction_value REAL,
                    first_auction_date TEXT,
                    second_auction_value REAL,
                    second_auction_date TEXT,
                    discount_percentage REAL,
                    image_url TEXT,
                    auctioneer_id TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    accepts_financing INTEGER,
                    accepts_fgts INTEGER,
                    accepts_installments INTEGER,
                    occupation_status TEXT,
                    pending_debts TEXT,
                    auctioneer_name TEXT,
                    auctioneer_url TEXT,
                    source TEXT,
                    latitude REAL,
                    longitude REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    dedup_key TEXT,
                    is_duplicate INTEGER DEFAULT 0,
                    original_id TEXT,
                    is_active INTEGER DEFAULT 1,
                    last_seen_at TEXT,
                    deactivated_at TEXT,
                    value_changed_at TEXT,
                    previous_first_auction_value REAL,
                    previous_second_auction_value REAL,
                    normalized_url TEXT
                )
            """)
            
            # Create indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_properties_state ON properties(state)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_properties_city ON properties(city)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_properties_category ON properties(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_properties_auctioneer ON properties(auctioneer_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_properties_discount ON properties(discount_percentage)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_properties_normalized_url ON properties(normalized_url)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_properties_is_duplicate ON properties(is_duplicate)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_properties_is_active ON properties(is_active)")
            
            # Auctioneers table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS auctioneers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    website TEXT,
                    is_active INTEGER DEFAULT 1,
                    property_count INTEGER DEFAULT 0,
                    last_scrape_at TEXT,
                    scrape_status TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
            logger.info("Database tables initialized")
    
    def _load_auctioneers_cache(self):
        """Load auctioneers into memory cache."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM auctioneers")
            for row in cursor:
                auctioneer = self._row_to_auctioneer(row)
                self._auctioneers_cache[auctioneer.id] = auctioneer
        
        # Initialize default auctioneers if empty
        if not self._auctioneers_cache:
            self._initialize_default_auctioneers()
    
    def _initialize_default_auctioneers(self):
        """Initialize with default auctioneers."""
        now = datetime.utcnow()
        default_auctioneers = [
            ("caixa", "Caixa Economica Federal", "https://venda-imoveis.caixa.gov.br"),
            ("portal_zuk", "Portal Zuk", "https://www.portalzuk.com.br"),
            ("superbid", "Superbid", "https://www.superbid.net"),
            ("mega_leiloes", "Mega Leiloes", "https://www.megaleiloes.com.br"),
            ("leilao_vip", "Leilao VIP", "https://www.leilaovip.com.br"),
            ("inovaleilao", "Inova Leilao", "https://www.inovaleilao.com.br"),
            ("pestana_leiloes", "Pestana Leiloes", "https://www.pestanaleiloes.com.br"),
            ("silas_leiloeiro", "Silas Leiloeiro", "https://www.silasleiloeiro.lel.br"),
            ("roberto_fernandes", "Roberto Fernandes Leiloes", "https://www.robertofernandesleiloes.com.br"),
        ]
        
        with self._get_connection() as conn:
            for auc_id, name, website in default_auctioneers:
                conn.execute("""
                    INSERT OR IGNORE INTO auctioneers (id, name, website, is_active, property_count, created_at, updated_at)
                    VALUES (?, ?, ?, 1, 0, ?, ?)
                """, (auc_id, name, website, now.isoformat(), now.isoformat()))
                
                self._auctioneers_cache[auc_id] = Auctioneer(
                    id=auc_id,
                    name=name,
                    website=website,
                    is_active=True,
                    property_count=0,
                    created_at=now,
                    updated_at=now,
                )
            conn.commit()
        logger.info(f"Initialized {len(default_auctioneers)} default auctioneers")
    
    def _row_to_property(self, row: sqlite3.Row) -> Property:
        """Convert a database row to a Property object."""
        def parse_datetime(val):
            if val:
                try:
                    return datetime.fromisoformat(val)
                except:
                    return None
            return None
        
        def parse_bool(val):
            if val is None:
                return None
            return bool(val)
        
        return Property(
            id=row['id'],
            title=row['title'],
            category=PropertyCategory(row['category']),
            auction_type=AuctionType(row['auction_type']),
            state=row['state'],
            city=row['city'],
            neighborhood=row['neighborhood'],
            address=row['address'],
            description=row['description'],
            area_total=row['area_total'],
            area_privativa=row['area_privativa'],
            evaluation_value=row['evaluation_value'],
            first_auction_value=row['first_auction_value'],
            first_auction_date=parse_datetime(row['first_auction_date']),
            second_auction_value=row['second_auction_value'],
            second_auction_date=parse_datetime(row['second_auction_date']),
            discount_percentage=row['discount_percentage'],
            image_url=row['image_url'],
            auctioneer_id=row['auctioneer_id'],
            source_url=row['source_url'],
            accepts_financing=parse_bool(row['accepts_financing']),
            accepts_fgts=parse_bool(row['accepts_fgts']),
            accepts_installments=parse_bool(row['accepts_installments']),
            occupation_status=row['occupation_status'],
            pending_debts=row['pending_debts'],
            auctioneer_name=row['auctioneer_name'],
            auctioneer_url=row['auctioneer_url'],
            source=row['source'],
            latitude=row['latitude'],
            longitude=row['longitude'],
            created_at=parse_datetime(row['created_at']) or datetime.utcnow(),
            updated_at=parse_datetime(row['updated_at']) or datetime.utcnow(),
            dedup_key=row['dedup_key'],
            is_duplicate=bool(row['is_duplicate']),
            original_id=row['original_id'],
            is_active=bool(row['is_active']),
            last_seen_at=parse_datetime(row['last_seen_at']),
            deactivated_at=parse_datetime(row['deactivated_at']),
            value_changed_at=parse_datetime(row['value_changed_at']),
            previous_first_auction_value=row['previous_first_auction_value'],
            previous_second_auction_value=row['previous_second_auction_value'],
        )
    
    def _row_to_auctioneer(self, row: sqlite3.Row) -> Auctioneer:
        """Convert a database row to an Auctioneer object."""
        def parse_datetime(val):
            if val:
                try:
                    return datetime.fromisoformat(val)
                except:
                    return None
            return None
        
        return Auctioneer(
            id=row['id'],
            name=row['name'],
            website=row['website'],
            is_active=bool(row['is_active']),
            property_count=row['property_count'] or 0,
            last_scrape=parse_datetime(row['last_scrape_at']),
            scrape_status=row['scrape_status'] or "pending",
            created_at=parse_datetime(row['created_at']) or datetime.utcnow(),
            updated_at=parse_datetime(row['updated_at']) or datetime.utcnow(),
        )
    
    def _property_to_row(self, prop: Property) -> tuple:
        """Convert a Property object to database row values."""
        def format_datetime(dt):
            return dt.isoformat() if dt else None
        
        def format_bool(val):
            if val is None:
                return None
            return 1 if val else 0
        
        normalized_url = normalize_url(prop.source_url or prop.auctioneer_url or "")
        
        return (
            prop.id,
            prop.title,
            prop.category.value if isinstance(prop.category, PropertyCategory) else prop.category,
            prop.auction_type.value if isinstance(prop.auction_type, AuctionType) else prop.auction_type,
            prop.state,
            prop.city,
            prop.neighborhood,
            prop.address,
            prop.description,
            prop.area_total,
            prop.area_privativa,
            prop.evaluation_value,
            prop.first_auction_value,
            format_datetime(prop.first_auction_date),
            prop.second_auction_value,
            format_datetime(prop.second_auction_date),
            prop.discount_percentage,
            prop.image_url,
            prop.auctioneer_id,
            prop.source_url,
            format_bool(prop.accepts_financing),
            format_bool(prop.accepts_fgts),
            format_bool(prop.accepts_installments),
            prop.occupation_status,
            prop.pending_debts,
            prop.auctioneer_name,
            prop.auctioneer_url,
            prop.source,
            prop.latitude,
            prop.longitude,
            format_datetime(prop.created_at),
            format_datetime(prop.updated_at),
            prop.dedup_key,
            1 if prop.is_duplicate else 0,
            prop.original_id,
            1 if prop.is_active else 0,
            format_datetime(prop.last_seen_at),
            format_datetime(prop.deactivated_at),
            format_datetime(prop.value_changed_at),
            prop.previous_first_auction_value,
            prop.previous_second_auction_value,
            normalized_url,
        )
    
    # Property methods
    def get_property(self, property_id: str) -> Optional[Property]:
        """Get a property by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM properties WHERE id = ?", (property_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_property(row)
        return None
    
    def get_properties(
        self,
        filters: Optional[PropertyFilter] = None,
        skip: int = 0,
        limit: int = 18,
    ) -> Tuple[List[Property], int]:
        """Get properties with optional filtering and pagination."""
        conditions = []
        params = []
        
        if filters:
            if filters.state:
                conditions.append("LOWER(state) = LOWER(?)")
                params.append(filters.state)
            
            if filters.city:
                conditions.append("LOWER(city) = LOWER(?)")
                params.append(filters.city)
            
            if filters.neighborhood:
                conditions.append("LOWER(neighborhood) LIKE LOWER(?)")
                params.append(f"%{filters.neighborhood}%")
            
            if filters.category:
                conditions.append("category = ?")
                params.append(filters.category.value if isinstance(filters.category, PropertyCategory) else filters.category)
            
            if filters.auction_type:
                conditions.append("auction_type = ?")
                params.append(filters.auction_type.value if isinstance(filters.auction_type, AuctionType) else filters.auction_type)
            
            if filters.min_value:
                conditions.append("second_auction_value >= ?")
                params.append(filters.min_value)
            
            if filters.max_value:
                conditions.append("second_auction_value <= ?")
                params.append(filters.max_value)
            
            if filters.min_discount:
                conditions.append("discount_percentage >= ?")
                params.append(filters.min_discount)
            
            if filters.auctioneer_id:
                conditions.append("auctioneer_id = ?")
                params.append(filters.auctioneer_id)
            
            if filters.search_term:
                search_pattern = f"%{filters.search_term}%"
                conditions.append("(LOWER(title) LIKE LOWER(?) OR LOWER(description) LIKE LOWER(?) OR LOWER(address) LIKE LOWER(?) OR LOWER(city) LIKE LOWER(?))")
                params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
            
            if not filters.include_duplicates:
                conditions.append("is_duplicate = 0")
        else:
            conditions.append("is_duplicate = 0")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with self._get_connection() as conn:
            # Get total count
            count_query = f"SELECT COUNT(*) FROM properties WHERE {where_clause}"
            cursor = conn.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Get paginated results
            query = f"""
                SELECT * FROM properties 
                WHERE {where_clause}
                ORDER BY discount_percentage DESC NULLS LAST
                LIMIT ? OFFSET ?
            """
            cursor = conn.execute(query, params + [limit, skip])
            properties = [self._row_to_property(row) for row in cursor]
        
        return properties, total
    
    def add_property(self, prop: Property, auto_save: bool = False, upsert: bool = True) -> Property:
        """Add or update a property."""
        normalized_url = normalize_url(prop.source_url or prop.auctioneer_url or "")
        
        with self._get_connection() as conn:
            # Check if property exists by normalized URL
            if normalized_url:
                cursor = conn.execute(
                    "SELECT id FROM properties WHERE normalized_url = ?",
                    (normalized_url,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    if upsert:
                        # Update existing property
                        self._update_property(conn, existing['id'], prop)
                        conn.commit()
                        return self.get_property(existing['id'])
                    else:
                        return self.get_property(existing['id'])
            
            # Insert new property
            prop.last_seen_at = datetime.utcnow()
            prop.is_active = True
            
            row_values = self._property_to_row(prop)
            placeholders = ",".join(["?" for _ in range(42)])
            
            conn.execute(f"""
                INSERT INTO properties (
                    id, title, category, auction_type, state, city, neighborhood, address,
                    description, area_total, area_privativa, evaluation_value,
                    first_auction_value, first_auction_date, second_auction_value, second_auction_date,
                    discount_percentage, image_url, auctioneer_id, source_url,
                    accepts_financing, accepts_fgts, accepts_installments, occupation_status, pending_debts,
                    auctioneer_name, auctioneer_url, source, latitude, longitude,
                    created_at, updated_at, dedup_key, is_duplicate, original_id,
                    is_active, last_seen_at, deactivated_at, value_changed_at,
                    previous_first_auction_value, previous_second_auction_value, normalized_url
                ) VALUES ({placeholders})
            """, row_values)
            
            conn.commit()
        
        return prop
    
    def _update_property(self, conn: sqlite3.Connection, prop_id: str, new_prop: Property):
        """Update an existing property with new data."""
        now = datetime.utcnow()
        
        conn.execute("""
            UPDATE properties SET
                title = ?,
                first_auction_value = ?,
                first_auction_date = ?,
                second_auction_value = ?,
                second_auction_date = ?,
                discount_percentage = ?,
                image_url = ?,
                evaluation_value = ?,
                updated_at = ?,
                last_seen_at = ?,
                is_active = 1
            WHERE id = ?
        """, (
            new_prop.title,
            new_prop.first_auction_value,
            new_prop.first_auction_date.isoformat() if new_prop.first_auction_date else None,
            new_prop.second_auction_value,
            new_prop.second_auction_date.isoformat() if new_prop.second_auction_date else None,
            new_prop.discount_percentage,
            new_prop.image_url,
            new_prop.evaluation_value,
            now.isoformat(),
            now.isoformat(),
            prop_id,
        ))
    
    def bulk_insert_properties(self, properties: List[Property]) -> dict:
        """Bulk insert properties for efficient sync operations."""
        imported = 0
        updated = 0
        skipped = 0
        
        with self._get_connection() as conn:
            for prop in properties:
                normalized_url = normalize_url(prop.source_url or prop.auctioneer_url or "")
                
                # Check if exists
                if normalized_url:
                    cursor = conn.execute(
                        "SELECT id FROM properties WHERE normalized_url = ?",
                        (normalized_url,)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        self._update_property(conn, existing['id'], prop)
                        updated += 1
                        continue
                
                # Insert new
                prop.last_seen_at = datetime.utcnow()
                prop.is_active = True
                
                row_values = self._property_to_row(prop)
                placeholders = ",".join(["?" for _ in range(42)])
                
                try:
                    conn.execute(f"""
                        INSERT INTO properties (
                            id, title, category, auction_type, state, city, neighborhood, address,
                            description, area_total, area_privativa, evaluation_value,
                            first_auction_value, first_auction_date, second_auction_value, second_auction_date,
                            discount_percentage, image_url, auctioneer_id, source_url,
                            accepts_financing, accepts_fgts, accepts_installments, occupation_status, pending_debts,
                            auctioneer_name, auctioneer_url, source, latitude, longitude,
                            created_at, updated_at, dedup_key, is_duplicate, original_id,
                            is_active, last_seen_at, deactivated_at, value_changed_at,
                            previous_first_auction_value, previous_second_auction_value, normalized_url
                        ) VALUES ({placeholders})
                    """, row_values)
                    imported += 1
                except sqlite3.IntegrityError:
                    skipped += 1
            
            conn.commit()
        
        return {"imported": imported, "updated": updated, "skipped": skipped}
    
    def delete_property(self, property_id: str) -> bool:
        """Delete a property by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM properties WHERE id = ?", (property_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def save_to_disk(self):
        """No-op for SQLite (data is already persisted)."""
        pass
    
    # Auctioneer methods
    @property
    def auctioneers(self) -> Dict[str, Auctioneer]:
        """Return auctioneers cache for compatibility."""
        return self._auctioneers_cache
    
    @property
    def properties(self) -> Dict[str, Property]:
        """Return a dict-like interface for compatibility. Note: This loads ALL properties into memory!"""
        result = {}
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM properties")
            for row in cursor:
                prop = self._row_to_property(row)
                result[prop.id] = prop
        return result
    
    def get_auctioneer(self, auctioneer_id: str) -> Optional[Auctioneer]:
        """Get an auctioneer by ID."""
        return self._auctioneers_cache.get(auctioneer_id)
    
    def get_auctioneers(self) -> List[Auctioneer]:
        """Get all auctioneers."""
        return list(self._auctioneers_cache.values())
    
    def create_auctioneer(self, auctioneer_data: AuctioneerCreate) -> Auctioneer:
        """Create a new auctioneer."""
        import uuid
        now = datetime.utcnow()
        auctioneer_id = str(uuid.uuid4())
        
        auctioneer = Auctioneer(
            id=auctioneer_id,
            name=auctioneer_data.name,
            website=auctioneer_data.website,
            is_active=True,
            property_count=0,
            created_at=now,
            updated_at=now,
        )
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO auctioneers (id, name, website, is_active, property_count, created_at, updated_at)
                VALUES (?, ?, ?, 1, 0, ?, ?)
            """, (auctioneer_id, auctioneer_data.name, auctioneer_data.website, now.isoformat(), now.isoformat()))
            conn.commit()
        
        self._auctioneers_cache[auctioneer_id] = auctioneer
        return auctioneer
    
    def get_auctioneer_by_website(self, website: str) -> Optional[Auctioneer]:
        """Get an auctioneer by website URL."""
        for auctioneer in self._auctioneers_cache.values():
            if auctioneer.website and website.lower() in auctioneer.website.lower():
                return auctioneer
        return None
    
    def update_auctioneer_scrape_status(self, auctioneer_id: str, status: str, last_scrape_at: datetime = None):
        """Update auctioneer scrape status."""
        if auctioneer_id in self._auctioneers_cache:
            auctioneer = self._auctioneers_cache[auctioneer_id]
            auctioneer.scrape_status = status
            if last_scrape_at:
                auctioneer.last_scrape_at = last_scrape_at
            auctioneer.updated_at = datetime.utcnow()
            
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE auctioneers SET scrape_status = ?, last_scrape_at = ?, updated_at = ?
                    WHERE id = ?
                """, (status, last_scrape_at.isoformat() if last_scrape_at else None, 
                      auctioneer.updated_at.isoformat(), auctioneer_id))
                conn.commit()
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            # Total properties
            cursor = conn.execute("SELECT COUNT(*) FROM properties")
            total = cursor.fetchone()[0]
            
            # Unique properties (non-duplicates)
            cursor = conn.execute("SELECT COUNT(*) FROM properties WHERE is_duplicate = 0")
            unique = cursor.fetchone()[0]
            
            # Duplicates
            duplicates = total - unique
            
            # Category counts
            cursor = conn.execute("""
                SELECT category, COUNT(*) as count 
                FROM properties 
                WHERE is_duplicate = 0
                GROUP BY category
            """)
            category_counts = {row['category']: row['count'] for row in cursor}
            
            # State counts (top 10)
            cursor = conn.execute("""
                SELECT state, COUNT(*) as count 
                FROM properties 
                WHERE is_duplicate = 0
                GROUP BY state
                ORDER BY count DESC
                LIMIT 10
            """)
            state_counts = {row['state']: row['count'] for row in cursor}
        
        return {
            "total_properties": total,
            "unique_properties": unique,
            "duplicate_properties": duplicates,
            "total_auctioneers": len(self._auctioneers_cache),
            "active_auctioneers": sum(1 for a in self._auctioneers_cache.values() if a.is_active),
            "category_counts": category_counts,
            "state_counts": state_counts,
        }
    
    def update_auctioneer_property_counts(self):
        """Update property counts for all auctioneers."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT auctioneer_id, COUNT(*) as count 
                FROM properties 
                WHERE is_duplicate = 0
                GROUP BY auctioneer_id
            """)
            counts = {row['auctioneer_id']: row['count'] for row in cursor}
            
            for auc_id, auctioneer in self._auctioneers_cache.items():
                auctioneer.property_count = counts.get(auc_id, 0)
                conn.execute(
                    "UPDATE auctioneers SET property_count = ? WHERE id = ?",
                    (auctioneer.property_count, auc_id)
                )
            conn.commit()


# Singleton instance
_db_instance: Optional[SQLiteDatabase] = None


def get_sqlite_database() -> SQLiteDatabase:
    """Get the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = SQLiteDatabase()
    return _db_instance
