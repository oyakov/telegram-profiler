import asyncio
import sys
import os
import structlog
from datetime import datetime, timezone

sys.path.append(os.getcwd())

from src.db.database import get_session, get_engine
from src.core.settings_service import SettingsService
import sqlalchemy as sa

logger = structlog.get_logger()

DATABASES = [
    "crm",
    "crm_crypto",
    "crm_bg_rent",
    "crm_bg_cars",
    "crm_bg_work",
    "crm_bg_news"
]

async def trigger():
    print("--- Enabling Sync and Triggering Processing ---")
    
    for db_name in DATABASES:
        print(f"\n[*] Processing Database: {db_name}")
        async with get_session(db_name=db_name) as session:
            svc = SettingsService(session)
            await svc.set("telegram_sync_enabled", True)
            print(f"  [OK] telegram_sync_enabled = True")
    
    # Now trigger the Celery tasks
    # We can use the orchestrate tasks from src.pipeline.tasks
    from src.pipeline.tasks import orchestrate_multi_db_sync, orchestrate_multi_db_message_processing
    
    print("\n[*] Dispatching Orchestration Tasks...")
    try:
        res_sync = orchestrate_multi_db_sync.delay()
        print(f"  [OK] Sync orchestration dispatched (Task ID: {res_sync.id})")
        
        res_proc = orchestrate_multi_db_message_processing.delay()
        print(f"  [OK] Processing orchestration dispatched (Task ID: {res_proc.id})")
    except Exception as e:
        print(f"  [Error] Failed to dispatch tasks: {e}")
        print("  [!] Make sure Redis is running and reachable.")

if __name__ == "__main__":
    asyncio.run(trigger())
