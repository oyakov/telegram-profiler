import asyncio
import sys
import os

sys.path.append(os.getcwd())

from src.db.database import ensure_database_exists, init_database_schema

DATABASES = [
    "crm",
    "crm_crypto",
    "crm_bg_rent",
    "crm_bg_cars",
    "crm_bg_work",
    "crm_bg_news"
]

async def main():
    print("--- Re-initializing All Databases ---")
    for db_name in DATABASES:
        try:
            print(f"\n[*] Processing: {db_name}")
            await ensure_database_exists(db_name)
            await init_database_schema(db_name)
            print(f"[OK] {db_name} is ready.")
        except Exception as e:
            print(f"[Error] Failed to initialize {db_name}: {e}")
    print("\n--- All Databases Processed ---")

if __name__ == "__main__":
    asyncio.run(main())
