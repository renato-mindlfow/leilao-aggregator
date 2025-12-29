import os
from dotenv import load_dotenv

# Carregar .env ANTES de qualquer outra coisa
load_dotenv()

# Database selection priority:
# 1. PostgreSQL if DATABASE_URL is set (Supabase)
# 2. SQLite if USE_SQLITE is true
# 3. In-memory database as fallback

# NO FALLBACK - DATABASE_URL must be in .env
DATABASE_URL = os.getenv("DATABASE_URL")
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

if DATABASE_URL:
    # Use PostgreSQL (Supabase)
    from .postgres_database import get_postgres_database
    db = get_postgres_database()
elif USE_SQLITE:
    # Use SQLite for local persistent storage
    from .sqlite_database import get_sqlite_database
    db = get_sqlite_database()
else:
    # Use in-memory database as fallback
    from .database import InMemoryDatabase
    db = InMemoryDatabase()

from .deduplication import DeduplicationService

__all__ = ["db", "DeduplicationService"]
