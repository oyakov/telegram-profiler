# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security (round-7)
- **`/stats/embeddings/reindex` X-Database injection**: the endpoint now validates the
  `X-Database` header against `_DB_NAME_RE` before passing it to Celery, consistent with
  all other multi-tenant endpoints.
- **`create_contact` mass-assignment**: `ContactService.create_contact` now applies a
  server-side `_ALLOWED_CREATE_FIELDS` whitelist. Internal columns (`lead_score`, `is_lead`,
  `embedding`, etc.) can no longer be injected via the create path.
- **`add_to_tracked` DataError via invalid UUID**: each item in the `contact_ids` list is
  now parsed with `UUID(...)` before the ORM query. Malformed IDs are silently dropped;
  the endpoint returns a count instead of raising asyncpg `DataError` (500).
- **File-upload DoS**: `/pipeline/import/excel` now reads at most 50 MB (`_MAX_UPLOAD_BYTES`)
  before rejecting with HTTP 413. Previously an unbounded `file.read()` could exhaust memory.

### Fixed (round-7)
- **`enrich_contact` / `sync_deep_history_chunk` AttributeError**: Both methods were called
  on `TelegramConnector` but never implemented, causing every invocation of `enrich_contact_task`
  and `deep_track_chunk` (beat: every 15 min per active channel) to crash with `AttributeError`.
  Both methods are now implemented on the connector.
- **`CampaignService(session, db_name=db_name)` TypeError**: `tasks.send_campaign` was passing
  `db_name=` as a keyword argument that `CampaignService.__init__` does not accept, raising
  `TypeError` on every campaign-send task. The spurious argument is removed.
- **`MissingGreenlet` on sync status endpoints**: `start_channel_sync` and
  `get_channel_sync_status` accessed `channel.sync_state` without eager-loading the
  relationship, triggering async lazy-load errors. Both queries now use
  `selectinload(TrackedChannel.sync_state)`.
- **`start_channel_sync` cleanup used `__import__` anti-pattern**: orphaned `ChannelSyncState`
  cleanup after a broker failure now reuses the existing `db` session instead of opening a
  second connection via `__import__("src.db.database")`.
- **`start_channel_sync` missing `queue="connectors"`**: the single-channel start endpoint
  now explicitly routes `scan_channel_metadata` to the `connectors` queue, consistent with
  the folder-sync and orchestrator paths.
- **`start_folder_sync` cleanup after enqueue failure**: `await db.rollback()` after a
  committed session was a no-op, leaving an orphaned `ChannelSyncState`. The handler now
  executes a targeted `DELETE` + `commit` to clean up the orphaned row.
- **`sync_orchestrator` cleanup opened unnecessary second session**: the `get_session`
  context manager inside `_queue_new_channels`' error path is replaced with a direct
  execute+commit on the already-open `session`, reducing connection overhead.
- **`run_campaign` permanently stuck in `"running"` after worker crash**: the guard
  condition `status in ("running", "completed")` prevented retry of campaigns that stalled
  mid-delivery due to a worker restart. Changed to `status == "completed"` only.
- **`full_reindex` unbounded while-True loop**: replaced with a bounded `for _ in range(2000)`
  loop so a continuous stream of dirty contacts cannot hold a Celery worker indefinitely.
- **`bulk_save_messages` wrong conflict target**: changed `ON CONFLICT index_elements=` to
  `constraint="uq_message_source_id"` so the upsert works whether the unique constraint was
  created as a `CONSTRAINT` or a `UNIQUE INDEX`.
- **ILIKE search unescaped wildcards**: `ContactService.list_contacts` now escapes `%` and
  `_` in the search parameter via `_escape_ilike()` so user input is matched literally.
- **Tenant-scoped Redis cache for `/stats/tree`**: the `tree:msg_counts` cache key now
  includes the tenant DB name (`tree:msg_counts:{db_name}`) so different tenants cannot
  receive each other's message counts during the 30-second TTL window.

### Changed (round-7)
- **`CampaignUpdate` schema**: `name`, `description`, and `message` now enforce the same
  `max_length` constraints as `CampaignCreate` (255 / 2048 / 4096 respectively).
- **Campaign `status` query parameters**: `list_campaigns` and `get_campaign_messages` now
  use `Literal["draft","sending","completed","failed"]` / `Literal["pending","sent","failed","skipped"]`
  instead of bare `str`, so invalid status values are rejected with HTTP 422.

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
