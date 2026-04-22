import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.core.settings_service import SettingsService

async def main():
    async with get_session() as session:
        settings = SettingsService(session)
        channels = await settings.get("telegram_channel_whitelist", [])
        chats = await settings.get("telegram_chat_whitelist", [])
        
        print("\n--- CURRENT WHITELIST ---")
        print(f"Channels: {channels}")
        print(f"Chats: {chats}")

if __name__ == "__main__":
    asyncio.run(main())
