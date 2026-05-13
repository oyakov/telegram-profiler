# Track: Refactor: Cleanup & Admin Utilities

## Specification
Move database creation and schema initialization logic out of the core `database.py` module to maintain a clean runtime API.

## Objectives
- Move `ensure_database_exists` and `init_database_schema` to `src/db/utils.py`.
- Update any references to these utilities.

## Success Criteria
- [x] `src/db/database.py` contains only session/engine management.
- [x] `src/db/utils.py` contains administrative helpers.
