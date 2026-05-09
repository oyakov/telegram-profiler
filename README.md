# Networking Brain CRM

A sophisticated personal CRM and market intelligence tool powered by Telegram, AI, and Vector search.

## Features

- **Telegram Folder Import**: Bulk-import channels from your Telegram folder structure with automatic deduplication and retry logic.
- **Multi-Database Isolation**: Isolate different folders (e.g., Crypto, Belgrade News) into dedicated databases for independent tracking.
- **AI Extraction**: Identify contacts, leads, and ad-buyers using Google Gemini or local LLMs (LM Studio).
- **Semantic Search**: Find contacts and messages using natural language queries via `pgvector` embeddings.
- **Thematic Discovery**: Automatically expand your network by joining niche-specific channels with auto-joined/muted folder organization.
- **Market Intelligence**: Real-time dashboard for monitoring ad-buyer trends and scoring high-value leads with configurable ranking algorithms.
- **Contact Deduplication**: Intelligent matching by Telegram ID, username, email, and name to prevent duplicate tracking.

## Tech Stack

- **Backend**: FastAPI (Python 3.12) with async/await support
- **Database**: PostgreSQL 15+ with `pgvector` for semantic search and HNSW indexing
- **Background Tasks**: Celery + Redis for distributed task processing with priority queues
- **Frontend**: React 18+ + TypeScript (Vite) — modern dashboard with semantic search, folder management, and real-time monitoring
- **Telegram Integration**: Telethon with persistent session management and exponential backoff retry logic
- **AI**: Google Gemini (Direct or OpenAI-compatible API) / LM Studio for local inference
- **ASR**: OpenAI Whisper (for transcribing voice notes)
- **Observability**: Prometheus + Grafana for metrics, structured logging with correlation IDs

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Telegram API Credentials (`api_id` and `api_hash`)
- (Optional) Google AI Studio API Key

### Setup

1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in your credentials.
3. Start the services:
   ```bash
   docker-compose up --build
   ```
4. Access the frontend at `http://localhost:3005`.
5. Access the API documentation at `http://localhost:8000/docs`.

## Project Structure

- `src/api`: FastAPI routers (consolidated pipeline endpoint)
- `src/connectors`: Data sources (Telegram, Excel, external APIs, audio)
- `src/ai`: LLM clients, extraction, embeddings, and analysis
- `src/db`: SQLAlchemy models and database management
- `src/pipeline`: Celery tasks and unified processing logic
- `src/core`: Configuration and logging
- `frontend`: React + TypeScript dashboard

## Documentation

### Getting Started
- [Quick Start Guide](docs/01-introduction/quick-start.md) — Run the project in 5 minutes
- [Architecture Overview](docs/02-architecture/overview.md) — System design and components
- [Core Concepts](docs/concepts.md) — Key ideas: folders, channels, leads, sessions, folder import

### Features
- [Telegram Folder Import](docs/features/telegram-folder-import.md) — Bulk-import channels with retry logic
- [Skill: Host-Side Mass Processing](docs/skills/pattern_host_side_processing.md)
- [Skill: Thematic Discovery](docs/skills/pattern_thematic_discovery.md)

### Development
- [Development Workflow](docs/04-development/workflow.md)
- [Python Style Guide](docs/04-development/style-guides/python.md)
- [Testing Guide](docs/04-development/testing.md)

### Architecture
- [Multi-Database Isolation](docs/02-architecture/multi-database.md)
- [Technology Stack](docs/02-architecture/tech-stack.md)
- [Project Structure](docs/02-architecture/project-structure.md)
