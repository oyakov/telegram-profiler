import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.types import DialogFilter, PeerChannel, PeerChat, PeerUser

# Load config from env or hardcode
API_ID = 26593457
API_HASH = '1f6c406085a6a61cc9513364f7754d92'
SESSION_NAME = 'crm_session'

async def main():
    client = TelegramClient(f"sessions/{SESSION_NAME}", API_ID, API_HASH)
    async with client:
        print("Checking Telegram folders (Dialog Filters)...")
        result = await client(GetDialogFiltersRequest())
        filters = result.filters if hasattr(result, 'filters') else result
        
        target_folder = None
        for f in filters:
            if isinstance(f, DialogFilter):
                title = f.title.text if hasattr(f.title, 'text') else str(f.title)
                print(f"Found folder: '{title}' (ID: {f.id})")
                if title == "BG Intel":
                    target_folder = f
        
        if not target_folder:
            print("\nERROR: Folder 'BG Intel' not found. Make sure the name matches exactly.")
            return

        print(f"\nContents of '{target_folder.title}':")
        print("-" * 50)
        
        for peer in target_folder.include_peers:
            try:
                entity = await client.get_entity(peer)
                title = getattr(entity, 'title', getattr(entity, 'first_name', 'Unknown'))
                username = f"@{entity.username}" if getattr(entity, 'username', None) else "No username"
                print(f"- {title} ({username}) [ID: {entity.id}]")
            except Exception as e:
                print(f"- [Could not resolve peer: {peer}] Error: {e}")
        
        print("-" * 50)
        print(f"Total: {len(target_folder.include_peers)} items in folder.")

if __name__ == "__main__":
    asyncio.run(main())
