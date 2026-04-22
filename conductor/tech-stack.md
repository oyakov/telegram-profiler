# Technology Stack

## Language & Core
- **Language:** Python
- **Environment:** Docker (defined via `docker-compose.yml` and `Dockerfile`s)

## Backend
- **Framework:** FastAPI with Uvicorn for asynchronous, high-performance API delivery.

## Database & Data Storage
- **Relational Database:** PostgreSQL with the `pgvector` extension for storing and querying embeddings.
- **ORM & Migrations:** SQLAlchemy (asyncpg) for database interactions and Alembic for schema migrations.

## Task Queue & Background Processing
- **Queue Manager:** Celery
- **Broker:** Redis

## Frontend & Dashboard
- **Framework:** Streamlit for rapid, data-dense internal dashboard creation.
- **Visualization:** Plotly

## AI & Machine Learning
- **LLM Providers:** OpenAI and Google GenAI.
- **Tokenization:** Tiktoken for precise LLM context management.

## Integrations & Connectors
- **Telegram:** Telethon
- **Data Parsing:** Pandas and Openpyxl
- **HTTP Client:** httpx