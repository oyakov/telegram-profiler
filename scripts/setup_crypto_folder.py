import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.folders import EditPeerFoldersRequest
from telethon.tl.types import InputFolderPeer
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest
from telethon.tl.types import DialogFilter, TextWithEntities
from telethon.tl.functions.account import UpdateNotifySettingsRequest
from telethon.tl.types import InputPeerNotifySettings, InputNotifyPeer

sys.path.append(os.getcwd())
from src.core.config import get_settings

async def main():
    settings = get_settings()
    client = TelegramClient(f"sessions/{settings.telegram_session_name}", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    async with client:
        if not await client.is_user_authorized():
            print("Client is not authorized. Please log in first.")
            return

        print("Fetching archived dialogs...")
        archived_dialogs = await client.get_dialogs(folder=1)
        
        crypto_peers = []
        for d in archived_dialogs:
            if d.is_channel or d.is_group:
                crypto_peers.append(d.entity)
                
        print(f"Found {len(crypto_peers)} archived channels/groups to process.")
        
        if not crypto_peers:
            return

        print("1. Unarchiving them...")
        folder_peers = []
        for entity in crypto_peers:
            peer = await client.get_input_entity(entity)
            folder_peers.append(InputFolderPeer(peer=peer, folder_id=0))
            
        batch_size = 100
        for i in range(0, len(folder_peers), batch_size):
            await client(EditPeerFoldersRequest(folder_peers=folder_peers[i:i+batch_size]))
            
        print("2. Adding to 'Crypto' folder...")
        res = await client(GetDialogFiltersRequest())
        filters = res.filters if hasattr(res, 'filters') else res
        
        def get_title(f):
            t = getattr(f, 'title', '')
            return t.text if hasattr(t, 'text') else str(t)

        target_folder = next((f for f in filters if isinstance(f, DialogFilter) and get_title(f).lower() == "crypto"), None)
        
        input_peers = [await client.get_input_entity(e) for e in crypto_peers]
        
        if target_folder:
            from telethon.utils import get_peer_id
            current_ids = {get_peer_id(p) for p in target_folder.include_peers}
            added = 0
            for p in input_peers:
                if get_peer_id(p) not in current_ids:
                    target_folder.include_peers.append(p)
                    added += 1
            await client(UpdateDialogFilterRequest(id=target_folder.id, filter=target_folder))
            print(f"Added {added} peers to existing 'Crypto' folder.")
        else:
            print("Folder 'Crypto' not found. Creating it...")
            nid = max([f.id for f in filters if hasattr(f, 'id')] + [10]) + 1
            await client(UpdateDialogFilterRequest(id=nid, filter=DialogFilter(
                id=nid, title=TextWithEntities(text="Crypto", entities=[]), include_peers=input_peers, 
                pinned_peers=[], exclude_peers=[], emoticon="💰"
            )))
            
        print("3. Muting channels...")
        for peer in input_peers:
            try:
                await client(UpdateNotifySettingsRequest(
                    peer=InputNotifyPeer(peer),
                    settings=InputPeerNotifySettings(mute_until=2147483647)
                ))
            except Exception as e:
                print(f"Error muting: {e}")

        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
