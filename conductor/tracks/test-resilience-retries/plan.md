# Plan: Resilience & Retry Logic Tests

## Goal
Verify that the `telegram_retry` logic correctly handles transient failures and respects the maximum attempt limit.

## Tasks
1. [ ] Create `tests/unit/test_resilience.py`.
2. [ ] Mock Telethon client to raise `ConnectionError` and verify retries in `TelegramSyncService`.
3. [ ] Mock Telethon client to raise `RPCError` and verify retries.
4. [ ] Verify that final failure is raised after 3 attempts.
5. [ ] Verify that `FloodWaitError` behavior remains correct (or is explicitly handled).
