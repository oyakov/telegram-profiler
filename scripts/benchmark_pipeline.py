import asyncio
import time
import sys
import os
from unittest.mock import patch, AsyncMock, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline.unified_processor import MessageProcessor
from src.db.models import Message

async def mock_extract(text, extraction_type=None, **kwargs):
    # Simulate LLM latency per extraction type
    print(f"  Starting extraction: {extraction_type}")
    await asyncio.sleep(0.5)
    print(f"  Finished extraction: {extraction_type}")
    return [], {"time_ms": 500}

async def benchmark_pipeline():
    # Mock session
    session = AsyncMock()
    processor = MessageProcessor(session)
    
    # Create a dummy message
    msg = Message(
        id="00000000-0000-0000-0000-000000000001",
        content="This is a test message for parallel processing benchmarking.",
        raw_json={"is_channel": True},
        source="telegram"
    )
    
    print(f"--- Benchmarking MessageProcessor.process_batch (Contacts + Ad Buyers) ---")
    
    with patch("src.ai.services.ExtractionService.extract", side_effect=mock_extract):
        start_time = time.perf_counter()
        stats = await processor.process_batch([msg], force_ad_detection=True)
        end_time = time.perf_counter()
        
        total_duration = end_time - start_time
        print(f"Total duration: {total_duration:.4f} seconds")
        print(f"Stats: {stats}")
        
        # In parallel mode, total duration should be close to 0.5s
        # In sequential mode, it would be 1.0s (0.5s for contacts + 0.5s for buyers)
        if total_duration < 0.7:
            print("\nSUCCESS: Extraction types processed in parallel!")
        else:
            print("\nFAILURE: Processing seems sequential.")

if __name__ == "__main__":
    asyncio.run(benchmark_pipeline())
