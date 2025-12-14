import os

# Database selection priority:
# 1. PostgreSQL if DATABASE_URL is set (Supabase)
# 2. SQLite if USE_SQLITE is true
# 3. In-memory database as fallback

# Default to Supabase PostgreSQL if DATABASE_URL is not set
DEFAULT_DATABASE_URL = "postgresql://postgres.nawbptwbmdgrkbpbwxzl:Ri%25Fu!y$N!56ckC@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
USE_SQLITE = os.environ.get("USE_SQLITE", "false").lower() == "true"

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
