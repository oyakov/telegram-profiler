# Структура проекта

## Дерево файлов

```
telegram-profiler/
├── .github/
│   └── workflows/          # CI/CD pipelines
├── conductor/              # Project management docs (legacy)
├── docs/                   # Полная документация (рекомендуется)
├── frontend/               # React + TypeScript frontend
│   ├── public/
│   ├── src/
│   │   ├── components/    # React компоненты
│   │   ├── pages/        # Страницы (Dashboard, Contacts, etc.)
│   │   ├── hooks/        # Custom React hooks
│   │   ├── services/     # API clients
│   │   ├── types/        # TypeScript types
│   │   ├── utils/        # Utility functions
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── package.json
│   └── tsconfig.json
├── src/                    # Python backend
│   ├── api/               # FastAPI routers
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── contacts.py
│   │   │   ├── search.py
│   │   │   ├── channels.py
│   │   │   ├── leads.py
│   │   │   └── statistics.py
│   │   └── dependencies.py
│   ├── connectors/        # Data source integrations
│   │   ├── telegram/      # Telethon integration
│   │   ├── excel/         # Excel import
│   │   └── base.py
│   ├── ai/               # LLM & AI processing
│   │   ├── extractors/   # Contact extraction logic
│   │   ├── embedders/    # Embedding generation
│   │   ├── scorers/      # Lead scoring logic
│   │   └── clients.py    # LLM API clients
│   ├── db/               # Database layer
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── schemas.py    # Pydantic schemas
│   │   ├── session.py    # DB session management
│   │   └── migrations/   # Alembic migrations
│   ├── pipeline/         # Celery tasks
│   │   ├── tasks.py      # Task definitions
│   │   ├── processors.py # Processing logic
│   │   └── scheduler.py  # Task scheduling
│   ├── core/            # Configuration & utilities
│   │   ├── config.py    # Environment config
│   │   ├── logger.py    # Logging setup
│   │   └── constants.py # Application constants
│   ├── main.py          # FastAPI application entry point
│   └── requirements.txt  # Python dependencies
├── sessions/            # Telegram session files (local)
├── tests/              # Test suite
│   ├── unit/
│   ├── integration/
│   ├── conftest.py    # pytest fixtures
│   └── requirements.txt # Test dependencies
├── .env.example        # Environment template (NO SECRETS)
├── docker-compose.yml  # Container orchestration
├── Dockerfile         # Backend container image
├── .gitignore        # Git ignore patterns
├── README.md         # Project README (main overview)
└── pyproject.toml    # Python project config

```

## Назначение каждого модуля

### Frontend (`frontend/`)

| Папка | Назначение |
|-------|-----------|
| `components/` | Переиспользуемые UI компоненты (Button, Modal, Card, etc.) |
| `pages/` | Страницы приложения (Dashboard, Contacts, Search, Settings, Audit) |
| `hooks/` | Custom React hooks (useApi, useAuth, useSearch, etc.) |
| `services/` | API clients и HTTP утилиты |
| `types/` | TypeScript interfaces и types |
| `utils/` | Helper функции (date formatting, parsing, etc.) |
| `App.tsx` | Главный компонент приложения |

### Backend API (`src/api/`)

| Файл | Назначение |
|------|-----------|
| `auth.py` | Endpoints авторизации и управления пользователем |
| `contacts.py` | CRUD операции с контактами |
| `search.py` | Семантический поиск |
| `channels.py` | Управление каналами и папками |
| `leads.py` | Lead management и scoring |
| `statistics.py` | Аналитика и дашборд данные |
| `telegram.py` | Telegram integration endpoints (auth, folders, import) |

### Connectors (`src/connectors/`)

| Компонент | Назначение |
|-----------|-----------|
| `telegram_connector.py` | Интеграция с Telegram через Telethon: auth, sync, folder import с retry logic |
| `excel/` | Импорт контактов из Excel файлов |
| `base.py` | Базовый класс для всех connectors |

