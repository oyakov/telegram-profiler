# Plan: Externalize Constants to Config

## Goal
Improve maintainability by removing hardcoded 'magic numbers' from the business logic and centralizing them in `src/core/config.py`.

## Tasks
1. [ ] Identify hardcoded thresholds in `src/api/routers/search.py` (e.g., 0.52 similarity).
2. [ ] Identify magic numbers in `src/pipeline/unified_processor.py`.
3. [ ] Add corresponding fields to `AppSettings` in `src/core/config.py`.
4. [ ] Refactor code to use `get_settings()` instead of literals.
