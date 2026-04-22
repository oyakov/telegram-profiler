import asyncio
import time
import sys
import os
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai.services import ExtractionService

async def mock_structured_extraction(*args, **kwargs):
    # Simulate LLM latency
    await asyncio.sleep(0.5)
    return {
        "data": {"items": [{"first_name": "Test"}]},
        "model": "gpt-4o",
        "provider": "openai",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "processing_time_ms": 500
    }

async def benchmark():
    service = ExtractionService()
    
    # Large text that will be split into 5 chunks (assuming max_tokens=10)
    # We'll force small chunks to test parallelism
    text = "Word " * 100 
    
    print(f"--- Benchmarking ExtractionService.extract with 5 parallel chunks ---")
    
    with patch("src.ai.services.structured_extraction", side_effect=mock_structured_extraction):
        start_time = time.perf_counter()
        # Mocking _chunk_text to return 5 chunks
        with patch.object(ExtractionService, '_chunk_text', return_value=["chunk"] * 5):
            items, metadata = await service.extract(text, max_chunk_tokens=10)
        end_time = time.perf_counter()
        
        total_duration = end_time - start_time
        print(f"Total duration: {total_duration:.4f} seconds")
        print(f"Items found: {len(items)}")
        print(f"Metadata: {metadata}")
        
        # In parallel mode, total duration should be close to 0.5s (single chunk latency)
        # In sequential mode, it would be 2.5s (0.5s * 5)
        if total_duration < 1.0:
            print("\nSUCCESS: Chunks processed in parallel!")
        else:
            print("\nFAILURE: Processing seems sequential.")

if __name__ == "__main__":
    asyncio.run(benchmark())
