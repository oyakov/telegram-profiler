"""Tests for LLM-based contact extraction."""

import pytest
from unittest.mock import AsyncMock, patch

from src.ai.services import ExtractionService, ContactExtraction

@pytest.mark.asyncio
async def test_extract_contacts_mock():
    """Test contact extraction with a mocked LLM response."""
    # This mock data matches the new ExtractionResult schema (items)
    mock_data = {
        "items": [
            {
                "first_name": "Alice",
                "last_name": "Smith",
                "email": "alice@example.com",
                "confidence": 0.95
            }
        ],
        "summary": "Extracted Alice Smith"
    }

    with patch("src.ai.services.structured_extraction", new_callable=AsyncMock) as mock_ext:
        mock_ext.return_value = {
            "data": mock_data,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "processing_time_ms": 200,
            "model": "gpt-4o",
            "provider": "openai"
        }

        service = ExtractionService()
        contacts, metadata = await service.extract("Alice Smith is at alice@example.com")

        assert len(contacts) == 1
        assert contacts[0].first_name == "Alice"
        assert contacts[0].email == "alice@example.com"
        assert metadata["chunks"] == 1
        assert metadata["tokens"] == 150
