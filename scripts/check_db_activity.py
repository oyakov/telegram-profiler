import asyncio
import os
import sys
from sqlalchemy import text

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session

async def check_activity():
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    async with get_session() as session:
        # Check for locks or long running queries
        res = await session.execute(text("""
            SELECT pid, now() - query_start AS duration, query, state 
            FROM pg_stat_activity 
            WHERE state != 'idle' AND query NOT LIKE '%pg_stat_activity%';
        """))
        rows = res.all()
        print("\nActive Queries:")
        for row in rows:
            print(f"PID: {row[0]}, Duration: {row[1]}, Query: {row[2][:100]}, State: {row[3]}")

if __name__ == "__main__":
    asyncio.run(check_activity())
