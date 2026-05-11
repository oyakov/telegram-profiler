#!/usr/bin/env python3
"""Simple semantic search test using direct database queries."""

import asyncio
import sys
from datetime import datetime, timezone

async def test_simple_search():
    """Test semantic search with simple database queries."""
    from src.db.database import get_session
    from src.db.models import MessageEmbedding, Message, Contact
    from src.ai.analysis import generate_embedding
    from sqlalchemy import func, select

    print("=" * 70)
    print("SIMPLE SEMANTIC SEARCH TEST")
    print("=" * 70)

    async with get_session(db_name="crm") as session:
        # Check embedding coverage
        msgs = await session.execute(select(func.count(Message.id)))
        embs = await session.execute(
            select(func.count(MessageEmbedding.message_id.distinct()))
        )
        total_msgs = msgs.scalar() or 0
        total_embs = embs.scalar() or 0
        coverage = (total_embs / total_msgs * 100) if total_msgs > 0 else 0

        print(f"\nDatabase Status:")
        print(f"  Total messages: {total_msgs:,}")
        print(f"  With embeddings: {total_embs:,} ({coverage:.2f}%)")

        if total_embs == 0:
            print("\n[WARNING] No embeddings found. Run embedding generation first.")
            print("  Command: python scripts/batch_embed_all_messages.py")
            return 1

        print(f"\n[OK] Found {total_embs} embeddings to search\n")

        # Test queries
        test_queries = [
            "machine learning AI",
            "business investment",
            "technology software",
            "networking community",
        ]

        print(f"{'Query':<30} {'Similar Messages':<20}")
        print("-" * 50)

        for query_text in test_queries:
            try:
                # Generate embedding for query
                query_embedding = await generate_embedding(query_text)

                # Simple cosine distance search
                results = await session.execute(
                    select(
                        Message.id,
                        Message.content,
                        MessageEmbedding.embedding.cosine_distance(query_embedding).label(
                            "distance"
                        ),
                    )
                    .join(Message, Message.id == MessageEmbedding.message_id)
                    .order_by("distance")
                    .limit(5)
                )

                rows = results.fetchall()
                found = len([r for r in rows if r[2] < 0.52])  # Count within threshold

                print(f"{query_text:<30} {found:<20}")

                if found > 0:
                    print(f"  Top result: {rows[0][1][:60]}...")

            except Exception as e:
                print(f"{query_text:<30} ERROR: {str(e)[:15]}")

        print("\n" + "=" * 70)
        return 0


async def main():
    """Main entry point."""
    try:
        return await test_simple_search()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
