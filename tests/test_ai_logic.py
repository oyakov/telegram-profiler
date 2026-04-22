import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.ai.deduplication import find_duplicate, merge_contact_fields
from src.ai.embeddings import cosine_similarity, generate_embedding
from src.db.models import Contact

@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_find_duplicate_exact(mock_session):
    # Setup: Contact in DB
    existing = Contact(id=1, email="test@example.com", first_name="Test")
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing
    mock_session.execute.return_value = mock_res
    
    # Run
    match = await find_duplicate(mock_session, email="test@example.com")
    
    # Assert
    assert match.id == 1
    mock_session.execute.assert_called()

@pytest.mark.asyncio
async def test_find_duplicate_fuzzy(mock_session):
    # Setup: Contact with embedding
    existing = Contact(id=2, first_name="Fuzzy")
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing
    mock_session.execute.return_value = mock_res
    
    # Mock embedding query
    match = await find_duplicate(mock_session, embedding=[0.1]*1024)
    
    assert match.id == 2

def test_merge_contact_fields():
    existing = Contact(id=1, first_name="John", email=None, skills=["python"])
    new_data = {
        "first_name": "Johnny", # Should NOT overwrite
        "email": "john@example.com", # Should fill
        "skills": ["rust", "python"], # Should merge unique
        "notes": "New note"
    }
    
    updated = merge_contact_fields(existing, new_data)
    
    assert updated is True
    assert existing.first_name == "John"
    assert existing.email == "john@example.com"
    assert set(existing.skills) == {"python", "rust"}
    assert existing.notes == "New note"

def test_cosine_similarity():
    v1 = [1.0, 0.0]
    v2 = [1.0, 0.0]
    v3 = [0.0, 1.0]
    
    assert cosine_similarity(v1, v2) > 0.99
    assert abs(cosine_similarity(v1, v3)) < 0.01

@pytest.mark.asyncio
async def test_generate_embedding_mock():
    with patch("src.ai.embeddings.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.5]*1024)]
        )
        
        vec = await generate_embedding("test text")
        assert len(vec) == 1024
        assert vec[0] == 0.5
