"""Tests for Telegram enrichment logic."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import uuid
from contextlib import asynccontextmanager

from src.connectors.telegram_connector import TelegramConnector
from src.db.models import Contact

@asynccontextmanager
async def mock_get_session(session):
    yield session

@pytest.mark.asyncio
async def test_enrich_contact_mock():
    """Test enrich_contact with mocked Telethon and DB."""
    connector = TelegramConnector()
    
    # Mock contact
    contact_id = str(uuid.uuid4())
    mock_contact = Contact(
        id=contact_id,
        first_name="Original",
        telegram_id="123456",
        source="telegram"
    )
    
    # Mock DB session
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_contact
    mock_session.execute.return_value = mock_result
    
    # Mock Telethon client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    
    # Mock full user info
    mock_full_user = MagicMock()
    mock_full_user.full_user.about = "New Bio"
    # The client is called like client(GetFullUserRequest(...))
    mock_client.side_effect = lambda req: mock_full_user if "GetFullUserRequest" in str(type(req)) else None
    
    # Mock entity
    mock_entity = MagicMock()
    mock_entity.id = 123456
    mock_entity.first_name = "New Name"
    mock_entity.username = "new_username"
    mock_entity.bot = False
    mock_entity.verified = True
    mock_client.get_entity.return_value = mock_entity
    
    # Mock download_profile_photo
    mock_client.download_profile_photo.return_value = "uploads/avatars/123456.jpg"

    with patch("src.connectors.telegram_connector.get_session", side_effect=lambda *args, **kwargs: mock_get_session(mock_session)), \
         patch.object(TelegramConnector, "_get_client", return_value=mock_client):
        
        success = await connector.enrich_contact(contact_id)
        
        assert success is True
        assert mock_contact.bio == "New Bio"
        assert mock_contact.first_name == "New Name"
        assert mock_contact.telegram_username == "new_username"
        assert mock_contact.is_verified is True
        # Connector uses absolute path /app/uploads/avatars (fixed in Round-3 #18)
        assert mock_contact.profile_photo_path.endswith("uploads/avatars/123456.jpg")
        
        mock_session.commit.assert_called()

@pytest.mark.asyncio
async def test_enrich_contact_not_found():
    """Test enrichment when contact is missing."""
    connector = TelegramConnector()
    contact_id = str(uuid.uuid4())
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with patch("src.connectors.telegram_connector.get_session", side_effect=lambda *args, **kwargs: mock_get_session(mock_session)):
        success = await connector.enrich_contact(contact_id)
        assert success is False
