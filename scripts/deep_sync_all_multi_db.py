import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List

sys.path.append(os.getcwd())

from src.connectors.telegram_connector import TelegramConnector
from src.db.database import get_session, get_engine
from src.db.models import TrackedChannel
import sqlalchemy as sa

async def get_tracked_databases() -> List[str]:
    """Get all databases starting with 'crm_'."""
    engine = get_engine("postgres", use_pooling=False)
    async with engine.connect() as conn:
        res = await conn.execute(sa.text("SELECT datname FROM pg_database WHERE datname LIKE 'crm_%'"))
        return [row[0] for row in res.fetchall()]

async def deep_sync_db(db_name: str, days: int, limit: int):
    """Perform deep sync for all active channels in a specific database."""
    print(f"\n>>> DEEP SYNCING DATABASE: {db_name} (Depth: {days} days)")
    
    async with get_session(db_name=db_name) as session:
        # Get active channels
        res = await session.execute(
            sa.select(TrackedChannel.telegram_id, TrackedChannel.title)
            .where(TrackedChannel.is_active == True)
        )
        channels = res.all()
    
    if not channels:
        print(f"  - No active channels found in {db_name}.")
        return

    print(f"  - Found {len(channels)} active channels. Starting sync...")
    
    connector = TelegramConnector(db_name=db_name)
    # Convert IDs to int for better Telethon resolution
    chat_ids = []
    for c in channels:
        try:
            chat_ids.append(int(c[0]))
        except ValueError:
            chat_ids.append(c[0])
    
    # We run deep_sync. Note: TelegramConnector.deep_sync handles its own session inside.
    # It also handles TelegramClient connection.
    try:
        result = await connector.deep_sync(chat_ids=chat_ids, limit=limit, days=days)
        print(f"  - Sync completed for {db_name}:")
        print(f"    - Messages fetched: {result.messages_fetched}")
        if result.errors:
            print(f"    - Errors encountered: {len(result.errors)}")
            for err in result.errors[:5]: # Show first 5 errors
                print(f"      - {err}")
    except Exception as e:
        print(f"  - Fatal error syncing {db_name}: {e}")

async def main():
    # Configuration
    DAYS = 735 # 2 years + buffer
    LIMIT = 50000 # High limit to ensure full history
    
    dbs = await get_tracked_databases()
    print(f"Discovered {len(dbs)} databases: {', '.join(dbs)}")
    
    for db in dbs:
        await deep_sync_db(db, DAYS, LIMIT)
    
    print("\nAll databases processed!")

if __name__ == "__main__":
    asyncio.run(main())
