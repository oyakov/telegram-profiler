#!/usr/bin/env python3
"""
Maintenance CLI - Unified administrative utility for the telegram-profiler project.
Consolidates migrate, reinit, and reset operations across all tenant databases.
"""

import asyncio
import os
import sys
import argparse
import subprocess
import asyncpg
import structlog
from typing import List

# Add project root to path
sys.path.append(os.getcwd())

from src.core.config import get_settings
from src.db.database import ensure_database_exists, init_database_schema, get_session

# Setup logging
try:
    from src.core.logging import setup_logging
    setup_logging()
except ImportError:
    pass

logger = structlog.get_logger()
settings = get_settings()

async def get_all_crm_databases() -> List[str]:
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

def run_alembic_upgrade(db_name: str) -> bool:
    """Run alembic upgrade head for a specific database."""
    logger.info("maintenance_migrate_db", database=db_name)
    env = os.environ.copy()
    env["POSTGRES_DB"] = db_name
    
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("maintenance_migrate_success", database=db_name)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("maintenance_migrate_failed", database=db_name, error=e.stderr)
        return False

async def cmd_migrate(args):
    """Run migrations across all detected databases."""
    databases = await get_all_crm_databases()
    logger.info("maintenance_migrate_start", count=len(databases))
    
    for db in databases:
        run_alembic_upgrade(db)
    
    logger.info("maintenance_migrate_complete")

async def cmd_reinit(args):
    """Ensure all target databases exist and have basic schema."""
    # List from original reinit_all_dbs.py plus any dynamic ones
    base_dbs = [
        "crm", "crm_crypto", "crm_bg_rent", 
        "crm_bg_cars", "crm_bg_work", "crm_bg_news"
    ]
    
    logger.info("maintenance_reinit_start", databases=base_dbs)
    for db_name in base_dbs:
        try:
            await ensure_database_exists(db_name)
            await init_database_schema(db_name)
            logger.info("maintenance_reinit_success", database=db_name)
        except Exception as e:
            logger.error("maintenance_reinit_failed", database=db_name, error=str(e))

async def cmd_reset_sync(args):
    """Reset sync states in a specific or all databases."""
    from src.db.models import ChannelSyncState, SyncBatchLog
    from sqlalchemy import delete

    databases = [args.db] if args.db else await get_all_crm_databases()
    
    logger.info("maintenance_reset_sync_start", databases=databases)
    for db_name in databases:
        try:
            async with get_session(db_name=db_name) as session:
                await session.execute(delete(SyncBatchLog))
                await session.execute(delete(ChannelSyncState))
                await session.commit()
                logger.info("maintenance_reset_sync_success", database=db_name)
        except Exception as e:
            logger.error("maintenance_reset_sync_failed", database=db_name, error=str(e))

def main():
    parser = argparse.ArgumentParser(description="Telegram Profiler Maintenance CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Migrate
    subparsers.add_parser("migrate", help="Run Alembic migrations on all CRM databases")

    # Reinit
    subparsers.add_parser("reinit", help="Ensure base databases exist and are initialized")

    # Reset
    reset_parser = subparsers.add_parser("reset-sync", help="Clear all sync states and batch logs")
    reset_parser.add_argument("--db", help="Specific database to reset (default: all)")

    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    if args.command == "migrate":
        loop.run_until_complete(cmd_migrate(args))
    elif args.command == "reinit":
        loop.run_until_complete(cmd_reinit(args))
    elif args.command == "reset-sync":
        loop.run_until_complete(cmd_reset_sync(args))

if __name__ == "__main__":
    main()
