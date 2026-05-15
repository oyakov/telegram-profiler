"""Unit tests for database engine caching and tenant utilities."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def test_get_engine_caches_by_db_name():
    """Same db_name + pooling flag should return the cached engine."""
    from src.db.database import _engines, get_engine

    _engines.clear()

    engine_a = get_engine("crm_test_cache_a")
    engine_b = get_engine("crm_test_cache_a")
    engine_c = get_engine("crm_test_cache_b")

    assert engine_a is engine_b, "Same db_name must return the same engine instance"
    assert engine_a is not engine_c, "Different db_name must return different engines"

    _engines.clear()


def test_get_engine_differentiates_pooling():
    """pooled vs non-pooled variants are cached separately."""
    from src.db.database import _engines, get_engine

    _engines.clear()

    pooled = get_engine("crm_pool_flag", use_pooling=True)
    direct = get_engine("crm_pool_flag", use_pooling=False)

    assert pooled is not direct
    _engines.clear()


def test_get_engine_evicts_oldest_when_limit_reached():
    """When cache hits 50 engines, the oldest is evicted without RuntimeError."""
    from src.db.database import _engines, get_engine

    _engines.clear()

    # Fill to 50
    for i in range(50):
        get_engine(f"crm_evict_{i:03d}")

    assert len(_engines) == 50
    oldest_key = next(iter(_engines))

    # Adding one more should evict the oldest — and NOT raise RuntimeError
    # (the asyncio fix: RuntimeError caught when no loop is running)
    get_engine("crm_evict_new")

    assert len(_engines) == 50
    assert oldest_key not in _engines, "Oldest engine should have been evicted"
    assert any("crm_evict_new" in k for k in _engines)

    _engines.clear()


@pytest.mark.asyncio
async def test_list_tenant_databases_filters_and_merges():
    """list_tenant_databases returns crm-prefixed DBs and always includes the default."""
    from unittest.mock import AsyncMock
    import asyncpg

    mock_conn = MagicMock()
    # The SQL query uses WHERE datname LIKE 'crm%', so the mock returns
    # only what Postgres would actually return — no non-crm rows here.
    mock_conn.fetch = AsyncMock(return_value=[
        {'datname': 'crm_alpha'},
        {'datname': 'crm_beta'},
    ])
    mock_conn.close = AsyncMock()

    with patch('asyncpg.connect', AsyncMock(return_value=mock_conn)):
        from src.db.database import list_tenant_databases
        dbs = await list_tenant_databases()

    assert 'crm_alpha' in dbs
    assert 'crm_beta' in dbs

    # Always includes the configured default
    from src.core.config import get_settings
    assert get_settings().postgres_db in dbs

    mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_list_tenant_databases_deduplicates():
    """Default DB already returned by the query should not appear twice."""
    from unittest.mock import AsyncMock
    from src.core.config import get_settings
    import asyncpg

    default_db = get_settings().postgres_db

    mock_conn = MagicMock()
    mock_conn.fetch = AsyncMock(return_value=[
        {'datname': default_db},
        {'datname': 'crm_extra'},
    ])
    mock_conn.close = AsyncMock()

    with patch('asyncpg.connect', AsyncMock(return_value=mock_conn)):
        from src.db.database import list_tenant_databases
        dbs = await list_tenant_databases()

    assert dbs.count(default_db) == 1, "Default DB must appear exactly once"
