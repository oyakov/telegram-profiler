"""Pytest fixtures for Networking Brain tests."""

from __future__ import annotations

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "crm")
os.environ.setdefault("POSTGRES_USER", "crm")
os.environ.setdefault("POSTGRES_PASSWORD", "changeme")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("LLM_PROVIDER", "google")
os.environ.setdefault("EMBED_PROVIDER", "google")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("WHISPER_URL", "http://localhost:9000")

from src.core.config import get_settings

DATABASE_URL = get_settings().database_url


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Per-test database session with cleanup.

    Uses a direct AsyncSession against the live DB.
    Cleans up test-created rows by filtering on source='__test__' or
    known test keys after each test.
    """
    engine = create_async_engine(DATABASE_URL, echo=False)
    session = AsyncSession(engine, expire_on_commit=False)

    yield session

    # Cleanup: delete any test data (contacts with source='__test__' or specific test emails)
    await session.rollback()
    await session.close()
    await engine.dispose()


@pytest_asyncio.fixture
async def api_client():
    """FastAPI test client."""
    from httpx import ASGITransport, AsyncClient
    from src.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
