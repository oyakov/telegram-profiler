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

    # Fast path: no lock needed once the engine is cached.
    if cache_key in _engines:
        return _engines[cache_key]

    with _engines_lock:
        # Re-check inside the lock to handle concurrent first-access.
        if cache_key in _engines:
            return _engines[cache_key]

        if len(_engines) >= 50:
            oldest_key = next(iter(_engines))
            old_engine = _engines.pop(oldest_key)
            import asyncio
            try:
                asyncio.get_running_loop().create_task(old_engine.dispose())
            except RuntimeError:
                pass  # No event loop (Celery sync context); GC will clean up

        # Use SQLAlchemy URL object so the password is redacted in repr/logs
        url = sa.engine.URL.create(
            drivername="postgresql+asyncpg",
            username=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=int(settings.postgres_port),
            database=db_name,
        )

        engine_kwargs: dict = {
            # echo logs SQL statements (never the connection URL/password)
            "echo": settings.log_level.upper() == "DEBUG",
        }

        if not use_pooling:
            engine_kwargs["poolclass"] = NullPool
        else:
            # Conservative pool per tenant: 50 tenants × 8 conn = 400 max vs PG default 100
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 3
            # Detect stale connections after Docker/network restarts
            engine_kwargs["pool_pre_ping"] = True
            # Recycle connections every 30 min to prevent idle-timeout drops
            engine_kwargs["pool_recycle"] = 1800

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

from fastapi import Request, HTTPException

async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session based on X-Database header.

    The X-Database value is validated against _DB_NAME_RE before use to prevent
    connection-URL injection (issue #2 in code review).
    """
    db_name = request.headers.get("X-Database") or None  # treat empty string as None
    if db_name is not None and not _DB_NAME_RE.match(db_name):
        raise HTTPException(status_code=400, detail="Invalid X-Database header value")
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
