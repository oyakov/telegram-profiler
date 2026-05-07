"""Script to run Alembic migrations across all CRM databases."""

import asyncio
import os
import sys
import asyncpg
import subprocess
import structlog

# Add project root to path
sys.path.append(os.getcwd())

from src.core.config import get_settings

setup_logging = False
try:
    from src.core.logging import setup_logging as init_logging
    init_logging()
    setup_logging = True
except ImportError:
    pass

logger = structlog.get_logger()
settings = get_settings()

async def get_all_crm_databases() -> list[str]:
    """Fetch all database names starting with 'crm'."""
    conn = await asyncpg.connect(
        user=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database="postgres"
    )
    try:
        rows = await conn.fetch(
            "SELECT datname FROM pg_database WHERE datname LIKE 'crm%'"
        )
        return [row['datname'] for row in rows]
    finally:
        await conn.close()

def run_migration(db_name: str) -> bool:
    """Run alembic upgrade head for a specific database."""
    logger.info("starting_migration", database=db_name)
    
    # Set environment variable for alembic/env.py to pick up
    env = os.environ.copy()
    env["POSTGRES_DB"] = db_name
    
    try:
        # Use subprocess to avoid state pollution between runs in the same process
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("migration_success", database=db_name, output=result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("migration_failed", database=db_name, error=e.stderr)
        return False

async def main():
    logger.info("multi_db_migration_started")
    databases = await get_all_crm_databases()
    logger.info("databases_found", count=len(databases), list=databases)
    
    results = {}
    for db in databases:
        success = run_migration(db)
        results[db] = "OK" if success else "FAILED"
    
    logger.info("multi_db_migration_finished", results=results)

if __name__ == "__main__":
    asyncio.run(main())
