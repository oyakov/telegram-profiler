#!/usr/bin/env python3
"""Monitor embedding generation progress and statistics."""

import asyncio
import sys
from datetime import datetime, timezone
from typing import Optional
import time

async def monitor_progress(interval: int = 10, continuous: bool = False):
    """Monitor embedding generation progress."""
    from src.db.database import get_session
    from src.db.models import MessageEmbedding, Message
    from sqlalchemy import func, select

    last_count = 0
    start_time = time.time()
    checks = 0

    while True:
        checks += 1

        async with get_session(db_name="crm") as s:
            msgs = await s.execute(select(func.count(Message.id)))
            embs = await s.execute(select(func.count(MessageEmbedding.message_id.distinct())))

            total_msgs = msgs.scalar() or 0
            total_embs = embs.scalar() or 0
            coverage = (total_embs / total_msgs * 100) if total_msgs > 0 else 0

            new_embeddings = total_embs - last_count
            elapsed = time.time() - start_time

            if checks > 1:
                rate = new_embeddings / (elapsed / 60)  # embeddings per minute
                if rate > 0:
                    remaining = (total_msgs - total_embs) / rate
                    remaining_hours = remaining / 60
                    eta = datetime.fromtimestamp(time.time() + remaining * 60, tz=timezone.utc)
                else:
                    remaining_hours = float('inf')
                    eta = None
            else:
                rate = 0
                remaining_hours = float('inf')
                eta = None

            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{timestamp}]")
            print(f"  Embeddings: {total_embs:,} / {total_msgs:,} ({coverage:.2f}%)")
            print(f"  New since last check: {new_embeddings}")
            print(f"  Rate: {rate:.2f} embeddings/min")

            if remaining_hours < 1000:
                print(f"  ETA: {remaining_hours:.1f} hours")
                if eta:
                    print(f"  Completion: {eta.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            else:
                print(f"  ETA: >1000 hours (very long)")

            last_count = total_embs

        if not continuous:
            break

        await asyncio.sleep(interval)

async def main():
    """Run progress monitoring."""
    continuous = "--continuous" in sys.argv or "-c" in sys.argv
    interval = 30  # Check every 30 seconds

    try:
        await monitor_progress(interval=interval, continuous=continuous)
        return 0
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
