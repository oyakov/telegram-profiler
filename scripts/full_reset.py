
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
from sqlalchemy import delete

async def full_reset():
    async with get_session() as session:
        print("PERFORMING FULL SYNC STATE RESET...")
        await session.execute(delete(ChannelSyncState))
        await session.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(full_reset())
