# Specification: System Flexibility & Final Consolidation

## Context
Lead scoring parameters and target channel IDs are currently hardcoded in the pipeline. Additionally, the Dashboard still needs to be aligned with the newly modularized API.

## Goals
- Externalize all business logic constants to the `settings` table.
- Finalize the migration of the Dashboard to the new API.
- Remove all deprecated files and scripts.

## Technical Requirements
- **Dynamic Configuration:** Use `SettingsService` to fetch scoring weights and channel filters.
- **Frontend Refactor:** Update Streamlit components to use Pydantic schemas and `/api/leads/...` endpoints.
- **Code Cleanup:** Purge unused files identified in the consolidation track.

## Affected Components
- `src/pipeline/unified_processor.py`
- `dashboard/app.py`
- `src/core/settings_service.py`
