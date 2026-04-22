# Implementation Plan: Telegram UI Authentication

## Phase 1: Docker & Infrastructure
*Goal: Ensure the containerized environment is robust and runs all necessary services.*

- [x] **Task 1: Add Celery Worker to Docker Compose.**
  - Define a new service `worker` in `docker-compose.yml` running `celery -A src.pipeline.celery_app worker`.
  - Ensure volume mounts (especially `/app/sessions` and `/app/uploads`) match the `app` service.

## Phase 2: Telethon & API Integration
*Goal: Implement the backend logic for non-blocking Telegram authentication.*

- [x] **Task 2: Refactor Telegram Connector Auth.**
  - Create methods in `TelegramConnector` for `send_code`, `verify_code`, and `verify_2fa` that wrap Telethon's manual auth flow instead of the blocking `client.start()`.
- [x] **Task 3: Create Auth Endpoints.**
  - Add routes in `src/api/main.py`: `/api/telegram/auth/status`, `/api/telegram/auth/send_code`, `/api/telegram/auth/verify`, `/api/telegram/auth/2fa`, and `/api/telegram/auth/logout`.
  - Handle Telethon exceptions (e.g., `SessionPasswordNeededError`) gracefully.

## Phase 3: Dashboard UI
*Goal: Provide a seamless user interface for login.*

- [x] **Task 4: Implement Login UI Components.**
  - Update `dashboard/app.py` in the "Connectors" section to check `/api/telegram/auth/status`.
  - Create forms for Phone Number, Verification Code, and Password.
  - Manage the multi-step flow using Streamlit's `st.session_state`.
- [x] **Task 5: Final Validation.**
  - Start the stack via Docker.
  - Successfully log in via the UI.
  - Trigger a sync to verify the session works inside the container.
