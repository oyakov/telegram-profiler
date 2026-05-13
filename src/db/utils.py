import asyncpg
import sqlalchemy as sa
from src.core.config import get_settings
from src.db.database import get_engine

settings = get_settings()

async def ensure_database_exists(db_name: str):
    """Ensure a database exists, creating it if necessary."""
    user = settings.postgres_user
    password = settings.postgres_password
    host = settings.postgres_host
    port = settings.postgres_port
    
    # Connect to system 'postgres' DB to perform creation
    conn = await asyncpg.connect(
        user=user, 
        password=password, 
        host=host, 
        port=port, 
        database="postgres"
    )
    try:
        # Check if exists
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            # CREATE DATABASE cannot be executed in a transaction block
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Created database: {db_name}")
    finally:
        await conn.close()

async def init_database_schema(db_name: str):
    """Initialize database schema by creating all tables."""
    from src.db.models import Base
    engine = get_engine(db_name, use_pooling=False)
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print(f"Initialized schema for database: {db_name}")
