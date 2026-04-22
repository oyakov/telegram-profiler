"""Script to add NEW target channels to whitelist and trigger 1-year history sync."""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.core.settings_service import SettingsService
from src.connectors.telegram_connector import TelegramConnector

NEW_CHANNELS = [
    "beograd_service",
    "afisha_rs",
    "vrachivserbii",
    "russmedicserbia",
    "SrbijaRS",
    "balkan_hub",
    "letimizserbii",
    "dotcoffeebar",
    "rade_traffic_chat"
]

async def setup_and_sync():
    # Ensure POSTGRES_HOST is set to localhost if running from host
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"

    print(f"Starting setup for {len(NEW_CHANNELS)} new channels...")
    
    async with get_session() as session:
        svc = SettingsService(session)
        
        # 1. Update Whitelist
        current_whitelist = await svc.get("telegram_channel_whitelist", [])
        updated_whitelist = list(set(current_whitelist + NEW_CHANNELS))
        
        await svc.set(
            "telegram_channel_whitelist", 
            updated_whitelist, 
            value_type="json",
            description="Whitelisted Telegram channels for monitoring",
            category="telegram"
        )
        await session.commit()
        print(f"Updated telegram_channel_whitelist. Total channels now: {len(updated_whitelist)}")

    # 2. Trigger Deep Sync (1 year)
    print("\nStarting deep sync (1 year) for new channels...")
    connector = TelegramConnector()
    # 50k limit per channel, 1 year back
    result = await connector.deep_sync(chat_ids=NEW_CHANNELS, limit=50000, days=365)
    
    print(f"\nDeep Sync Completed!")
    print(f"Total messages fetched from new channels: {result.messages_fetched}")
    if result.errors:
        print(f"Errors encountered: {result.errors}")

if __name__ == "__main__":
    asyncio.run(setup_and_sync())
