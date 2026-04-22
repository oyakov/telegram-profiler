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

async def sync_new_in_db(db_name: str, days: int, limit: int):
    """Perform deep sync only for channels added in the last 2 hours."""
    print(f"\n[*] Processing Database: {db_name}")
    
    # Threshold for "new" channels: added in the last 24 hours
    threshold = datetime.now(timezone.utc) - timedelta(hours=24)
    
    async with get_session(db_name=db_name) as session:
        # Get active channels added recently
        res = await session.execute(
            sa.select(TrackedChannel.telegram_id, TrackedChannel.title)
            .where(TrackedChannel.is_active == True)
            .where(TrackedChannel.created_at >= threshold)
        )
        channels = res.all()
    
    if not channels:
        print(f"  - No new channels added recently in {db_name}.")
        return

    print(f"  - Found {len(channels)} NEW channels. Starting 2-year sync...")
    
    connector = TelegramConnector(db_name=db_name)
    chat_ids = []
    for c in channels:
        try:
            chat_ids.append(int(c[0]))
        except ValueError:
            chat_ids.append(c[0])
    
    try:
        result = await connector.deep_sync(chat_ids=chat_ids, limit=limit, days=days)
        print(f"  - [OK] Sync completed: {result.messages_fetched} messages fetched.")
    except Exception as e:
        print(f"  - [Error] Sync failed for {db_name}: {e}")

async def main():
    print("--- Starting Targeted Sync for NEW Channels ---")
    DAYS = 735
    LIMIT = 20000
    
    dbs = await get_tracked_databases()
    for db in dbs:
        await sync_new_in_db(db, DAYS, LIMIT)
    
    print("\n[Done] New channels history sync finished.")

if __name__ == "__main__":
    asyncio.run(main())
