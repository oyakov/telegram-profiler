# Networking Brain CRM

A sophisticated personal CRM and market intelligence tool powered by Telegram, AI, and Vector search.

## Features

- **Multi-Database Isolation**: Isolate different folders (e.g., Crypto, Belgrade News) into dedicated databases.
- **AI Extraction**: Identify contacts, leads, and ad-buyers using Gemini or local LLMs (LM Studio).
- **Semantic Search**: Find contacts and messages using natural language queries via `pgvector`.
- **Thematic Discovery**: Automatically expand your network by joining niche-specific channels with auto-joined/muted folders.
- **Market Intelligence**: Dashboard for monitoring ad-buyer trends and scoring high-value leads.

## Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL with `pgvector`
- **Background Tasks**: Celery + Redis
- **Dashboard**: Streamlit
- **AI**: Google Gemini (Direct or OpenAI-compat) / LM Studio
- **ASR**: Whisper (for voice notes)

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
4. Access the dashboard at `http://localhost:8501`.
5. Access the API documentation at `http://localhost:8000/docs`.

## Project Structure

- `src/api`: FastAPI routers and schemas.
- `src/connectors`: Data ingestion from Telegram, Excel, and Social sources.
- `src/ai`: LLM clients, extraction logic, and embeddings.
- `src/db`: SQLAlchemy models and database management.
- `src/pipeline`: Celery tasks and unified processing logic.
- `dashboard`: Streamlit UI.

## Documentation

- [Architecture: Multi-Database](file:///c:/Projects/telegram-profiler/docs/architecture_multi_db.md)
- [Skill: Host-Side Mass Processing](file:///c:/Projects/telegram-profiler/docs/skills/pattern_host_side_processing.md)
- [Skill: Thematic Discovery](file:///c:/Projects/telegram-profiler/docs/skills/pattern_thematic_discovery.md)
- [General Concepts](file:///c:/Projects/telegram-profiler/docs/concepts.md)
