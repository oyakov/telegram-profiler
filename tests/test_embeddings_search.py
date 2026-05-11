"""Integration tests for embeddings and semantic search."""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from src.db.database import get_session
from src.db.models import Contact, Message, MessageEmbedding
from src.pipeline.unified_processor import maintenance_index_messages, maintenance_reindex_dirty
from src.api.routers.search import semantic_search
from src.api.schemas import SearchRequest


@pytest.fixture
async def test_db_session():
    """Create a test database session."""
    async with get_session(db_name="crm") as session:
        yield session


@pytest.mark.asyncio
async def test_create_test_messages(test_db_session):
    """Create test messages for embedding."""
    session = test_db_session

    # Create test contact
    contact = Contact(
        id=uuid4(),
        first_name="John",
        last_name="Developer",
        company="TechCorp",
        position="Senior Developer",
        source="test",
        embedding_dirty=True,
    )
    session.add(contact)
    await session.flush()

    # Create test messages
    messages = [
        Message(
            id=uuid4(),
            contact_id=contact.id,
            source="test",
            content="I'm a Python developer with 10 years of experience in machine learning and AI.",
            group_name="Tech Group",
            timestamp=datetime.now(timezone.utc),
        ),
        Message(
            id=uuid4(),
            contact_id=contact.id,
            source="test",
            content="Currently working on deep learning projects using TensorFlow and PyTorch.",
            group_name="Tech Group",
            timestamp=datetime.now(timezone.utc),
        ),
        Message(
            id=uuid4(),
            contact_id=contact.id,
            source="test",
            content="Looking for investors for my AI startup focused on natural language processing.",
            group_name="Investor Group",
            timestamp=datetime.now(timezone.utc),
        ),
    ]

    for msg in messages:
        session.add(msg)

    await session.commit()
    return contact, messages


@pytest.mark.asyncio
async def test_generate_message_embeddings(test_db_session):
    """Test message embedding generation."""
    contact, messages = await test_create_test_messages(test_db_session)
    session = test_db_session

    print("\n=== Testing Message Embedding Generation ===")
    print(f"Created {len(messages)} test messages")

    # Generate embeddings
    result = await maintenance_index_messages(batch_size=10, session=session, db_name="crm")

    print(f"✓ Embeddings generated: {result['processed']}")
    print(f"  Errors: {result['errors']}")
    print(f"  Tokens used: {result['tokens']}")

    assert result["processed"] > 0, "Should have processed at least one message"
    assert result["errors"] == 0, "Should have no errors"

    # Verify embeddings were created
    from sqlalchemy import select

    embeddings = await session.execute(select(MessageEmbedding))
    embeddings_list = embeddings.scalars().all()

    print(f"✓ Verified: {len(embeddings_list)} embeddings in database")
    assert len(embeddings_list) >= len(messages), "Should have embeddings for all messages"

    return contact, messages


@pytest.mark.asyncio
async def test_reindex_dirty_contacts(test_db_session):
    """Test contact re-indexing."""
    contact, _ = await test_create_test_messages(test_db_session)
    session = test_db_session

    print("\n=== Testing Contact Re-indexing ===")

    # Mark contact as dirty
    from sqlalchemy import select, update

    await session.execute(
        update(Contact)
        .where(Contact.id == contact.id)
        .values(embedding_dirty=True)
    )
    await session.commit()

    # Re-index
    result = await maintenance_reindex_dirty(batch_size=50, session=session, db_name="crm")

    print(f"✓ Contacts re-indexed: {result['processed']}")
    print(f"  Errors: {result['errors']}")
    print(f"  Skipped: {result['skipped']}")

    assert result["processed"] > 0, "Should have processed at least one contact"

    # Verify contact now has embedding
    refreshed = await session.get(Contact, contact.id)
    print(f"✓ Contact embedding created: {refreshed.embedding is not None}")
    assert refreshed.embedding is not None, "Contact should have embedding"


