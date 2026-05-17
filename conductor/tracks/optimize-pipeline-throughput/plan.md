# Implementation Plan: Pipeline Throughput Optimization

## Goal
Improve the performance and reliability of the message processing and embedding pipeline.

## Phase 1: Database Optimizations
- [ ] Implement Bulk Upsert logic in `ContactRepository` and `MessageRepository`.
- [ ] Optimize `MessageProcessor.process_batch` to use bulk operations for contacts and leads.

## Phase 2: AI Pipeline Enhancements
- [ ] Implement Redis-based global rate limiting for AI providers.
- [ ] Move AI extraction logging to background tasks.
- [ ] Add concurrency controls for batch processing tasks.

## Phase 3: Validation
- [ ] Benchmark processing speed before and after changes.
- [ ] Verify data consistency after bulk operations.