#!/usr/bin/env python3
"""
Load COMPLETE message history from all channels - no time limits.
Refactored to use PipelineService.
"""

import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.services.pipeline_service import PipelineService
from src.core.config import get_settings

async def main():
    """Load complete history from all channels."""
    settings = get_settings()
    db_name = os.getenv("POSTGRES_DB", settings.postgres_db)

    print("=" * 70)
    print(f"LOADING COMPLETE MESSAGE HISTORY FROM ALL CHANNELS (DB: {db_name})")
    print("(No time limits - fetching everything from the beginning)")
    print("=" * 70)

    service = PipelineService(db_name=db_name)
    result = await service.run_complete_history_load()

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if result["status"] == "success":
        print(f"Messages before:     {result['before']:,}")
        print(f"Messages after:      {result['after']:,}")
        print(f"Messages loaded:     {result['messages_loaded']:,}")
        print(f"New messages:        {result['new']:,}")
        print("=" * 70)
        return 0
    else:
        print(f"FAILED - {result.get('reason', result.get('error', 'Unknown error'))}")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
