# Plan: Deduplication & Merge Logic Tests

## Goal
Ensure that `ContactRepository.merge_contact_fields` correctly aggregates data without loss or corruption.

## Tasks
1. [ ] Create `tests/unit/test_deduplication.py`.
2. [ ] Test basic field merging (null -> value).
3. [ ] Test list merging (interests, skills) with uniqueness.
4. [ ] Test JSON object merging (facts).
5. [ ] Test notes accumulation.
6. [ ] Verify `embedding_dirty` flag is set correctly.
