import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest
from telethon.tl.types import DialogFilter, InputPeerChannel, InputPeerChat

# Load config
API_ID = 26593457
API_HASH = '1f6c406085a6a61cc9513364f7754d92'
SESSION_NAME = 'crm_session'

async def main():
    client = TelegramClient(f"sessions/{SESSION_NAME}", API_ID, API_HASH)
    async with client:
        print("Fetching dialogs...")
        dialogs = await client.get_dialogs()
        
        # Filter Belgrade-related channels we already have
        target_names = [
            "Русские в Белграде", "Барахолка", "Сербия", "Белград", 
            "РАБОТА В СЕРБИИ", "Медицина в Сербии", "Plavi Voz", "Workshop",
            "Apartments", "DOT COFFEE", "Balkan HUB"
        ]
        
        peers_to_add = []
        for d in dialogs:
            if d.is_channel or d.is_group:
                if any(name.lower() in d.name.lower() for name in target_names):
                    print(f"Adding to list: {d.name}")
                    input_peer = await client.get_input_entity(d.entity)
                    peers_to_add.append(input_peer)
        
        if not peers_to_add:
            print("No peers found.")
            return

        print(f"Total to move: {len(peers_to_add)}")

        # Get existing filters
        res = await client(GetDialogFiltersRequest())
        filters = res.filters if hasattr(res, 'filters') else res
        
        folder_name = "Belgrade Intel"
        existing_filter = next((f for f in filters if isinstance(f, DialogFilter) and f.title == folder_name), None)
        
        new_id = existing_filter.id if existing_filter else (max([f.id for f in filters if hasattr(f, 'id')] + [10]) + 1)
        
        # Create fresh filter object
        # IMPORTANT: Peers must be TLObjects (InputPeerChannel, InputPeerChat, etc)
        new_filter = DialogFilter(
            id=new_id,
            title=folder_name,
            include_peers=peers_to_add,
            pinned_peers=[],
            exclude_peers=[],
            emoticon="🧠"
        )
        
        try:
            await client(UpdateDialogFilterRequest(id=new_id, filter=new_filter))
            print(f"SUCCESS: Folder '{folder_name}' updated!")
        except Exception as e:
            print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
