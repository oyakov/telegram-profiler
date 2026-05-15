"""Database engine and session management."""

from __future__ import annotations

import re
import threading
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool
import asyncpg

from src.core.config import get_settings

settings = get_settings()
_engines: dict[str, AsyncEngine] = {}
_engines_lock = threading.Lock()

_DB_NAME_RE = re.compile(r'^[a-z][a-z0-9_]{0,62}$')

def get_engine(db_name: str | None = None, use_pooling: bool = True) -> sa.ext.asyncio.AsyncEngine:
    db_name = db_name or settings.postgres_db
    cache_key = f"{db_name}_{'pooled' if use_pooling else 'direct'}"

    with _engines_lock:
        if cache_key not in _engines:
            if len(_engines) >= 50:
                oldest_key = next(iter(_engines))
                old_engine = _engines.pop(oldest_key)
                import asyncio
                try:
                    asyncio.get_running_loop().create_task(old_engine.dispose())
                except RuntimeError:
                    pass  # No event loop (Celery sync context); GC will clean up

            url = (
                f"postgresql+asyncpg://"
                f"{settings.postgres_user}:{settings.postgres_password}"
                f"@{settings.postgres_host}:{settings.postgres_port}"
                f"/{db_name}"
            )

            engine_kwargs = {
                "echo": settings.log_level.upper() == "DEBUG",
            }

            if not use_pooling:
                engine_kwargs["poolclass"] = NullPool
            else:
                engine_kwargs["pool_size"] = 20
                engine_kwargs["max_overflow"] = 10

            _engines[cache_key] = create_async_engine(url, **engine_kwargs)

    return _engines[cache_key]

@asynccontextmanager
async def get_session(db_name: str | None = None, use_pooling: bool = False) -> AsyncGenerator[AsyncSession, None]:
    """Standalone async context manager for use outside FastAPI with optional DB routing.
    Defaults to use_pooling=False for safe usage in Celery workers.
    """
    engine = get_engine(db_name, use_pooling=use_pooling)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

from fastapi import Request

async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session based on X-Database header."""
    db_name = request.headers.get("X-Database")
    async with get_session(db_name, use_pooling=True) as session:
        yield session

async def ensure_database_exists(db_name: str):
    """Ensure a database exists, creating it if necessary."""
    if not _DB_NAME_RE.match(db_name):
        raise ValueError(f"Invalid database name: {db_name!r}")
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

async def list_tenant_databases() -> list[str]:
    """Scan Postgres for all databases starting with 'crm_' or return configured default."""
    user = settings.postgres_user
    password = settings.postgres_password
    host = settings.postgres_host
    port = settings.postgres_port
    
    # Connect to system 'postgres' DB
    conn = await asyncpg.connect(
        user=user, 
        password=password, 
        host=host, 
        port=port, 
        database="postgres"
    )
    try:
        rows = await conn.fetch("SELECT datname FROM pg_database WHERE datname LIKE 'crm%'")
        dbs = [row['datname'] for row in rows]
        # Always include the default configured DB if not found
        if settings.postgres_db not in dbs:
            dbs.append(settings.postgres_db)
        return sorted(list(set(dbs)))
    finally:
        await conn.close()
