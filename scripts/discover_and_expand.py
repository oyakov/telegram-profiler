import asyncio
import os
import sys
import structlog

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.connectors.telegram_connector import TelegramConnector
from src.db.database import get_session
from src.core.settings_service import SettingsService

logger = structlog.get_logger()

KEYWORDS = [
    "Белград", "Сербия", "Beograd", "Serbia", "БГ", 
    "Релокация Сербия", "ВНЖ Сербия", "Работа Сербия", 
    "Аренда Белград", "Белград Чат", "Сербия Чат"
]

MIN_PARTICIPANTS = 1000

async def main():
    print(f"🚀 Starting Global Discovery for Belgrade & Serbia (Min members: {MIN_PARTICIPANTS})")
    conn = TelegramConnector()
    
    # 1. Get current tracking lists to avoid duplicates
    async with get_session() as session:
        settings = SettingsService(session)
        tracked_channels = await settings.get("telegram_channel_whitelist", [])
        tracked_chats = await settings.get("telegram_chat_whitelist", [])
        tracked_ids = set(tracked_channels + tracked_chats)

    discovered_count = 0
    joined_count = 0
    
    all_results = []
    
    # 2. Search for each keyword
    for kw in KEYWORDS:
        print(f"🔍 Searching for: '{kw}'...")
        results = await conn.search_communities(kw, limit=50)
        all_results.extend(results)
    
    # Deduplicate results from different keywords
    unique_results = {res['id']: res for res in all_results}.values()
    
    # 3. Process candidates
    for item in unique_results:
        chat_id = item['id']
        title = item['title']
        participants = item['participants']
        username = item['username']
        
        # Filter by size and current tracking
        if participants < MIN_PARTICIPANTS:
            continue
            
        if chat_id in tracked_ids or (isinstance(chat_id, int) and -1000000000000 - chat_id in tracked_ids):
            continue
            
        print(f"✨ Found new large community: {title} (@{username}) - {participants} members")
        discovered_count += 1
        
        # 4. Join, Mute, Folder, and Add to Whitelist
        # Note: join_community already handles Mute and Folder
        success, entity = await conn.join_community(chat_id, username=username)
        
        if success and entity:
            joined_count += 1
            print(f"   ✅ Joined and added to 'BG Intel' folder.")
            
            # Add to CRM whitelist
            async with get_session() as session:
                settings = SettingsService(session)
                from telethon.tl.types import Channel
                is_channel = isinstance(entity, Channel) and entity.broadcast
                
                key = "telegram_channel_whitelist" if is_channel else "telegram_chat_whitelist"
                current = await settings.get(key, [])
                if entity.id not in current:
                    current.append(entity.id)
                    await settings.set(key, current, value_type="json")
                    await session.commit()
                    print(f"   📥 Added to CRM tracking: {key}")
            
            # Trigger Historical Sync (via API call or directly via Task if possible)
            # For simplicity in this script, we'll assume the background 'deep_sync' will pick it up 
            # or we can trigger it via the existing tasks module
            try:
                from src.pipeline.tasks import deep_sync_telegram
                deep_sync_telegram.delay(chat_ids=[str(entity.id)], days=365, limit=5000)
                print(f"   ⏳ 1-year history sync queued.")
            except Exception as e:
                print(f"   ⚠️ Could not queue sync: {e}")
                
        # Sleep to avoid Telegram Flood Limits
        await asyncio.sleep(5)

    print(f"\n--- Discovery Finished ---")
    print(f"Total discovered: {discovered_count}")
    print(f"Total joined and synced: {joined_count}")

if __name__ == "__main__":
    asyncio.run(main())
