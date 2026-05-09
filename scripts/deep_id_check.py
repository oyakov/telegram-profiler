
import asyncio
import os
import sys

# Environment setup
os.environ['POSTGRES_HOST'] = 'postgres'
os.environ['POSTGRES_PASSWORD'] = 'changeme'

sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import TrackedChannel, Message, ChannelSyncState, TrackedFolder
from sqlalchemy import select, func

async def run():
    async with get_session() as session:
        # Folder ID for "IT"
        folder_id = '8fde39ed-5391-4c5c-b2f9-57ed37f8a2e6'
        
        # 1. Get channels in this folder
        res = await session.execute(
            select(TrackedChannel).where(TrackedChannel.folder_id == folder_id)
        )
        channels = res.scalars().all()
        
        print(f"--- FOLDER IT CHANNELS ---")
        for ch in channels:
            print(f"ID: {ch.id} | TG_ID: '{ch.telegram_id}' (len={len(str(ch.telegram_id))}) | Title: {ch.title}")

        # 2. Get samples from messages table
        print(f"\n--- MESSAGES TABLE SAMPLES ---")
        msg_res = await session.execute(
            select(Message.group_id, Message.group_name, func.count(Message.id))
            .group_by(Message.group_id, Message.group_name)
            .order_by(func.count(Message.id).desc())
            .limit(10)
        )
        for row in msg_res.all():
            print(f"Group_ID in DB: '{row[0]}' (len={len(str(row[0])) if row[0] else 0}) | Name: {row[1]} | Count: {row[2]}")

        # 3. Check for specific IT channel ID match
        it_id = '1528034935'
        print(f"\n--- SPECIFIC MATCH CHECK for '{it_id}' ---")
        match_res = await session.execute(
            select(func.count(Message.id)).where(Message.group_id == it_id)
        )
        print(f"Direct match for '{it_id}': {match_res.scalar()}")
        
        prefixed_it_id = f"-100{it_id}"
        match_res = await session.execute(
            select(func.count(Message.id)).where(Message.group_id == prefixed_it_id)
        )
        print(f"Prefixed match for '{prefixed_it_id}': {match_res.scalar()}")

if __name__ == "__main__":
    asyncio.run(run())