@pytest.mark.asyncio
async def test_semantic_search_with_embeddings(test_db_session):
    """Test semantic search using embeddings."""
    contact, messages = await test_create_test_messages(test_db_session)
    session = test_db_session

    print("\n=== Testing Semantic Search ===")

    # First generate embeddings
    await maintenance_index_messages(batch_size=10, session=session, db_name="crm")

    # Test semantic search
    search_query = SearchRequest(query="machine learning artificial intelligence", limit=10)

    try:
        result = await semantic_search(search_query, db=session)

        print(f"✓ Search results:")
        print(f"  Query: {result['query']}")
        print(f"  Contacts found: {len(result['contacts'])}")
        print(f"  Messages found: {len(result['messages'])}")

        if result["contacts"]:
            top_contact = result["contacts"][0]
            print(f"\n  Top contact:")
            print(f"    Name: {top_contact['first_name']} {top_contact['last_name']}")
            print(f"    Similarity: {top_contact['similarity']}")
            print(f"    Search type: {top_contact['search_type']}")
            if top_contact["evidence"]:
                print(f"    Evidence:")
                for ev in top_contact["evidence"][:2]:
                    print(f"      - {ev['text'][:80]}... (relevance: {ev['relevance']})")

        if result["messages"]:
            print(f"\n  Top messages:")
            for msg in result["messages"][:2]:
                print(f"    - {msg['content'][:80]}...")
                print(f"      Contact: {msg['contact_name']}, Similarity: {msg['similarity']}")

        assert len(result["contacts"]) > 0, "Should find at least one contact"
        assert len(result["messages"]) > 0, "Should find at least one message"

    except Exception as e:
        print(f"✗ Search failed: {e}")
        import traceback

        traceback.print_exc()
        raise


@pytest.mark.asyncio
async def test_keyword_search_fallback(test_db_session):
    """Test keyword search as fallback when semantic fails."""
    contact, messages = await test_create_test_messages(test_db_session)
    session = test_db_session

    print("\n=== Testing Keyword Search Fallback ===")

    # Search for something in contact name/company
    search_query = SearchRequest(query="TechCorp", limit=10)

    result = await semantic_search(search_query, db=session)

    print(f"✓ Keyword search for 'TechCorp':")
    print(f"  Contacts found: {len(result['contacts'])}")

    if result["contacts"]:
        for contact_result in result["contacts"]:
            print(f"    - {contact_result['first_name']} {contact_result['last_name']}")
            print(f"      Company: {contact_result['company']}")
            print(f"      Search type: {contact_result['search_type']}")

    assert len(result["contacts"]) > 0, "Should find contact by company name"


@pytest.mark.asyncio
async def test_combined_workflow():
    """Test complete workflow: create messages -> embed -> search."""
    print("\n=== Testing Complete Workflow ===")

    async with get_session(db_name="crm") as session:
        # 1. Create test data
        print("1. Creating test data...")
        contact, messages = await test_create_test_messages(session)
        print(f"   ✓ Created {len(messages)} messages for contact")

        # 2. Generate embeddings
        print("2. Generating embeddings...")
        embed_result = await maintenance_index_messages(batch_size=10, session=session, db_name="crm")
        print(f"   ✓ Generated {embed_result['processed']} embeddings")

        # 3. Re-index contact
        print("3. Re-indexing contact...")
        from sqlalchemy import update

        await session.execute(
            update(Contact)
            .where(Contact.id == contact.id)
            .values(embedding_dirty=True)
        )
        await session.commit()

        reindex_result = await maintenance_reindex_dirty(batch_size=50, session=session, db_name="crm")
        print(f"   ✓ Re-indexed {reindex_result['processed']} contacts")

        # 4. Perform search
        print("4. Testing semantic search...")
        search_query = SearchRequest(query="machine learning investment opportunity", limit=5)
        search_result = await semantic_search(search_query, db=session)

        print(f"   ✓ Found {len(search_result['contacts'])} contacts and {len(search_result['messages'])} messages")

        if search_result["contacts"]:
            print(f"\n   Top result:")
            c = search_result["contacts"][0]
            print(f"     Name: {c['first_name']} {c['last_name']}")
            print(f"     Similarity: {c['similarity']:.4f}")

        return True


if __name__ == "__main__":
    # Run tests with: pytest tests/test_embeddings_search.py -v -s
    pytest.main([__file__, "-v", "-s"])
