import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.core.settings_service import SettingsService
from src.pipeline.tasks import deep_sync_telegram

async def main():
    print("🚀 Orchestrating Massive Historical Sync for 66 communities...")
    
    async with get_session() as session:
        settings = SettingsService(session)
        channels = await settings.get("telegram_channel_whitelist", [])
        chats = await settings.get("telegram_chat_whitelist", [])
        all_ids = list(set(channels + chats))
        
    if not all_ids:
        print("No channels found in whitelist.")
        return

    print(f"Total sources to sync: {len(all_ids)}")
    
    # Trigger in batches of 5 to not overload Telethon session immediately
    batch_size = 5
    for i in range(0, len(all_ids), batch_size):
        batch = all_ids[i:i+batch_size]
        print(f"Queuing batch {i//batch_size + 1}: {batch}")
        
        deep_sync_telegram.delay(
            chat_ids=[str(cid) for cid in batch],
            days=365,
            limit=10000  # High limit to get most of the year
        )
        
    print("\n✅ All sync tasks have been queued in Celery.")
    print("Monitor progress in Dashboard or via 'docker-compose logs -f worker'")

if __name__ == "__main__":
    asyncio.run(main())
