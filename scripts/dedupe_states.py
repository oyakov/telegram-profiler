
import asyncio
import os
import sys
from uuid import UUID

# Environment setup
os.environ['POSTGRES_HOST'] = 'postgres'
os.environ['POSTGRES_PASSWORD'] = 'changeme'

sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import ChannelSyncState
from sqlalchemy import select, delete, desc

async def cleanup():
    async with get_session() as session:
        print("Starting sync state deduplication...")
        
        # Get all unique channel IDs
        res = await session.execute(select(ChannelSyncState.channel_id).distinct())
        channel_ids = [r[0] for r in res.all()]
        
        for cid in channel_ids:
            # Get all states for this channel ordered by start time
            res = await session.execute(
                select(ChannelSyncState)
                .where(ChannelSyncState.channel_id == cid)
                .order_by(desc(ChannelSyncState.started_at))
            )
            states = res.scalars().all()
            
            if len(states) > 1:
                print(f"Channel {cid}: keeping {states[0].id}, deleting {len(states)-1} old states")
                # Keep the first one (newest), delete others
                to_delete = [s.id for s in states[1:]]
                await session.execute(
                    delete(ChannelSyncState).where(ChannelSyncState.id.in_(to_delete))
                )
        
        await session.commit()
        print("Deduplication complete.")

if __name__ == "__main__":
    asyncio.run(cleanup())
