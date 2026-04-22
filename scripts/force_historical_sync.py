import asyncio
import os
import sys
from sqlalchemy import select

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.db.database import get_session, get_engine
import sqlalchemy as sa
from src.db.models import TrackedChannel
from src.pipeline.tasks import deep_sync_telegram

async def get_all_dbs():
    engine = get_engine("postgres", use_pooling=False)
    async with engine.connect() as conn:
        res = await conn.execute(sa.text("SELECT datname FROM pg_database WHERE datname LIKE 'crm_%'"))
        return [row[0] for row in res.fetchall()]

async def main():
    dbs = await get_all_dbs()
    print(f"Found {len(dbs)} databases: {dbs}")
    
    for db in dbs:
        print(f"\n>>> FORCING SYNC FOR DATABASE: {db}")
        async with get_session(db_name=db) as session:
            res = await session.execute(select(TrackedChannel).where(TrackedChannel.is_active == True))
            channels = res.scalars().all()
            
            if not channels:
                print(f"  - No active channels found in {db}")
                continue
                
            channel_ids = [str(c.telegram_id) for c in channels]
            print(f"  - Found {len(channel_ids)} channels. Triggering deep sync...")
            
            # Use chunks of 50 to avoid huge task payloads
            chunk_size = 50
            for i in range(0, len(channel_ids), chunk_size):
                chunk = channel_ids[i:i + chunk_size]
                deep_sync_telegram.delay(
                    chat_ids=chunk,
                    limit=10000,
                    days=365,
                    db_name=db
                )
    
    print("\nAll tasks dispatched!")

if __name__ == "__main__":
    asyncio.run(main())
