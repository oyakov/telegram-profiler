import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy_utils import database_exists, create_database, drop_database
import sqlalchemy as sa

from src.db.database import get_engine, list_tenant_databases
from src.db.models import Base
from src.core.config import get_settings

settings = get_settings()
TEST_DB_NAME = "crm_test"
DB_HOST = "localhost" if settings.postgres_host == "postgres" else settings.postgres_host

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def setup_test_db():
    """Create a test database and initialize schema."""
    sync_url = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{DB_HOST}:{settings.postgres_port}/{TEST_DB_NAME}"
    
    if not database_exists(sync_url):
        create_database(sync_url)
    
    # Initialize schema
    engine = create_async_engine(
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{DB_HOST}:{settings.postgres_port}/{TEST_DB_NAME}"
    )
    
    async with engine.begin() as conn:
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()
    # Optional: drop_database(sync_url)

@pytest_asyncio.fixture
async def db_session(setup_test_db):
    """Provide an async session for a test."""
    engine = setup_test_db
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback() # Always rollback to keep tests isolated


@pytest_asyncio.fixture
async def api_client(setup_test_db):
    """Async HTTP client for testing FastAPI endpoints.

    Uses httpx.AsyncClient with ASGITransport so no real TCP socket is needed.
    The test database engine is set up before the first request is made.
    """
    from httpx import AsyncClient, ASGITransport
    from src.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
