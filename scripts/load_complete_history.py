#!/usr/bin/env python3
"""
Load COMPLETE message history from all channels - no time limits.
Fetches ALL available messages from the very beginning.
"""

import asyncio
import sys
from datetime import datetime, timezone
import structlog

logger = structlog.get_logger()

async def load_complete_history(connector, channels: list, session) -> dict:
    """
    Load COMPLETE history from all channels.
    Uses sync with massive limit to fetch everything.
    """
    from sqlalchemy import select, func
    from src.db.models import Message

    # Count before
    before_result = await session.execute(select(func.count(Message.id)))
    before_count = before_result.scalar() or 0

    print(f"Messages before load: {before_count:,}")

    try:
        # Call sync with VERY high limit (1 million) to get all messages
        # sync() will iterate through all channels with this limit
        result = await connector.sync(
            chat_ids=[int(ch.telegram_id) for ch in channels],
            limit=1000000,  # Load up to 1M per channel
            offset_date=None  # No time restriction - load everything
        )

        # Count after
        after_result = await session.execute(select(func.count(Message.id)))
        after_count = after_result.scalar() or 0
        new_messages = after_count - before_count

        logger.info(
            "complete_load_complete",
            messages_fetched=result.messages_fetched,
            new_messages=new_messages,
            total_messages=after_count
        )

        return {
            "status": "success",
            "before": before_count,
            "after": after_count,
            "loaded": result.messages_fetched,
            "new": new_messages
        }

    except Exception as e:
        logger.error(
            "complete_load_failed",
            error=str(e)
        )
        return {
            "status": "failed",
            "error": str(e),
            "before": before_count
        }


async def main():
    """Load complete history from all channels."""
    from src.db.database import get_session
    from src.db.models import TrackedChannel
    from src.connectors.telegram_connector import TelegramConnector
    from sqlalchemy import select

    print("=" * 70)
    print("LOADING COMPLETE MESSAGE HISTORY FROM ALL CHANNELS")
    print("(No time limits - fetching everything from the beginning)")
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
        print("Starting complete history load (may take a while)...\n")

        # Load complete history from ALL channels at once
        result = await load_complete_history(connector, channels, session)

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        if result["status"] == "success":
            print(f"Messages before:     {result['before']:,}")
            print(f"Messages after:      {result['after']:,}")
            print(f"Messages loaded:     {result['loaded']:,}")
            print(f"New messages:        {result['new']:,}")
            print("=" * 70)
            return 0
        else:
            print(f"FAILED - {result.get('error', 'Unknown error')}")
            print("=" * 70)
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
