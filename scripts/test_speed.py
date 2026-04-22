import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

DB_URL = "postgresql+asyncpg://crm:changeme@postgres:5432/crm"

async def main():
    engine = create_async_engine(DB_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Fetching one user...")
        query_top = text("SELECT contact_id FROM messages GROUP BY contact_id LIMIT 1")
        row = (await session.execute(query_top)).fetchone()
        cid = row.contact_id
        
        print(f"Testing analyze for CID: {cid}")
        start = time.monotonic()
        query_msgs = text("SELECT content FROM messages WHERE contact_id = :contact_id LIMIT 20")
        res = await session.execute(query_msgs, {"contact_id": cid})
        msgs = res.fetchall()
        print(f"Fetched {len(msgs)} msgs in {time.monotonic()-start:.3f}s")

if __name__ == "__main__":
    asyncio.run(main())
