# Architecture: Multi-Database Isolation

This document describes the multi-database architecture implemented to support isolated Telegram folders and thematic data separation.

## Overview

The system uses a single PostgreSQL instance but distributes data across multiple databases. Each database corresponds to a specific Telegram folder or a specific thematic focus.

### Data Isolation Strategy
- **Base Database:** `crm` (used for system-wide configurations).
- **Thematic Databases:** Prefixed with `crm_` (e.g., `crm_bg_intel`, `crm_bg_rent`).
- **Dynamic Routing:** All connectors and pipeline tasks accept a `db_name` parameter to route operations to the correct target.

## Core Components

### 1. Database Manager (`src/db/database.py`)
- **`ensure_database_exists(name)`:** Auto-creates PostgreSQL databases if they don't exist.
- **`init_database_schema(name)`:** Initializes the base schema (Tables, Indexes) and enables the `pgvector` extension for AI search.
- **Connection Pooling:** Each database maintains its own session factory to avoid cross-talk.

### 2. Telegram Connector (`src/connectors/telegram_connector.py`)
- **Isolated Sessions:** Uses unique session files per database to maintain authentication state.
- **Folder Sync:** Maps Telegram's folder structure to database names by slugifying folder titles.
- **ID Resolution:** Handles both `int` and `str` peer IDs to ensure compatibility across manual and automated channel joins.

## Operations

### Global Sync Orchestration
Scripts like `deep_sync_all_multi_db.py` iterate through all databases matching the `crm_*` pattern and perform operations sequentially or in parallel.

### Processing Pipeline
The Celery-based processing pipeline is database-aware. Background tasks like `process_message_embeddings` are triggered per database, ensuring that AI-powered analysis is isolated to the relevant data context.
