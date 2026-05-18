# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- **PII sanitization in auth logs**: `TelegramAuthService.sign_in` and `sign_in_2fa` now log only
  `error_type=type(e).__name__` — phone numbers, FloodWait countdowns, and session hashes no longer
  appear in structured log output.
- **Contact mass-assignment protection**: `ContactService.update_contact` enforces a server-side
  field whitelist (`_ALLOWED_UPDATE_FIELDS`). Internal columns (`lead_score`, `is_lead`, `source`,
  `embedding`, `id`, etc.) are silently ignored even if the schema were to be bypassed.
- **UUID validation before DB queries**: `get_contact`, `update_contact`, and `delete_contact` now
  parse the `contact_id` string with `UUID(...)` before issuing ORM queries. Invalid IDs raise
  `ValueError → 404` instead of asyncpg `DataError → 500`.
- **Campaign preview input sanitization**: `CampaignPreviewRequest.sample_contact` is validated
  against an allowlist of known field names; unknown keys and values exceeding 255 characters are
  stripped at schema-validation time.
- **Message length caps**: `CampaignCreate.message` and `CampaignPreviewRequest.message` now enforce
  `max_length=4096` to prevent unbounded string allocation (DoS).
- **Generic campaign delivery error**: `CampaignService` stores `"Internal delivery error"` in
  `CampaignMessage.error_message` instead of raw exception text that could expose stack traces.
- **Generic 404 messages in leads router**: `HTTPException` detail strings are now static
  (`"Contact not found"`, `"Search not found"`) — exception text no longer echoed to API clients.
- **Campaign service error_message sanitization**: delivery failures store `"Delivery provider failed"`
  rather than raw exception strings in the database.
- **Upload path traversal prevention**: `import_excel` task uses `Path.resolve()` on both the root
  and the user-supplied path so symlinks pointing outside `/app/uploads/` are rejected.

### Fixed
- **`sync_orchestrator` on wrong Celery queue**: the task was routed to the `processing` queue but
  issues Telegram API calls; corrected to `connectors`.
- **`run_saved_search` hardcoded limit**: `LeadService.run_saved_search` previously capped results
  at 50 regardless of filter settings, causing `last_result_count` to always be ≤ 50. It now
  respects `profile_filter.get("page_size", 200)`.
- **Inline `structlog.get_logger()` in handler**: removed the `import structlog; structlog.get_logger()`
  call inside the `manual_sync` handler body in `routers/sync.py`; uses the module-level logger instead.
- **`IntegrityError` over-broad catch**: `ContactRepository.bulk_upsert_contacts` previously caught
  generic `Exception`; narrowed to `sqlalchemy.exc.IntegrityError` so FK violations and other
  non-unique errors propagate correctly.

### Added
- **Telegram Folder Import Feature**: Bulk-import channels from Telegram folder structure
  - `GET /api/telegram/folders` endpoint to list user's Telegram folders
  - `POST /api/telegram/folders/import` endpoint to import channels
  - Exponential backoff retry logic (0.5s → 1s → 2s) for handling database locks
  - Detailed logging for import diagnostics
- **Comprehensive Documentation**: New feature documentation and updated existing docs
  - New file: `docs/features/telegram-folder-import.md` with technical details
  - Updated `docs/concepts.md` with folder import section
  - Updated `docs/02-architecture/overview.md` with import data flow
  - Updated `docs/02-architecture/project-structure.md` with Telegram endpoint details
  - Updated main `README.md` with feature list and documentation links

### Fixed
- **UUID Type Handling**: Proper conversion of folder_id from string to UUID in import endpoint
  - Prevents `sqlalchemy.exc.ProgrammingError: operator does not exist: uuid = integer`
- **Database Locking**: Retry mechanism for concurrent Telethon session access
  - Handles `sqlite3.OperationalError: database is locked` gracefully
  - Automatically retries with exponential backoff

### Changed
- Enhanced error handling in Telegram connector methods
- Improved logging with context-specific information for debugging
- Updated architecture documentation to reflect folder import flow
- Tech stack documentation now includes specific library versions and features

## [Previous Releases]

See git history for details on previous releases.

---

**Last Updated**: 2026-05-18
