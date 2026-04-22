import asyncio
import os
import sys
from sqlalchemy import select, func

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import Message

async def list_channel_stats():
    # Ensure POSTGRES_HOST is set to localhost if running from host
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    async with get_session() as session:
        query = (
            select(Message.group_id, Message.group_name, func.count(Message.id))
            .where(Message.group_id.is_not(None))
            .group_by(Message.group_id, Message.group_name)
            .order_by(func.count(Message.id).desc())
        )
        result = await session.execute(query)
        rows = result.all()
        
        print("\nChannel Message Counts:")
        print("-" * 50)
        for group_id, group_name, count in rows:
            print(f"{group_name or 'Unknown'} (ID: {group_id}): {count} messages")
        print("-" * 50)
        print(f"Total channel messages: {sum(row[2] for row in rows)}")

if __name__ == "__main__":
    asyncio.run(list_channel_stats())
