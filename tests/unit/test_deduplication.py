"""Unit tests for ContactRepository deduplication and merging logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.db.repository import ContactRepository
from src.db.models import Contact

@pytest.fixture
def repo():
    session = AsyncMock()
    return ContactRepository(session)

def test_merge_basic_fields(repo):
    """Test filling empty fields with new values."""
    existing = Contact(first_name="Alice", company=None)
    new_data = {"first_name": "Alice Override", "company": "Acme Corp", "position": "CEO"}
    
    updated = repo.merge_contact_fields(existing, new_data)
    
    assert updated is True
    assert existing.first_name == "Alice" # Should NOT override existing
    assert existing.company == "Acme Corp"
    assert existing.position == "CEO"
    assert existing.embedding_dirty is True

def test_merge_lists_uniqueness(repo):
    """Test merging interests and skills while maintaining uniqueness."""
    existing = Contact(interests=["coding", "crypto"], skills=["python"])
    new_data = {"interests": ["crypto", "travel"], "skills": ["python", "rust"]}
    
    updated = repo.merge_contact_fields(existing, new_data)
    
    assert updated is True
    assert set(existing.interests) == {"coding", "crypto", "travel"}
    assert set(existing.skills) == {"python", "rust"}
    assert existing.embedding_dirty is True

def test_merge_facts_json(repo):
    """Test merging facts_json without overwriting existing keys."""
    existing = Contact(facts_json={"location": "London", "age": "30"})
    new_data = {"facts": {"age": "35", "hobby": "chess"}}
    
    updated = repo.merge_contact_fields(existing, new_data)
    
    assert updated is True
    assert existing.facts_json["location"] == "London"
    assert existing.facts_json["age"] == "30" # Should NOT override
    assert existing.facts_json["hobby"] == "chess"

def test_merge_notes_accumulation(repo):
    """Test that notes are appended with a separator."""
    existing = Contact(notes="Initial note.")
    new_data = {"notes": "New discovery."}
    
    updated = repo.merge_contact_fields(existing, new_data)
    
    assert updated is True
    assert "Initial note." in existing.notes
    assert "New discovery." in existing.notes
    assert "---" in existing.notes

def test_merge_no_changes(repo):
    """Test that updated is False if no changes are made."""
    existing = Contact(first_name="Alice", interests=["coding"], embedding_dirty=False)
    new_data = {"first_name": "Alice", "interests": ["coding"]}
    
    updated = repo.merge_contact_fields(existing, new_data)
    
    assert updated is False
    assert existing.embedding_dirty is False
