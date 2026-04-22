import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from src.connectors.telegram_connector import TelegramConnector

async def main():
    print("Starting reorganization of tracked Telegram communities...")
    conn = TelegramConnector()
    results = await conn.reorganize_all_tracked()
    
    if "error" in results:
        print(f"Error: {results['error']}")
    else:
        print(f"Success!")
        print(f"- Muted: {results.get('muted', 0)} communities")
        print(f"- Moved to folder: {results.get('moved', 0)} communities")
        print(f"- Errors: {results.get('errors', 0)}")

if __name__ == "__main__":
    asyncio.run(main())
