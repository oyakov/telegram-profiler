# Re-export canonical implementations from src.db.database to avoid duplication.
# All callers should import from here or directly from src.db.database.
from src.db.database import ensure_database_exists, init_database_schema  # noqa: F401
