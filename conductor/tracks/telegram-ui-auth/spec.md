# Specification: Telegram UI Authentication

## Overview
Currently, initializing the Telegram connection requires running an interactive Python script in the terminal (`tg_login.py`). To make the product truly standalone and Docker-native, this process must be moved to the web dashboard. Users should be able to enter their phone number and the verification code sent by Telegram directly in the UI.

## Requirements

### 1. Backend API (FastAPI)
New endpoints to manage the Telethon authentication flow asynchronously:
- `GET /api/telegram/auth/status`: Returns whether the current session is authorized.
- `POST /api/telegram/auth/send_code`: Accepts a phone number and calls `client.send_code_request`. Returns a `phone_code_hash`.
- `POST /api/telegram/auth/verify`: Accepts the phone number, code, and `phone_code_hash`. Attempts `client.sign_in`. If 2FA is required, returns a specific status (e.g., `requires_2fa`).
- `POST /api/telegram/auth/2fa`: Accepts the 2FA password and attempts `client.sign_in(password=...)`.
- `POST /api/telegram/auth/logout`: Disconnects and deletes the session file.

### 2. Telethon Integration
The `TelegramConnector` (or a dedicated `TelegramAuthManager`) must be refactored to support these interactive steps, breaking the previous blocking `client.start()` call into its constituent parts (`connect`, `is_user_authorized`, `send_code_request`, `sign_in`).

### 3. Dashboard UI (Streamlit)
A new section (likely in the "Connectors" page) that dynamically updates based on the auth state:
- **State: Not Logged In**: Shows a phone number input field.
- **State: Waiting for Code**: Shows a code input field (and handles `phone_code_hash` invisibly via session state).
- **State: Waiting for 2FA**: Shows a password input field.
- **State: Logged In**: Shows the connected username and a "Logout" button.

### 4. Containerization
- Update `docker-compose.yml` to run a `celery worker` service. Currently, tasks are only defined but the worker container is missing.
- Ensure the `/app/sessions` directory is properly mounted as a volume so the `.session` file persists across container restarts.

## Success Criteria
1. The user can start the entire stack using `docker-compose up -d`.
2. The user can open the dashboard, navigate to Connectors, and log in to Telegram entirely through the UI.
3. The session persists even if the `crm-app` container is restarted.
4. No terminal interaction is required for any part of the setup (assuming `.env` is populated with `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`).
