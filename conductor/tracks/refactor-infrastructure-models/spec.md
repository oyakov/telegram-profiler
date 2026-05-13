# Track: Refactor: Modular Models & Async Infrastructure

## Specification
The goal is to improve code maintainability by splitting the monolithic `models.py` into a package structure and standardizing async Celery tasks.

## Objectives
- Split `src/db/models.py` into `src/db/models/` package.
- Implement `AsyncDBTask` base class for Celery.
- Ensure all models are exportable from `src/db/models/__init__.py`.

## Success Criteria
- [x] `src/db/models/` contains logical sub-modules.
- [x] Celery tasks inherit from `AsyncDBTask`.
- [x] Project imports continue to work correctly.
