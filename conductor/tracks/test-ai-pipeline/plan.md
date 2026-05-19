# Plan: AI Extraction Pipeline Tests

## Goal
Ensure `UnifiedProcessor` handles various AI extraction scenarios, including failures and low-confidence results.

## Tasks
1. [ ] Create `tests/unit/test_unified_processor.py`.
2. [ ] Test message length filtering (< 10 chars).
3. [ ] Test `lead_threshold` enforcement.
4. [ ] Test LLM failure isolation (one message failing doesn't stop the batch).
5. [ ] Verify that `is_extracted` is only set on success.
