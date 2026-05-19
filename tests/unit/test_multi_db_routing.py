"""Unit tests for Multi-DB routing and tenant isolation."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from src.db.database import get_db, _DB_NAME_RE

@pytest.mark.asyncio
async def test_db_name_validation():
    """Verify the strict regex for database names."""
    valid_names = ["tenant1", "my_db", "db_123"]
    invalid_names = ["tenant;DROP", "db-name", "123db", "db.name", "db name"]
    
    for name in valid_names:
        assert _DB_NAME_RE.match(name) is not None
        
    for name in invalid_names:
        assert _DB_NAME_RE.match(name) is None

@pytest.mark.asyncio
async def test_get_db_routing():
    """Verify that get_db uses the X-Database header."""
    mock_request = MagicMock()
    mock_request.headers = {"X-Database": "tenant_a"}
    
    with patch("src.db.database.get_session") as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # We use the dependency directly
        generator = get_db(mock_request)
        db = await generator.__anext__()
        
        assert db == mock_session
        # Updated to match actual call signature: get_session(db_name, use_pooling=True)
        mock_get_session.assert_called_once_with("tenant_a", use_pooling=True)

@pytest.mark.asyncio
async def test_get_db_invalid_header():
    """Verify that an invalid X-Database header raises 400."""
    mock_request = MagicMock()
    mock_request.headers = {"X-Database": "invalid;db"}
    
    with pytest.raises(HTTPException) as exc:
        generator = get_db(mock_request)
        await generator.__anext__()
        
    assert exc.value.status_code == 400
    assert "Invalid X-Database" in exc.value.detail

@pytest.mark.asyncio
async def test_get_db_default_routing():
    """Verify that get_db falls back to default if header is missing."""
    mock_request = MagicMock()
    mock_request.headers = {}
    
    with patch("src.db.database.get_session") as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        generator = get_db(mock_request)
        await generator.__anext__()
        
        # Updated to match actual call signature
        mock_get_session.assert_called_once_with(None, use_pooling=True)
