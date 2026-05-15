import pytest
from src.db.database import list_tenant_databases
from unittest.mock import patch, MagicMock
import asyncpg

@pytest.mark.asyncio
async def test_list_tenant_databases():
    # We mock asyncpg.connect to avoid actual DB connection in this test
    # but still test the logic of filtering and merging with settings
    
    mock_conn = MagicMock()
    # Mocking fetch as an AsyncMock to be awaitable
    from unittest.mock import AsyncMock
    mock_conn.fetch = AsyncMock(return_value=[
        {'datname': 'crm_project_a'},
        {'datname': 'crm_project_b'}
    ])
    mock_conn.close = AsyncMock()
    
    with patch('asyncpg.connect', AsyncMock(return_value=mock_conn)):
        dbs = await list_tenant_databases()
        
        assert 'crm_project_a' in dbs
        assert 'crm_project_b' in dbs
        # The 'other_db' should NOT be in the result because of the LIKE 'crm%' filter
        assert 'other_db' not in dbs
        
        # Verify it includes the default DB from settings if not already present
        # (Assuming the mock settings in conftest.py use 'crm_test')
        from src.core.config import get_settings
        settings = get_settings()
        assert settings.postgres_db in dbs
        
    mock_conn.close.assert_called_once()
