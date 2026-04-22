import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.types import DialogFilter, Channel
from sqlalchemy import select, delete

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import TrackedFolder, TrackedChannel
from src.core.config import get_settings

async def main():
    db_name = os.getenv("POSTGRES_DB", "crm")
    folder_name = os.getenv("TARGET_FOLDER", "BG Intel")
    
    settings = get_settings()
    session_name = settings.telegram_session_name
    if db_name == "crm_crypto":
        session_name = f"{session_name}_crm_crypto"
    elif db_name != "crm":
        session_name = f"{session_name}_{db_name}"

    client = TelegramClient(f"sessions/{session_name}", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    async with client:
        print(f"Fetching folder '{folder_name}' from Telegram for cleanup...")
        result = await client(GetDialogFiltersRequest())
        filters = result.filters if hasattr(result, 'filters') else result
        
        target_folder_data = None
        for f in filters:
            if isinstance(f, DialogFilter):
                title = f.title.text if hasattr(f.title, 'text') else str(f.title)
                if title == folder_name:
                    target_folder_data = f
                    break
        
        if not target_folder_data:
            print(f"Error: Folder '{folder_name}' not found.")
            return

        print(f"Found {len(target_folder_data.include_peers)} items in Telegram folder.")
        
        valid_tg_ids = set()
        for peer in target_folder_data.include_peers:
            try:
                entity = await client.get_entity(peer)
                valid_tg_ids.add(str(entity.id))
            except Exception:
                continue

        # Sync Database
        print(f"\nUpdating database {db_name} (RESTRICTED TO FOLDER ONLY)...")
        async with get_session(db_name=db_name) as session:
            # 1. Get folder ID
            res = await session.execute(select(TrackedFolder).where(TrackedFolder.name == folder_name))
            folder = res.scalar_one_or_none()
            if not folder:
                print(f"No TrackedFolder '{folder_name}' in DB. Run sync first.")
                return
            
            # 2. Mark channels NOT in the Telegram folder as inactive (or delete them)
            # We'll mark as inactive for safety
            res = await session.execute(
                select(TrackedChannel).where(TrackedChannel.folder_id == folder.id)
            )
            db_channels = res.scalars().all()
            
            deactivated = 0
            active = 0
            for chan in db_channels:
                if chan.telegram_id not in valid_tg_ids:
                    chan.is_active = False
                    deactivated += 1
                else:
                    chan.is_active = True
                    active += 1
            
            await session.commit()
            
            print(f"Success! Cleanup complete for {db_name}:")
            print(f"- Still Active: {active}")
            print(f"- Deactivated: {deactivated}")

if __name__ == "__main__":
    asyncio.run(main())
