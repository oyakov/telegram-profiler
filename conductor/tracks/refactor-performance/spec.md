# Specification: Performance Optimization (AI & Pipeline)

## Context
Currently, the AI extraction pipeline processes text chunks sequentially and runs different types of extraction (contacts vs. ad buyers) one after another. This leads to high latency, especially for long messages or batches.

## Goals
- Reduce end-to-end processing time for messages.
- Maximize LLM throughput using parallel requests.
- Implement concurrency control to avoid rate limits.

## Technical Requirements
- **Asyncio Parallelism:** Use `asyncio.gather` for chunk processing in `ExtractionService`.
- **Parallel Extraction Types:** Run contact extraction and ad buyer detection concurrently in `MessageProcessor`.
- **Semaphore Control:** Introduce a semaphore to limit the number of concurrent LLM calls.

## Affected Components
- `src/ai/services.py` (`ExtractionService`)
- `src/pipeline/unified_processor.py` (`MessageProcessor`)
- `src/ai/llm_client.py` (Potential global semaphore)
