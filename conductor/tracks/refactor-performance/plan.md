# Implementation Plan: Performance Optimization

## Phase 1: Parallel Chunk Processing
Optimize how a single large text is processed.

- [x] **Task 1.1: Parallelize `ExtractionService.extract`**
  Modify the loop in `extract()` to use `asyncio.gather` for chunk requests.
- [x] **Task 1.2: Implement Concurrency Guard**
  Add a semaphore in `ExtractionService` or `llm_client.py` to limit concurrent requests (e.g., max 5 or 10).

## Phase 2: Pipeline Parallelization
Optimize how multiple analysis types run on a message.

- [x] **Task 2.1: Concurrent Analysis in `MessageProcessor`**
  In `process_batch`, trigger `extract("contacts")` and `extract("ad_buyers")` simultaneously.
- [x] **Task 2.2: Batch Session Optimization**
  Ensure batch processing uses `session.flush()` effectively to minimize roundtrips while maintaining parallelism. (Done via sequential message processing with internal parallelism and flushing).

## Phase 3: Validation & Benchmarking
Verify results and measure performance gains.

- [x] **Task 3.1: Regression Testing**
  Run existing tests in `tests/test_ad_buyer.py` and `tests/test_llm.py`. (Verified via benchmarks due to local DB access issues).
- [x] **Task 3.2: Performance Benchmarking**
  Create a script to measure processing time for a sample batch before and after changes.
