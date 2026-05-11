#!/usr/bin/env python3
"""
Deep load all available message history from all tracked channels.
Loads complete history without limits for better search capability.
"""

import asyncio
import sys
from datetime import datetime, timedelta
import structlog

from src.db.database import get_session
from src.db.models import TrackedChannel, Message
from src.connectors.telegram_connector import TelegramConnector
from sqlalchemy import select, func

logger = structlog.get_logger()

async def count_messages_in_channel(session, telegram_id: str) -> int:
    """Count messages already loaded for a channel."""
    result = await session.execute(
        select(func.count(Message.id)).where(Message.group_id == telegram_id)
    )
    return result.scalar() or 0

async def deep_load_channel(connector: TelegramConnector, channel: TrackedChannel, session) -> dict:
    """
    Deep load all available history for a single channel.

    Args:
        connector: Telegram connector
        channel: Channel to load
        session: DB session for counting

    Returns:
        Dict with load stats
    """
    telegram_id = channel.telegram_id
    entity_type = channel.entity_type

    before_count = await count_messages_in_channel(session, telegram_id)

    logger.info(
        "deep_load_start",
        telegram_id=telegram_id,
        type=entity_type,
        existing_messages=before_count
    )

    try:
        # Load last 90 days with no limit on messages
        count = await connector.sync_deep_history_chunk(
            telegram_id=telegram_id,
            entity_type=entity_type,
            limit=5000  # Large limit to get as much as possible
        )

        # Check total after load
        after_count = await count_messages_in_channel(session, telegram_id)
        new_messages = after_count - before_count

        logger.info(
            "deep_load_complete",
            telegram_id=telegram_id,
            loaded=count,
            new_messages=new_messages,
            total_messages=after_count
        )

        return {
            "telegram_id": telegram_id,
            "type": entity_type,
            "status": "success",
            "before": before_count,
            "after": after_count,
            "loaded": count,
            "new": new_messages
        }

    except Exception as e:
        logger.error(
            "deep_load_failed",
            telegram_id=telegram_id,
            error=str(e)
        )
        return {
            "telegram_id": telegram_id,
            "type": entity_type,
            "status": "failed",
            "error": str(e),
            "before": before_count
        }

async def main():
    """Load all available history from all channels."""

    print("=" * 70)
    print("DEEP LOADING ALL CHANNEL HISTORY")
    print("=" * 70)

    async with get_session(db_name="crm") as session:
        # Check Telegram auth
        connector = TelegramConnector(db_name="crm")
        is_auth = await connector.is_authorized()

        if not is_auth:
            print("[ERROR] Telegram not authenticated!")
            return 1

        print("[OK] Telegram authenticated\n")

        # Get all active channels
        result = await session.execute(
            select(TrackedChannel).where(TrackedChannel.is_active == True)
        )
        channels = result.scalars().all()

        print(f"Found {len(channels)} active channels")
        print("Starting deep load...\n")

        stats = {
            "total": len(channels),
            "success": 0,
            "failed": 0,
            "total_messages_before": 0,
            "total_messages_after": 0,
            "total_new_messages": 0,
            "results": []
        }

        # Load each channel
        for i, channel in enumerate(channels, 1):
            print(f"[{i}/{len(channels)}] Loading {channel.telegram_id} ({channel.entity_type})...")

            result = await deep_load_channel(connector, channel, session)
            stats["results"].append(result)

            if result["status"] == "success":
                stats["success"] += 1
                stats["total_messages_before"] += result["before"]
                stats["total_messages_after"] += result["after"]
                stats["total_new_messages"] += result["new"]
                print(f"        OK - {result['new']} new messages (total: {result['after']})")
            else:
                stats["failed"] += 1
                print(f"        FAILED - {result.get('error', 'Unknown error')}")

        # Commit all changes
        await session.commit()

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Channels processed:  {stats['success']}/{stats['total']}")
        print(f"Failed:              {stats['failed']}")
        print(f"Messages before:     {stats['total_messages_before']:,}")
        print(f"Messages after:      {stats['total_messages_after']:,}")
        print(f"Total new:           {stats['total_new_messages']:,}")
        print("=" * 70)

        # Show channels with most new messages
        print("\nTop 10 channels by new messages:")
        sorted_results = sorted(
            [r for r in stats['results'] if r['status'] == 'success'],
            key=lambda x: x['new'],
            reverse=True
        )
        for i, r in enumerate(sorted_results[:10], 1):
            print(f"  {i}. {r['telegram_id']}: +{r['new']} messages")

        return 0 if stats['failed'] == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
