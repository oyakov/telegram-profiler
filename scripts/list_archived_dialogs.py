import asyncio
import os
import sys
from telethon import TelegramClient

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.core.config import get_settings
from src.db.database import get_session
from src.core.settings_service import SettingsService

async def main():
    settings = get_settings()
    client = TelegramClient(f"sessions/{settings.telegram_session_name}", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    async with get_session() as session:
        svc = SettingsService(session)
        whitelisted_channels = await svc.get("telegram_channel_whitelist", [])
        whitelisted_chats = await svc.get("telegram_chat_whitelist", [])
        all_whitelisted = set(whitelisted_channels + whitelisted_chats)

    async with client:
        if not await client.is_user_authorized():
            print("Client is not authorized. Please log in first.")
            return

        print("Fetching archived dialogs...")
        archived_dialogs = await client.get_dialogs(folder=1)
        
        if not archived_dialogs:
            print("No archived dialogs found.")
            return

        print(f"\n--- ARCHIVED WHITELISTED ITEMS ---")
        found_any = False
        for d in archived_dialogs:
            # Normalize ID for comparison
            # d.id is signed. Whitelist usually has the positive part (sometimes with 100 prefix)
            raw_id = abs(d.id)
            
            # Check for exact match or with 100 prefix stripped
            match = False
            if raw_id in all_whitelisted:
                match = True
            elif str(raw_id).startswith("100") and int(str(raw_id)[3:]) in all_whitelisted:
                match = True
            elif int("100" + str(raw_id)) in all_whitelisted:
                match = True

            if match:
                found_any = True
                entity_type = "Channel" if d.is_channel else "Group" if d.is_group else "User"
                print(f"- {d.title} (ID: {d.id}, Type: {entity_type})")
        
        if not found_any:
            print("None of the whitelisted items are currently archived.")

if __name__ == "__main__":
    asyncio.run(main())
