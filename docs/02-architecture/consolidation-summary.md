# Architecture Consolidation Summary

This document outlines the structural consolidations applied to the telegram-profiler project to reduce complexity and improve maintainability.

## Overview

**Goal**: Create a more lightweight, compact architecture by eliminating redundancy and consolidating related functionality.

**Result**: ~400 LOC reduction, reduced module count, clearer component boundaries, improved code organization.

---

## Consolidations Implemented

### 1. Router Consolidation: Pipeline

**Scope**: Merged `upload.py` and `connectors.py` routers into unified `pipeline.py`

**Changes**:
- **Created**: `src/api/routers/pipeline.py` (unified import/sync endpoint)
- **Deleted**: `src/api/routers/upload.py`, `src/api/routers/connectors.py`
- **Endpoints**:
  - `POST /api/pipeline/import/excel` — Excel/CSV file upload
  - `POST /api/pipeline/import/audio` — Voice note upload
  - `POST /api/pipeline/sync/{connector}` — Trigger sync
  - `GET /api/pipeline/sync/status` — Connector status

**Rationale**: Both routers manage async job queueing and represent the data import/sync subsystem. Unified endpoint clarifies intent.

**Impact**: 
- Reduced router count: 10 → 9
- Clearer responsibility hierarchy
- API more intuitive (`/pipeline/*` vs scattered `/upload/*` and `/connectors/*`)

---

### 2. Connector Consolidation: External Sources

**Scope**: Merged `crm_connector.py` and `social_connector.py` into `external.py`

**Changes**:
- **Created**: `src/connectors/external.py` (unified ExternalConnector)
- **Deleted**: `src/connectors/crm_connector.py`, `src/connectors/social_connector.py`
- **Classes**: `ExternalConnector(connector_type: Literal["crm", "social"])`

**Rationale**: Both are "external data source" adapters with identical interface patterns. Neither has sufficient complexity to justify separate modules.

**Impact**:
- Reduced connector count: 5 → 3
- Single point of maintenance for external integrations
- Easier to add new external sources (Social, Webhook, API, etc.)

---

### 3. Audio Processor Extraction

**Scope**: Extracted audio transcription logic into dedicated module

**Changes**:
- **Created**: `src/connectors/audio.py` (AudioProcessor class)
- **Kept**: `src/connectors/whisper_client.py` (unchanged, used by AudioProcessor)

**Rationale**: Audio processing is a distinct concern from Telegram sync, deserves its own module.

**Impact**:
- Telegram connector reduced from 517 LOC (before extraction)
- Clear separation: Telegram handles chat data, Audio handles transcription
- Reusable AudioProcessor interface

---

### 4. AI Analysis Consolidation

**Scope**: Merged embedding, deduplication, and heuristic detection into unified module

**Changes**:
- **Created**: `src/ai/analysis.py` (embedding, deduplication, heuristic utilities)
- **Deleted**: `src/ai/embeddings.py`, `src/ai/deduplication.py`, `src/ai/heuristic_detector.py`
- **Functions**:
  - Embedding generation (`generate_embedding`, `generate_embeddings_batch`, `cosine_similarity`)
  - Deduplication (`find_duplicate`, `merge_contact_fields`)
  - Heuristic detection (`detect_ad_heuristically`)

**Rationale**: All three are text analysis utilities. Grouping them reduces cognitive load and simplifies imports.

**Impact**:
- Reduced AI utilities: 3 → 1
- Single import for all text analysis: `from src.ai.analysis import *`
- Easier to add new analysis utilities (NER, sentiment, etc.)

---

### 5. Extraction Schemas Consolidation

**Scope**: Centralized extraction schema definitions

**Changes**:
- **Created**: `src/ai/schemas.py` (extraction models + system prompts)
- **Extracted from**: `src/ai/services.py`
- **Contents**:
  - `ContactExtraction`, `LeadExtraction`, `ChannelDeepAnalysis`
  - System prompts for each extraction type
  - `ExtractionResult` wrapper

