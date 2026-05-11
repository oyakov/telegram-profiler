#!/usr/bin/env python3
"""
Optimized batch embedding generation.
Processes messages in multiple efficient batches with progress tracking.
"""

import asyncio
import sys
from datetime import datetime, timezone
import structlog

logger = structlog.get_logger()


async def generate_all_embeddings_optimized(
    batch_size: int = 500,
    max_batches: int = None,
    db_name: str = "crm"
):
    """Generate embeddings for all messages with optimized batching."""
    from src.pipeline.unified_processor import maintenance_index_messages
    from src.db.database import get_session
    from src.db.models import MessageEmbedding, Message
    from sqlalchemy import func, select

    print("=" * 70)
    print("OPTIMIZED BATCH EMBEDDING GENERATION")
    print("=" * 70)

    total_stats = {
        "total_processed": 0,
        "total_errors": 0,
        "total_tokens": 0,
        "batches": 0,
        "start_time": datetime.now(timezone.utc),
    }

    batch_num = 0

    while True:
        batch_num += 1
        if max_batches and batch_num > max_batches:
            print(f"\nReached max batches ({max_batches})")
            break

        # Check current coverage
        async with get_session(db_name=db_name) as s:
            msgs = await s.execute(select(func.count(Message.id)))
            embs = await s.execute(
                select(func.count(MessageEmbedding.message_id.distinct()))
            )
            total_msgs = msgs.scalar() or 0
            total_embs = embs.scalar() or 0

        if total_embs >= total_msgs:
            print(f"\nAll messages have embeddings! Coverage: 100%")
            break

        coverage = (total_embs / total_msgs * 100) if total_msgs > 0 else 0
        remaining = total_msgs - total_embs

        print(f"\n[Batch {batch_num}]")
        print(f"  Progress: {total_embs:,} / {total_msgs:,} ({coverage:.2f}%)")
        print(f"  Remaining: {remaining:,}")
        print(f"  Processing batch of {batch_size} messages...")

        try:
            result = await maintenance_index_messages(
                batch_size=batch_size, db_name=db_name
            )

            total_stats["total_processed"] += result["processed"]
            total_stats["total_errors"] += result["errors"]
            total_stats["total_tokens"] += result["tokens"]
            total_stats["batches"] += 1

            if result["processed"] == 0:
                print(f"  [OK] Batch complete (0 messages - might all be done)")
                break

            print(f"  [OK] Processed: {result['processed']:,}")
            if result["errors"] > 0:
                print(f"      Errors: {result['errors']}")
            print(f"      Tokens: {result['tokens']:,}")

        except Exception as e:
            print(f"  [ERROR] Batch failed: {e}")
            total_stats["total_errors"] += 1
            break

    elapsed = (datetime.now(timezone.utc) - total_stats["start_time"]).total_seconds()

    # Final summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total batches: {total_stats['batches']}")
    print(f"Total processed: {total_stats['total_processed']:,}")
    print(f"Total errors: {total_stats['total_errors']}")
    print(f"Total tokens: {total_stats['total_tokens']:,}")
    print(f"Duration: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    # Final coverage check
    async with get_session(db_name=db_name) as s:
        msgs = await s.execute(select(func.count(Message.id)))
        embs = await s.execute(select(func.count(MessageEmbedding.message_id.distinct())))
        total_msgs = msgs.scalar() or 0
        total_embs = embs.scalar() or 0

    coverage = (total_embs / total_msgs * 100) if total_msgs > 0 else 0
    print(f"\nFinal coverage: {total_embs:,} / {total_msgs:,} ({coverage:.2f}%)")
    print("=" * 70)

    return 0 if total_stats["total_errors"] == 0 else 1


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate embeddings for all messages"
    )
    parser.add_argument("--batch-size", type=int, default=500, help="Messages per batch")
    parser.add_argument("--max-batches", type=int, default=None, help="Max batches to run")
    parser.add_argument("--db", default="crm", help="Database name")

    args = parser.parse_args()

    return await generate_all_embeddings_optimized(
        batch_size=args.batch_size, max_batches=args.max_batches, db_name=args.db
    )


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
