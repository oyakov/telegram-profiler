import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from src.connectors.telegram_connector import TelegramConnector

async def test_deep_sync():
    conn = TelegramConnector()
    print("Starting deep sync for 2094624699 (Новости Белграда)...")
    res = await conn.deep_sync(chat_ids=['2094624699'], days=7, limit=100)
    print(f"Result: {res}")

if __name__ == "__main__":
    asyncio.run(test_deep_sync())
