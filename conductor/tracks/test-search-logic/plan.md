# Plan: Search Logic Integrity Tests

## Goal
Ensure that hybrid search (semantic + keyword) works as expected and respects configurable thresholds.

## Tasks
1. [ ] Create `tests/unit/test_search_logic.py`.
2. [ ] Test semantic search with distances above/below threshold.
3. [ ] Test keyword fallback trigger.
4. [ ] Verify `_extract_evidence_batch` correctly limits results per contact.
5. [ ] Test hnsw.ef_search setting injection.
