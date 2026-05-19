"""Unit tests for hybrid search logic and evidence extraction."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.api.routers.search import semantic_search, _extract_evidence_batch
from src.api.schemas import SearchRequest

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.mark.asyncio
async def test_semantic_search_integration(mock_db):
    """Test the semantic search flow with mocked DB results."""
    req = SearchRequest(query="find python developers", limit=10)
    
    # Mock embedding generation
    with patch("src.ai.analysis.generate_embedding", AsyncMock(return_value=[0.1]*1536)), \
         patch("src.api.routers.search.settings") as mock_settings:
        
        mock_settings.search_semantic_threshold = 0.52
        mock_settings.search_row_limit_multiplier = 5
        mock_settings.search_max_semantic_per_contact = 5
        mock_settings.search_keyword_fallback_relevance = 0.5
        
        # Mock DB results for semantic search
        mock_contact = MagicMock()
        mock_contact.id = "contact-123"
        mock_contact.first_name = "Alice"
        
        mock_msg = MagicMock()
        mock_msg.contact = mock_contact
        
        mock_me = MagicMock()
        mock_me.message_id = "msg-456"
        
        # mock_db.execute returns an object with fetchall or iteration
        mock_res = MagicMock()
        mock_res.__iter__.return_value = [(mock_me, mock_msg, 0.1)] # Very similar
        mock_db.execute.return_value = mock_res
        
        # Mock _extract_evidence_batch
        with patch("src.api.routers.search._extract_evidence_batch", AsyncMock(return_value={"contact-123": []})):
            result = await semantic_search(req, mock_db)
            
    assert result["query"] == "find python developers"
    assert len(result["contacts"]) == 1
    assert result["contacts"][0]["id"] == "contact-123"

@pytest.mark.asyncio
async def test_keyword_fallback_trigger(mock_db):
    """Test that keyword search is triggered when semantic search yields few results."""
    req = SearchRequest(query="rare skill", limit=10)
    
    with patch("src.ai.analysis.generate_embedding", AsyncMock(return_value=[0.1]*1536)), \
         patch("src.api.routers.search.settings") as mock_settings, \
         patch("src.api.routers.search._keyword_search") as mock_keyword:
        
        mock_settings.search_semantic_threshold = 0.52
        
        # 1. Semantic search returns NOTHING
        mock_res = MagicMock()
        mock_res.__iter__.return_value = []
        mock_db.execute.return_value = mock_res
        
        # 2. Keyword search returns one contact
        mock_contact = MagicMock()
        mock_contact.id = "keyword-contact"
        mock_keyword.return_value = [(mock_contact, 1)]
        
        # 3. Mock _extract_evidence_batch
        with patch("src.api.routers.search._extract_evidence_batch", AsyncMock(return_value={})):
            result = await semantic_search(req, mock_db)
            
    assert mock_keyword.called
    assert len(result["contacts"]) == 1
    assert result["contacts"][0]["id"] == "keyword-contact"

@pytest.mark.asyncio
async def test_extract_evidence_batch_limit(mock_db):
    """Test that evidence extraction respects max_quotes."""
    contact_ids = ["c1"]
    query_emb = [0.1] * 1536
    
    # Mock DB to return 10 quotes for c1
    mock_res = MagicMock()
    mock_res.__iter__.return_value = [("c1", f"quote {i}", 0.1) for i in range(10)]
    mock_db.execute.return_value = mock_res
    
    evidence = await _extract_evidence_batch(mock_db, contact_ids, query_emb, max_quotes=3)
    
    assert "c1" in evidence
    assert len(evidence["c1"]) == 3 # Should be limited to 3
