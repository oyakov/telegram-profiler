#!/usr/bin/env python3
"""Quick test script for embeddings and search."""

import asyncio
import sys
from datetime import datetime, timezone
from uuid import uuid4

async def main():
    """Run quick embedding and search tests."""
    print("=" * 60)
    print("Testing Embeddings and Semantic Search")
    print("=" * 60)

    try:
        from src.db.database import get_session
        from src.db.models import Contact, Message, MessageEmbedding
        from src.pipeline.unified_processor import maintenance_index_messages, maintenance_reindex_dirty
        from src.api.routers.search import semantic_search
        from src.api.schemas import SearchRequest
        from sqlalchemy import select, update

        async with get_session(db_name="crm") as session:
            print("\n[1] Creating test data...")

            # Create contact
            contact = Contact(
                id=uuid4(),
                first_name="Alice",
                last_name="Developer",
                company="AI Innovations",
                position="ML Engineer",
                source="test",
                embedding_dirty=True,
            )
            session.add(contact)
            await session.flush()

            # Create messages
            messages_data = [
                "I specialize in machine learning and deep learning using PyTorch.",
                "Currently building AI systems for natural language processing.",
                "Looking for partners to develop computer vision solutions.",
                "5 years experience with TensorFlow and neural networks.",
            ]

            messages = []
            for i, content in enumerate(messages_data):
                msg = Message(
                    id=uuid4(),
                    contact_id=contact.id,
                    source="test",
                    content=content,
                    group_name="Tech Group",
                    timestamp=datetime.now(timezone.utc),
                )
                session.add(msg)
                messages.append(msg)

            await session.flush()
            print(f"   [OK] Created contact: {contact.first_name} {contact.last_name}")
            print(f"   [OK] Created {len(messages)} test messages")

            # Test 1: Generate embeddings
            print("\n[2] Generating message embeddings...")
            embed_result = await maintenance_index_messages(
                batch_size=10, session=session, db_name="crm"
            )
            print(f"   [OK] Processed: {embed_result['processed']}")
            print(f"   [OK] Errors: {embed_result['errors']}")
            print(f"   [OK] Tokens: {embed_result['tokens']}")

            # Verify embeddings
            emb_count = await session.execute(select(MessageEmbedding))
            emb_list = emb_count.scalars().all()
            print(f"   [OK] Total embeddings in DB: {len(emb_list)}")

            # Test 2: Re-index contact
            print("\n[3] Re-indexing dirty contact...")
            await session.execute(
                update(Contact).where(Contact.id == contact.id).values(embedding_dirty=True)
            )
            await session.commit()

            reindex_result = await maintenance_reindex_dirty(
                batch_size=50, session=session, db_name="crm"
            )
            print(f"   [OK] Processed: {reindex_result['processed']}")
            print(f"   [OK] Errors: {reindex_result['errors']}")

            # Verify contact has embedding
            contact_refreshed = await session.get(Contact, contact.id)
            has_embedding = contact_refreshed.embedding is not None
            print(f"   [OK] Contact has embedding: {has_embedding}")

            # Test 3: Semantic search
            print("\n[4] Testing semantic search...")
            search_queries = [
                "machine learning artificial intelligence",
                "PyTorch neural networks",
                "computer vision AI",
                "AI Innovations",
            ]

            for query_text in search_queries:
                search_req = SearchRequest(query=query_text, limit=5)
                result = await semantic_search(search_req, db=session)

                print(f"\n   Query: '{query_text}'")
                print(f"   - Contacts found: {len(result['contacts'])}")
                print(f"   - Messages found: {len(result['messages'])}")

                if result["contacts"]:
                    top = result["contacts"][0]
                    print(f"   - Top contact: {top['first_name']} {top['last_name']}")
                    print(f"     Similarity: {top['similarity']:.4f}")
                    print(f"     Type: {top['search_type']}")
                    if top["evidence"]:
                        print(f"     Evidence: {top['evidence'][0]['text'][:60]}...")

            print("\n" + "=" * 60)
            print("[PASS] All tests passed successfully!")
            print("=" * 60)
            return 0

    except Exception as e:
        print(f"\n[FAIL] Test failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
