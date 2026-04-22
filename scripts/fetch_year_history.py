"""Script to fetch 1 year of history for all target channels."""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.connectors.telegram_connector import TelegramConnector

TARGET_CHANNELS = [
    "serbska_baraholka",
    "serbia_self_it",
    "avito_serbia",
    "rabotavbelgrade",
    1553186701,  # Сербия TravelAsk
    1753396658   # Русские в Белграде
]

async def fetch_year_history():
    # Ensure POSTGRES_HOST is set to localhost if running from host
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    print(f"Starting deep sync (1 year) for {len(TARGET_CHANNELS)} channels...")
    
    connector = TelegramConnector()
    # We use a large limit to ensure we get as much as possible within 1 year
    # 50,000 per channel should cover most cases, though Telegram might rate limit
    result = await connector.deep_sync(chat_ids=TARGET_CHANNELS, limit=50000, days=365)
    
    print(f"\nDeep Sync Completed!")
    print(f"Total messages fetched: {result.messages_fetched}")
    if result.errors:
        print(f"Errors encountered: {result.errors}")

if __name__ == "__main__":
    asyncio.run(fetch_year_history())