**Telegram Connector особенности**:
- `list_telegram_folders()` — загрузка список папок и их peer_ids
- `import_folder_channels(peer_ids)` — импорт каналов с exponential backoff retry
- Persistent sessions для multi-database поддержки
- Автоматическое разрешение peer_ids в Channel/Chat объекты

### AI & Processing (`src/ai/`)

| Модуль | Назначение |
|--------|-----------|
| `extractors/` | LLM-based извлечение контактов из сообщений |
| `embedders/` | Генерация embedding'ов для семантического поиска |
| `scorers/` | Алгоритм расчета lead score |
| `clients.py` | Клиенты для работы с Gemini, OpenAI, LM Studio |

### Database (`src/db/`)

| Файл | Назначение |
|------|-----------|
| `models.py` | SQLAlchemy ORM модели (User, Contact, Message, etc.) |
| `schemas.py` | Pydantic schemas для валидации и сериализации |
| `session.py` | Database session factory и utilities |
| `migrations/` | Alembic миграции схемы БД |

### Pipeline (`src/pipeline/`)

| Файл | Назначение |
|------|-----------|
| `tasks.py` | Определение Celery задач |
| `processors.py` | Бизнес-логика обработки |
| `scheduler.py` | Планирование периодических задач |

### Core (`src/core/`)

| Файл | Назначение |
|------|-----------|
| `config.py` | Загрузка и валидация переменных окружения |
| `logger.py` | Конфигурация логирования |
| `constants.py` | Глобальные константы приложения |

## Зависимости между модулями

```
API Layer
  ├── depends on → Database (models, schemas)
  ├── depends on → AI (extractors, scorers)
  └── depends on → Core (config, logger)

Pipeline (Celery)
  ├── depends on → Connectors (Telegram sync)
  ├── depends on → AI (extraction, embedding)
  ├── depends on → Database (persist results)
  └── depends on → Core (config, logger)

Connectors
  └── depends on → Core (config, logger)

AI
  └── depends on → Core (config, logger)

Frontend
  └── depends on → API Layer (HTTP calls)
```

## Точки входа

### Backend
```python
# src/main.py
# Запуск FastAPI приложения через Uvicorn
# uvicorn src.main:app --reload
```

### Frontend
```bash
# frontend/
# Запуск dev сервера через Vite
# npm run dev → http://localhost:3005
```

### Celery Worker
```python
# Запуск background task worker
# celery -A src.pipeline.tasks worker --loglevel=info
```

## Миграции БД

Используется Alembic для управления версиями БД:

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "Add field to contacts"

# Применить миграцию
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

## Тестирование

```bash
# Запуск всех тестов
pytest

# С coverage
pytest --cov=src

# Только unit тесты
pytest tests/unit/

# С verbose output
pytest -v
```

## Сборка и развертывание

### Docker
```bash
# Сборка образов
docker-compose build

# Запуск всех сервисов
docker-compose up

# Остановка
docker-compose down
```

## Соглашения по именованию

### Python
- **Модули**: `lowercase_with_underscores.py`
- **Классы**: `PascalCase`
- **Функции/методы**: `lowercase_with_underscores`
- **Константы**: `UPPERCASE_WITH_UNDERSCORES`

### React/TypeScript
- **Компоненты**: `PascalCase` в файлах `PascalCase.tsx`
- **Hooks**: `useHookName`
- **Utilities**: `camelCase.ts`
- **Types/Interfaces**: `PascalCase` в файлах `index.ts`

### Database
- **Таблицы**: `lowercase_plural` (contacts, messages, channels)
- **Столбцы**: `lowercase_with_underscores`
- **Индексы**: `idx_table_column`
- **Foreign Keys**: `fk_table_referenced_table`

## Главные различия между старой и новой документацией

| Аспект | Старое (conductor/) | Новое (docs/) |
|--------|------------------|---------|
| Структура | Смешанная, по проектам | Иерархическая, по типам контента |
| Поиск | Сложнее найти нужную информацию | Централизованный README с индексом |
| Версионирование | Нет явной системы | Версии в заголовках |
| Обновления | Разрозненные | Централизованный процесс |

---

Для деталей см. README в каждом разделе docs/
