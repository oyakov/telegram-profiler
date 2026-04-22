import pytest
from unittest.mock import patch
from src.connectors.social_connector import SocialConnector

@pytest.mark.asyncio
async def test_social_connector_init():
    with patch("os.getenv", return_value="test_db"):
        conn = SocialConnector()
        assert conn.db_name == "test_db"

@pytest.mark.asyncio
async def test_social_sync_stub():
    conn = SocialConnector()
    result = await conn.sync()
    assert result.status == "error"
    assert "stub" in result.errors[0]

@pytest.mark.asyncio
async def test_social_status():
    conn = SocialConnector()
    status = await conn.get_status()
    assert status["status"] == "disabled"

@pytest.mark.asyncio
async def test_social_test_connection():
    conn = SocialConnector()
    assert await conn.test_connection() is False
