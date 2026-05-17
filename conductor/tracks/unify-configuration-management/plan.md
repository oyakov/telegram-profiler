# Implementation Plan: Unified Configuration Management

## Goal
Provide a consistent, hierarchical configuration interface across the entire application.

## Phase 1: Configuration Provider
- [ ] Implement `ConfigurationProvider` in `src/core/config.py`.
- [ ] Implement logic to merge `AppSettings` (environment) with `Setting` (DB) values.

## Phase 2: Migration
- [ ] Replace `get_settings()` and `SettingsService` calls with `ConfigurationProvider.get()`.
- [ ] Update background tasks and services to use the unified provider.

## Phase 3: Verification
- [ ] Verify DB overrides correctly supersede environment variables.
- [ ] Ensure cached settings refresh correctly after DB updates.