import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.types import DialogFilter, Channel

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.core.config import get_settings

async def main():
    settings = get_settings()
    client = TelegramClient(f"sessions/{settings.telegram_session_name}", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    async with client:
        print("Reading all folders from Telegram...")
        res = await client(GetDialogFiltersRequest())
        filters = res.filters if hasattr(res, 'filters') else res
        
        def get_title(f):
            t = getattr(f, 'title', '')
            return t.text if hasattr(t, 'text') else str(t)

        # Filter BG folders and Crypto
        target_filters = [
            f for f in filters 
            if isinstance(f, DialogFilter) and (get_title(f).startswith("BG") or get_title(f) == "Crypto")
        ]
        
        print(f"Found {len(target_filters)} target folders.\n")
        
        for tf in target_filters:
            folder_title = get_title(tf)
            print(f"=== FOLDER: {folder_title} ===")
            header = f"{'Title':<40} | {'Username':<25} | {'ID':<15}"
            print(header)
            print("-" * 85)
            
            for peer in tf.include_peers:
                try:
                    entity = await client.get_entity(peer)
                    title = getattr(entity, 'title', getattr(entity, 'first_name', 'Unknown'))
                    username = f"@{entity.username}" if getattr(entity, 'username', None) else "No username"
                    
                    # Safe print for Windows terminal
                    safe_title = str(title).encode('ascii', 'backslashreplace').decode('ascii')[:40]
                    safe_username = str(username).encode('ascii', 'backslashreplace').decode('ascii')
                    
                    print(f"{safe_title:<40} | {safe_username:<25} | {entity.id}")
                except Exception as e:
                    print(f"Could not resolve peer {peer}: {e}")
            print("\n")

if __name__ == "__main__":
    asyncio.run(main())
