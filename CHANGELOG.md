# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

**Last Updated**: 2026-05-09
