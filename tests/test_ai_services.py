import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.ai.services import ExtractionService, ContactExtraction, LeadExtraction, ChannelDeepAnalysis


@pytest.fixture
def extraction_service():
    mock_enc = MagicMock()
    mock_enc.encode.return_value = list(range(500))  # 500 tokens
    mock_enc.decode.return_value = "chunk"
    mock_tiktoken = MagicMock()
    mock_tiktoken.encoding_for_model.return_value = mock_enc
    mock_tiktoken.get_encoding.return_value = mock_enc

    with patch("src.core.config.get_settings") as mock_cfg, \
         patch("src.ai.services.tiktoken", mock_tiktoken):
        mock_cfg.return_value.llm_provider = "google"
        mock_cfg.return_value.google_llm_model = "gemini-2.5-flash"
        mock_cfg.return_value.lmstudio_llm_model = "qwen3.5-3b"
        yield ExtractionService()

def test_chunk_text(extraction_service):
    text = "Hello world " * 1000 
    chunks = extraction_service._chunk_text(text, max_tokens=100)
    assert len(chunks) > 1
    assert all(isinstance(c, str) for c in chunks)
    assert all(isinstance(c, str) for c in chunks)

@pytest.mark.asyncio
async def test_extract_contacts(extraction_service):
    mock_result = {
        "data": {
            "items": [
                {"first_name": "John", "last_name": "Doe", "email": "john@example.com"}
            ],
            "summary": "Found one contact",
            "is_relevant": True
        },
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "processing_time_ms": 200
    }
    
    with patch("src.ai.services.structured_extraction", new_callable=AsyncMock) as mock_structured:
        mock_structured.return_value = mock_result
        
        items, metadata = await extraction_service.extract("Some text", extraction_type="contacts")
        
        assert len(items) == 1
        assert isinstance(items[0], ContactExtraction)
        assert items[0].first_name == "John"
        assert metadata["tokens"] == 150
        assert metadata["chunks"] == 1

@pytest.mark.asyncio
async def test_extract_leads(extraction_service):
    mock_result = {
        "data": {
            "items": [
                {
                    "username": "leaduser",
                    "display_name": "Lead User",
                    "content_summary": "Looking for dev",
                    "category": "IT",
                    "lead_type": "Consumer",
                    "lead_quality": 8,
                    "confidence": 0.9,
                    "evidence_quote": "Hire me"
                }
            ]
        }
    }
    
    with patch("src.ai.services.structured_extraction", new_callable=AsyncMock) as mock_structured:
        mock_structured.return_value = mock_result
        
        items, metadata = await extraction_service.extract("Some text", extraction_type="leads")
        
        assert len(items) == 1
        assert isinstance(items[0], LeadExtraction)
        assert items[0].category == "IT"

@pytest.mark.asyncio
async def test_extract_deep_analysis(extraction_service):
    mock_result = {
        "data": {
            "items": [
                {
                    "topics": ["Python", "AI"],
                    "mentioned_companies": ["Google"],
                    "mentioned_products": ["Gemini"],
                    "sentiment": "positive"
                }
            ]
        }
    }
    
    with patch("src.ai.services.structured_extraction", new_callable=AsyncMock) as mock_structured:
        mock_structured.return_value = mock_result
        
        items, metadata = await extraction_service.extract("Some text", extraction_type="deep_analysis")
        
        assert len(items) == 1
        assert isinstance(items[0], ChannelDeepAnalysis)
        assert "Python" in items[0].topics

@pytest.mark.asyncio
async def test_extract_fallback_logic(extraction_service):
    # Test fallback for "contacts" key instead of "items"
    mock_result = {
        "data": {
            "contacts": [
                {"first_name": "Fallback", "email": "fb@example.com"}
            ]
        }
    }
    
    with patch("src.ai.services.structured_extraction", new_callable=AsyncMock) as mock_structured:
        mock_structured.return_value = mock_result
        items, _ = await extraction_service.extract("Some text", extraction_type="contacts")
        assert len(items) == 1
        assert items[0].first_name == "Fallback"

@pytest.mark.asyncio
async def test_extract_field_renaming_fallback(extraction_service):
    # Test ad_content_summary -> content_summary
    mock_result = {
        "data": {
            "items": [
                {
                    "username": "leaduser",
                    "ad_content_summary": "Old field name",
                    "category": "IT",
                    "lead_type": "Supplier",
                    "lead_quality": 5,
                    "confidence": 0.5,
                    "evidence_quote": "..."
                }
            ]
        }
    }
    
    with patch("src.ai.services.structured_extraction", new_callable=AsyncMock) as mock_structured:
        mock_structured.return_value = mock_result
        items, _ = await extraction_service.extract("Some text", extraction_type="leads")
        assert items[0].content_summary == "Old field name"
