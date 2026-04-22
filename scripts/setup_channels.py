"""Script to add target channels to whitelist and trigger deep history sync."""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.core.settings_service import SettingsService
from src.pipeline.tasks import deep_sync_telegram

TARGET_CHANNELS = [
    "serbska_baraholka",
    "serbia_self_it",
    "avito_serbia",
    "rabotavbelgrade"
]

async def setup_and_sync():
    print(f"Starting setup for {len(TARGET_CHANNELS)} channels...")
    
    async with get_session() as session:
        svc = SettingsService(session)
        
        # 1. Update Whitelist
        current_whitelist = await svc.get("telegram_channel_whitelist", [])
        new_whitelist = list(set(current_whitelist + TARGET_CHANNELS))
        
        await svc.set(
            "telegram_channel_whitelist", 
            new_whitelist, 
            value_type="json",
            description="Whitelisted Telegram channels for monitoring",
            category="telegram"
        )
        await session.commit()
        print(f"Updated telegram_channel_whitelist: {new_whitelist}")

    # 2. Trigger Deep Sync Task (90 days history)
    print("Triggering deep sync task for history (90 days)...")
    # Note: We can trigger the Celery task directly if Redis is up, 
    # but since we are running locally without docker-compose verified, 
    # we'll just print instructions or try to call the connector directly if preferred.
    
    # Attempt to trigger via Celery delay
    try:
        task = deep_sync_telegram.delay(chat_ids=TARGET_CHANNELS, limit=1000, days=90)
        print(f"Task queued successfully! Task ID: {task.id}")
    except Exception as e:
        print(f"Could not queue task via Celery: {e}")
        print("Falling back to direct execution...")
        from src.connectors.telegram_connector import TelegramConnector
        connector = TelegramConnector()
        result = await connector.deep_sync(chat_ids=TARGET_CHANNELS, limit=1000, days=90)
        print(f"Direct sync completed: {result.messages_fetched} messages fetched.")

if __name__ == "__main__":
    asyncio.run(setup_and_sync())
