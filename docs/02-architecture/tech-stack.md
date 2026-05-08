# Технологический стек

## Язык и ядро

- **Язык**: Python 3.12+
- **Окружение**: Docker (docker-compose.yml, Dockerfile)
- **Пакетный менеджер**: pip с requirements.txt
- **Управление зависимостями**: pip-tools (опционально)

## Backend

### Framework
- **FastAPI** с Uvicorn для асинхронного API
- **Pydantic** для валидации и сериализации данных
- **SQLAlchemy** (asyncpg) для ORM и работы с БД
- **Alembic** для миграций БД

### Ключевые зависимости
```
fastapi==0.104.0+
uvicorn[standard]==0.24.0+
sqlalchemy==2.0+
asyncpg==0.29+
pydantic==2.0+
alembic==1.13+
```

## База данных и хранилище

### Relational Database
- **PostgreSQL** 15+ с расширением `pgvector`
- **pgvector** v0.5+ для хранения и поиска embeddings (HNSW индексы)

### Connection Pooling
- **SQLAlchemy** с asyncpg

### Миграции
- **Alembic** для управления версиями схемы

## Task Queue и Background Processing

### Queue Manager
- **Celery** 5.3+ с поддержкой async/await

### Message Broker
- **Redis** 7.0+ для передачи сообщений и кэширования
- **RedisStack** (опционально) для расширенных функций

## Frontend и Dashboard

### Framework
- **React** 18.2+
- **TypeScript** 5.0+
- **Vite** для build система и dev server
- **React Router** для навигации

### Стилизация
- **Tailwind CSS** 3.3+ для утилит-первого стиля
- **Headless UI** компоненты для accessibility

### State Management
- **React Context API** для глобального состояния
- **useReducer** для сложной логики

### Визуализация
- **Recharts** для графиков и диаграмм
- **Plotly.js** (опционально) для интерактивных графиков

### HTTP Client
- **axios** или встроенный **fetch** API

### Типизация
- **TypeScript** с strict mode
- **@types/react**, **@types/node** и т.д.

## AI и Machine Learning

### LLM Провайдеры

#### Google Gemini API
- **google-generativeai** SDK
- Для анализа контента и извлечения контактов
- API ключ из [https://makersuite.google.com](https://makersuite.google.com)

#### OpenAI API (резервная опция)
- **openai** SDK
- Использование GPT-4 или GPT-3.5-turbo

#### Local LM Studio
- **HTTP API** на localhost:1234
- Поддержка Mistral, Llama и других моделей

### Embeddings
- **google-generativeai** для Google Embeddings API
- **sentence-transformers** для локальных embeddings (e.g., all-MiniLM-L6-v2)

### Обработка текста
- **tiktoken** для подсчета tokens и context management
- **nltk** или **spacy** для NLP preprocessing

## Интеграции и коннекторы

### Telegram
- **Telethon** 1.32+ для работы с Telegram API
- Синхронизация сообщений, мониторинг каналов, управление сессиями

### Data Parsing
- **pandas** 2.0+ для работы с tabular data
- **openpyxl** для Excel файлов

### HTTP Client
- **httpx** для async HTTP requests
- **requests** для sync requests (опционально)

## Observability и Monitoring

### Logging
- Встроенный **logging** модуль Python
- **loguru** (опционально) для улучшенного логирования

### Metrics (опционально)
- **prometheus-client** для экспорта метрик
- **Prometheus** для сбора и хранения

### Tracing (опционально)
- **opentelemetry** для distributed tracing
- **Jaeger** для визуализации tracing

## Development Tools

### Testing
- **pytest** для unit и integration тестов
- **pytest-asyncio** для тестирования async кода
- **pytest-cov** для code coverage
- **unittest.mock** для mocking

### Code Quality
- **black** для форматирования кода
- **flake8** или **ruff** для linting
- **isort** для сортировки импортов
- **mypy** для type checking

### Development Server
- **Vite** dev server для frontend (HMR поддержка)
- **Uvicorn --reload** для backend

### Documentation
- **MkDocs** (опционально) для документации
- **Markdown** для документов

## Version Control и CI/CD

### Git
- **Git** для контроля версий
- **.gitignore** для исключения sensitives файлов

### CI/CD
- **GitHub Actions** для automated testing и deployment
- **Docker** для containerization

## Security

### Authentication
- **Telegram OAuth2** для пользователей
- **JWT tokens** (PyJWT) для API sessions
- **python-jose** для JWT управления

### Password & Secrets
- **python-dotenv** для загрузки .env файлов
- **cryptography** для шифрования sensitive данных

## Container Management

### Docker
- **Docker** 20.10+ для контейнеризации
- **docker-compose** 2.0+ для оркестрации сервисов

### Services (docker-compose)
```yaml
services:
  db:
    image: pgvector/pgvector:pg15-latest
  redis:
    image: redis:7-alpine
  api:
    build: .
    depends_on: [db, redis]
  celery:
    build: .
    depends_on: [db, redis]
  frontend:
    build: frontend/
    ports: [3005]
```

## Production Deployment

### Container Orchestration
- **Kubernetes** (опционально) для масштабирования
- **Docker Swarm** (опционально) как альтернатива

### Reverse Proxy
- **nginx** для балансировки нагрузки и маршрутизации

### SSL/TLS
- **Let's Encrypt** для сертификатов
- **nginx** для управления SSL

### Database Backups
- **pg_dump** для резервных копий PostgreSQL
- **AWS S3** или другое облачное хранилище

## Резюме зависимостей

### Critical (обязательные)
```
Python 3.12+
PostgreSQL 15+ with pgvector
Redis 7+
FastAPI, SQLAlchemy, Pydantic
React, TypeScript, Vite
Telethon (Telegram)
```

### Important (рекомендуемые)
```
Celery, asyncpg, alembic
Google GenAI API
Tailwind CSS, Recharts
pytest, black, flake8
Docker, docker-compose
```

### Optional (улучшения)
```
LM Studio (локальный LLM)
Prometheus (мониторинг)
OpenTelemetry (трейсинг)
MkDocs (документация)
Kubernetes (масштабирование)
```

## История и изменения

### v1.0 (Текущая)
- FastAPI + PostgreSQL + React stack
- Google Gemini API интеграция
- Базовый semantic search через pgvector
- Telethon для Telegram синхронизации

### v1.1 (Планируется)
- OpenAI API опция
- LM Studio поддержка для локального LLM
- Prometheus мониторинг
- Kubernetes deployment templates

### v2.0 (Долгосрочно)
- GraphQL API (опционально)
- WebSocket real-time updates
- Advanced analytics engine
- Machine learning model training pipeline

---

**Последнее обновление**: 2026-05-08
**Ответственность за обновления**: Backend team
