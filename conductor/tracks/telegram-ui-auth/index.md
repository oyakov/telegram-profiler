# Track 02: Telegram UI Authentication & Containerization

## Status
- **Progress:** 100%
- **Status:** `[x]`

## Objectives
The primary objective of this track is to containerize the entire application for seamless deployment and replace the CLI-based Telegram login script with an interactive, user-friendly UI flow within the Streamlit dashboard.

1.  **Docker Orchestration:** Ensure the backend, worker (Celery), dashboard, and all services (Postgres, Redis, Whisper) start up correctly via `docker-compose`. Fix volume mapping for session persistence.
2.  **API Authentication Endpoints:** Create backend API endpoints to handle Telegram's 3-step authentication flow (Phone -> Code -> 2FA Password).
3.  **UI Login Flow:** Implement a dedicated section in the Streamlit dashboard to securely enter phone numbers, receive/input Telegram verification codes, and handle 2FA if enabled.
4.  **Session State Management:** Ensure the Telethon client can properly store its session file in a mounted Docker volume, allowing restarts without re-authentication.

## Key Files
- `docker-compose.yml`
- `src/api/main.py`
- `src/connectors/telegram_connector.py`
- `dashboard/app.py`

## Links
- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