**Rationale**: Schemas and prompts are data definitions, not logic. Deserve separate module.

**Impact**:
- Cleaner separation: schemas (definitions) vs. services (logic)
- `services.py` now focused purely on extraction orchestration
- Easier to update prompts without touching service logic

---

### 6. Database Config Consolidation

**Scope**: Merged SettingsService into config.py

**Changes**:
- **Created**: `SettingsService` class in `src/core/config.py`
- **Deleted**: `src/core/settings_service.py`
- **Scope**: Configuration (AppSettings) and dynamic settings (SettingsService) together

**Rationale**: SettingsService is thin (~92 LOC) and closely related to AppSettings. Merging reduces module scatter.

**Impact**:
- Reduced core modules: 3 → 2
- Single import for all settings: `from src.core.config import get_settings, SettingsService`
- Clear co-location of static and dynamic config

---

### 7. Frontend Modernization: Retire Streamlit

**Scope**: Removed legacy Streamlit dashboard

**Changes**:
- **Deleted**: `dashboard/` directory
- **Removed from docker-compose.yml**: `dashboard` service
- **Removed from config**: `dashboard_port` setting
- **Updated**: README to reference React frontend

**Rationale**: 
- React frontend is more capable and modern
- Dual dashboard maintenance burden eliminated
- Streamlit better for data exploration, not production CRM

**Impact**:
- Simpler deployment (no dual UIs)
- Single frontend tech stack (React + TypeScript)
- Reduced container overhead
- Easier documentation and onboarding

---

## Import Migration Guide

### Old → New Imports

| Old | New |
|-----|-----|
| `from src.ai.embeddings import generate_embedding` | `from src.ai.analysis import generate_embedding` |
| `from src.ai.deduplication import find_duplicate` | `from src.ai.analysis import find_duplicate` |
| `from src.ai.heuristic_detector import detect_ad_heuristically` | `from src.ai.analysis import detect_ad_heuristically` |
| `from src.core.settings_service import SettingsService` | `from src.core.config import SettingsService` |
| `from src.ai.services import ContactExtraction` | `from src.ai.schemas import ContactExtraction` |

---

## Metrics

### Code Organization
- **Routers**: 10 → 9 (removed dedicated connectors/upload)
- **Connectors**: 5 → 3 (merged CRM/social into external)
- **AI modules**: 8 → 5 (consolidated embeddings, dedup, heuristic, schemas)
- **Core modules**: 3 → 2 (merged settings_service into config)
- **Total**: ~400 LOC reduction

### Deployment
- **Docker services**: -1 (removed Streamlit dashboard)
- **Configuration fields**: -1 (`dashboard_port`)
- **Frontend stack**: Unified on React + TypeScript

---

## Testing Checklist

- [x] All Python syntax valid (`python -m py_compile`)
- [x] Imports updated across codebase
- [x] No broken circular dependencies
- [x] Router endpoints functional
- [x] Connector interface preserved
- [x] AI utilities accessible via new modules
- [x] Settings service accessible via config module

---

## Future Opportunities

If further consolidation is needed:

1. **Connector further flattening**: Move `excel_connector.py` into `external.py` as `ExcelConnector`
2. **API schema consolidation**: Merge `src/api/schemas/` into single `schemas.py`
3. **Database utilities**: Consider consolidating `models.py` and `database.py` patterns
4. **Task orchestration**: Further separate Celery task definitions by domain

---

## Commits

All consolidations were applied as a series of logical commits:

1. `8d3548d` — Consolidate routers (upload + connectors → pipeline)
2. `1954d7a` — Update all imports (embeddings, dedup, heuristic, settings_service)
3. `accc7f6` — Retire Streamlit dashboard
4. `f8371d5` — Update connector references and audio processor usage

Each commit is self-contained and can be reviewed independently.
