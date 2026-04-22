import asyncio
import os
import sys
import structlog
from typing import List, Dict
import sqlalchemy as sa

sys.path.append(os.getcwd())

from src.connectors.telegram_connector import TelegramConnector
from src.db.database import get_session
from src.core.settings_service import SettingsService
from telethon.tl.types import Channel

logger = structlog.get_logger()

# Mapping of DB to theme and target folder
EXPANSION_CONFIG = [
    {
        "db": "crm",
        "theme": "Белград сербия",
        "folder": "BG Intel",
        "keywords": ["Белград", "Сербия", "ВНЖ Сербия", "Релокация Сербия", "Помощь Сербия", "Русские в Сербии"],
        "min_participants": 600
    },
    {
        "db": "crm_crypto",
        "theme": "криптовалюты трейдинг",
        "folder": "Crypto",
        "keywords": ["Crypto", "Bitcoin", "Ethereum", "Solana", "DEX", "Trading", "Криптовалюта", "Трейдинг"],
        "min_participants": 1000
    },
    {
        "db": "crm_bg_rent",
        "theme": "белград аренда недвижимость",
        "folder": "BG - Rent",
        "keywords": ["Белград аренда", "Квартиры Белград", "Beograd rent", "Serbia real estate", "Снять квартиру Белград", "Недвижимость Сербия"],
        "min_participants": 100
    },
    {
        "db": "crm_bg_news",
        "theme": "белград сербия новости",
        "folder": "BG - News",
        "keywords": ["Сербия новости", "Белград новости", "Balkan news", "Сербия сегодня", "Srbija Danas", "Blic", "N1 Srbija"],
        "min_participants": 600
    },
    {
        "db": "crm_bg_work",
        "theme": "белград работы",
        "folder": "BG - Work",
        "keywords": ["Работа Белград", "Работа Сербия", "Jobs Serbia", "IT Serbia", "Вакансии Сербия", "Remote Serbia"],
        "min_participants": 100
    },
    {
        "db": "crm_bg_cars",
        "theme": "белград машины покупка аренда",
        "folder": "BG - Cars",
        "keywords": ["Машины Белград", "Авто Сербия", "Auto Beograd", "Rent a car Belgrade", "Polovni Automobili", "Купить авто Сербия"],
        "min_participants": 50
    }
]

async def discover_for_db(config: Dict):
    db_name = config["db"]
    folder_name = config["folder"]
    keywords = config["keywords"]
    min_participants = config["min_participants"]
    
    print(f"\n[*] Starting Expansion for Database: {db_name} (Folder: {folder_name})")
    conn = TelegramConnector(db_name=db_name)
    
    # Get current tracked IDs
    async with get_session(db_name=db_name) as session:
        settings = SettingsService(session)
        tracked_channels = await settings.get("telegram_channel_whitelist", [])
        tracked_chats = await settings.get("telegram_chat_whitelist", [])
        tracked_ids = set(tracked_channels + tracked_chats)

    all_results = []
    for kw in keywords:
        print(f"  [Find] Searching for: '{kw}'...")
        results = await conn.search_communities(kw, limit=20)
        all_results.extend(results)
    
    unique_results = {res['id']: res for res in all_results}.values()
    print(f"  [Info] Found {len(unique_results)} unique candidates. Filtering...")

    joined_now = 0
    for item in unique_results:
        chat_id = item['id']
        title = item['title']
        participants = item['participants']
        username = item['username']
        
        if participants < min_participants:
            continue
            
        if chat_id in tracked_ids or (isinstance(chat_id, int) and -1000000000000 - chat_id in tracked_ids):
            continue
            
        print(f"  [Add] High potential: {title} (@{username}) - {participants} members")
        
        # Join and add to folder
        success, entity = await conn.join_community(chat_id, username=username, folder_name=folder_name)
        
        if success and entity:
            joined_now += 1
            # Add to DB whitelist
            async with get_session(db_name=db_name) as session:
                settings = SettingsService(session)
                is_channel = isinstance(entity, Channel) and entity.broadcast
                key = "telegram_channel_whitelist" if is_channel else "telegram_chat_whitelist"
                current = await settings.get(key, [])
                if entity.id not in current:
                    current.append(entity.id)
                    await settings.set(key, current, value_type="json")
                
                # Also add to TrackedChannel model for sync
                from src.db.models import TrackedChannel, TrackedFolder
                res = await session.execute(sa.select(TrackedFolder).where(TrackedFolder.name == folder_name))
                folder = res.scalar_one_or_none()
                
                chan = TrackedChannel(
                    telegram_id=str(entity.id),
                    folder_id=folder.id if folder else None,
                    title=getattr(entity, 'title', 'Unknown'),
                    username=getattr(entity, 'username', None),
                    entity_type="channel" if is_channel else "group",
                    is_active=True
                )
                session.add(chan)
                await session.commit()
            
            print(f"    [OK] Joined and registered in {db_name}.")
            
        # Respect limits
        await asyncio.sleep(10)
        if joined_now >= 5: # Limit per DB per run to avoid spam detection
            print(f"  [Limit] Reached session limit (5) for {db_name}. Moving on.")
            break

async def main():
    if sys.platform == "win32":
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except Exception: pass

    print("--- Starting Multi-DB Thematic Expansion ---")
    for config in EXPANSION_CONFIG:
        try:
            await discover_for_db(config)
        except Exception as e:
            print(f"  [Error] Error processing {config['db']}: {str(e).encode('ascii', 'ignore').decode()}")
    print("\n--- Expansion Finished ---")

if __name__ == "__main__":
    asyncio.run(main())
