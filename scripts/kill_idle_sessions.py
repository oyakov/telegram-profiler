import asyncio
import os
import sys
from sqlalchemy import text

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session

async def kill_idle():
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    async with get_session() as session:
        # Kill idle in transaction
        print("Terminating 'idle in transaction' sessions...")
        await session.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction'"))
        await session.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(kill_idle())
