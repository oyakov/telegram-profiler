import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

DB_URL = "postgresql+asyncpg://crm:changeme@postgres:5432/crm"

async def main():
    print("Testing DB connection...")
    try:
        engine = create_async_engine(DB_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            print(f"Connection successful: {result.scalar()}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
