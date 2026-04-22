import asyncio
import sys
import os
import structlog
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.types import DialogFilter, Channel, Chat

sys.path.append(os.getcwd())

from src.connectors.telegram_connector import TelegramConnector
from src.db.database import get_session
from src.db.models import TrackedChannel, TrackedFolder
import sqlalchemy as sa

logger = structlog.get_logger()

# Folders to sync from Telegram to DB
TARGET_FOLDERS = [
    "BG Intel",
    "Crypto",
    "BG - Rent",
    "BG - Cars",
    "BG - Work",
    "BG - News"
]

# Mapping folders to DBs (as in docker-compose)
FOLDER_TO_DB = {
    "BG Intel": "crm",
    "Crypto": "crm_crypto",
    "BG - Rent": "crm_bg_rent",
    "BG - Cars": "crm_bg_cars",
    "BG - Work": "crm_bg_work",
    "BG - News": "crm_bg_news"
}

async def sync_folders():
    print("--- Syncing Telegram Folders to Database ---")
    
    # We'll use the main connector to fetch filters
    main_conn = TelegramConnector(db_name="crm")
    client = main_conn._get_client()
    
    async with client:
        if not await client.is_user_authorized():
            print("[Error] Telegram client not authorized!")
            return

        res = await client(GetDialogFiltersRequest())
        filters = res.filters if hasattr(res, 'filters') else res
        
        def get_title(f):
            t = getattr(f, 'title', '')
            return t.text if hasattr(t, 'text') else str(t)

        for folder_name in TARGET_FOLDERS:
            print(f"\n[*] Processing Folder: {folder_name}")
            target_db = FOLDER_TO_DB.get(folder_name, "crm")
            
            # Find the filter in Telegram
            tg_filter = next((f for f in filters if isinstance(f, DialogFilter) and get_title(f) == folder_name), None)
            
            if not tg_filter:
                print(f"  [!] Folder '{folder_name}' not found in Telegram. Skipping.")
                continue
            
            print(f"  [Info] Found {len(tg_filter.include_peers)} peers in folder. Syncing to DB: {target_db}")
            
            async with get_session(db_name=target_db) as session:
                # Ensure folder exists in DB
                res = await session.execute(sa.select(TrackedFolder).where(TrackedFolder.name == folder_name))
                db_folder = res.scalar_one_or_none()
                if not db_folder:
                    db_folder = TrackedFolder(name=folder_name, description=f"Tracked folder: {folder_name}")
                    session.add(db_folder)
                    await session.flush()
                
                for peer in tg_filter.include_peers:
                    try:
                        entity = await client.get_entity(peer)
                        tg_id = str(entity.id)
                        
                        # Check if already tracked
                        res = await session.execute(sa.select(TrackedChannel).where(TrackedChannel.telegram_id == tg_id))
                        existing = res.scalar_one_or_none()
                        
                        if not existing:
                            is_channel = isinstance(entity, Channel) and entity.broadcast
                            chan = TrackedChannel(
                                telegram_id=tg_id,
                                folder_id=db_folder.id,
                                title=getattr(entity, 'title', 'Unknown'),
                                username=getattr(entity, 'username', None),
                                entity_type="channel" if is_channel else "group",
                                is_active=True
                            )
                            session.add(chan)
                            print(f"    [+] Added: {chan.title} (@{chan.username})")
                        else:
                            print(f"    [-] Already exists: {existing.title}")
                            
                    except Exception as e:
                        print(f"    [Error] Failed to process peer: {e}")
                
                await session.commit()
    
    print("\n--- Folder Sync Finished ---")

if __name__ == "__main__":
    asyncio.run(sync_folders())
