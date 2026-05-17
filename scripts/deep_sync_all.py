import asyncio
import os
import sys
from sqlalchemy import select

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.core.config import get_settings
from src.pipeline.tasks import deep_sync_telegram
from src.db.models import TrackedChannel

async def main():
    settings = get_settings()
    db_name = os.getenv("POSTGRES_DB", settings.postgres_db)
    
    print(f"\n--- TRIGGERING FULL HISTORY SYNC (DB: {db_name}) ---")
    
    async with get_session(db_name=db_name) as session:
        res = await session.execute(select(TrackedChannel.telegram_id).where(TrackedChannel.is_active == True))
        all_ids = [row[0] for row in res.all()]
        
        if not all_ids:
            print("No tracked channels/groups found in this database.")
            return

        print(f"Found {len(all_ids)} targets. Dispatching deep sync tasks to Celery...")

        # Dispatch in smaller batches to avoid overwhelming the worker
        batch_size = 5
        for i in range(0, len(all_ids), batch_size):
            batch = all_ids[i:i+batch_size]
            task = deep_sync_telegram.delay(
                chat_ids=batch,
                limit=10000, # 10k messages per target
                days=730,    # 2 years
                db_name=db_name
            )
            print(f"  Queued batch {i//batch_size + 1}: {batch} (Task: {task.id})")

    print(f"Done dispatching for {db_name}. Worker will process them in background.")

if __name__ == "__main__":
    asyncio.run(main())
