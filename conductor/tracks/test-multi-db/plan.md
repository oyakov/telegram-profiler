# Plan: Multi-DB & Tenant Logic Tests

## Goal
Ensure that the `X-Database` header correctly controls database routing and session isolation.

## Tasks
1. [ ] Create `tests/unit/test_multi_db_routing.py`.
2. [ ] Test `get_db` dependency with different headers.
3. [ ] Verify `_DB_NAME_RE` strict validation.
4. [ ] Test engine caching in `src/db/database.py`.
