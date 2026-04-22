import asyncio
import os
import sys
from sqlalchemy import select, func

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import MessageEmbedding, Contact

async def main():
    async with get_session() as session:
        # Count message embeddings
        res_msg = await session.execute(select(func.count(MessageEmbedding.id)))
        msg_count = res_msg.scalar()
        
        # Count contacts with embeddings
        res_con = await session.execute(select(func.count(Contact.id)).where(Contact.embedding.isnot(None)))
        con_count = res_con.scalar()
        
        print(f"--- Database Stats ---")
        print(f"Message Embeddings: {msg_count}")
        print(f"Contacts with Embeddings: {con_count}")

if __name__ == "__main__":
    asyncio.run(main())
