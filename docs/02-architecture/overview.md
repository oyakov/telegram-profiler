# Архитектурный обзор

## Высокоуровневая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + TypeScript)             │
│                  Dashboard, Search, Contacts                 │
└────────────────────────┬────────────────────────────────────┘
                         │ (HTTP/WebSocket)
┌─────────────────────────▼────────────────────────────────────┐
│                  API Layer (FastAPI)                         │
│              /api/contacts, /api/search, /api/auth          │
└────────────┬──────────────────────────────┬─────────────────┘
             │                              │
    ┌────────▼──────────┐      ┌────────────▼──────────┐
    │  Task Queue       │      │  PostgreSQL Database   │
    │  (Celery + Redis) │      │  (pgvector, SQLAlchemy)│
    │                   │      │  Contacts, Messages    │
    │  Background Jobs  │      │  Embeddings, Leads     │
    │  - Sync Telegram  │      │  Users, Sessions       │
    │  - Extract Leads  │      └────────────────────────┘
    │  - Generate Embeds│
    │  - Score Contacts │
    └─────────┬─────────┘
              │
    ┌─────────▼────────────────┐
    │  Telegram Integration    │
    │  (Telethon Library)      │
    │  - Message Sync          │
    │  - Channel Monitoring    │
    │  - Session Management    │
    └──────────────────────────┘
```

## Компоненты системы

### Frontend (React + TypeScript + Vite)
**Расположение**: `frontend/`

Ответственность:
- Отображение dashboard с analytics
- Интерфейс семантического поиска
- Управление контактами и notes
- Авторизация через Telegram
- Real-time обновления

Технологии:
- React 18+
- TypeScript
- Tailwind CSS
- Recharts / Plotly для графиков
- Context API для state management

### Backend API (FastAPI)
**Расположение**: `src/api/`

Ответственность:
- REST API endpoints
- Авторизация и управление сессиями
- Валидация данных
- Обработка запросов к БД
- Взаимодействие с AI моделями

Маршруты:
- `/api/auth` — авторизация
- `/api/contacts` — управление контактами
- `/api/search` — семантический поиск
- `/api/channels` — управление каналами
- `/api/leads` — lead management
- `/api/statistics` — аналитика

### Database Layer
**Технология**: PostgreSQL + pgvector + SQLAlchemy

Таблицы:
- `users` — учетные записи пользователей
- `folders` — папки отслеживания (категории)
- `channels` — отслеживаемые каналы
- `messages` — сообщения из Telegram
- `contacts` — извлеченные контакты
- `leads` — выявленные leads с scores
- `embeddings` — векторные представления

Индексы:
- HNSW индексы для pgvector (семантический поиск)
- B-tree индексы для общего поиска

### Pipeline & Task Processing
**Технология**: Celery + Redis

Задачи:
- `sync_messages` — синхронизация сообщений из Telegram
- `extract_leads` — идентификация контактов через LLM
- `generate_embeddings` — создание векторов для поиска
- `score_contacts` — расчет relevance score
- `update_channel_stats` — агрегация статистики

### Telegram Integration
**Библиотека**: Telethon

Функционал:
- Аутентификация пользователя
- Синхронизация сообщений
- Мониторинг каналов
- Управление сессиями (в `sessions/`)
- Автоматическое вступление в каналы

### AI Integration
**Провайдеры**: Google Gemini + OpenAI API или LM Studio

Использование:
- Анализ содержания сообщений
- Извлечение контактной информации
- Классификация leads
- Генерация summary'ев

## Data Flow

### Процесс синхронизации

```
1. User инициирует sync → API endpoint
2. API создает Celery task
3. Worker подключается к Telegram
4. Загружает новые сообщения
5. Сохраняет в messages table
6. Запускает task для extraction
```

### Процесс извлечения leads

```
1. New messages поступают в tasks queue
2. Worker анализирует текст через LLM
3. Выявляет контакты (имя, email, phone)
4. Проверяет дубликаты в БД
5. Создает или обновляет record в contacts
6. Запускает embedding generation
7. Вычисляет lead score
```

### Семантический поиск

```
1. User вводит query
2. Frontend отправляет текст в API
3. API генерирует embedding для query
4. Выполняет similarity search в pgvector
5. Возвращает sorted results с scores
6. Frontend отображает результаты
```

## Концепция Multi-Database

Система поддерживает несколько независимых БД для изоляции:

```
Default: crm (Main database)
├── folder: crypto
├── folder: belgrade_news
└── folder: b2b_leads

Custom: crm_research (Secondary database)
├── folder: market_analysis
└── folder: competitor_tracking

Custom: crm_personal (Personal database)
└── folder: networking_events
```

**Преимущества**:
- Разделение данных по типам / проектам
- Независимые searches per DB
- Модульность и гибкость
- Возможность параллельной работы

## Масштабируемость

### Горизонтальное масштабирование

**Backend**:
- Несколько экземпляров FastAPI за nginx/load balancer
- Асинхронная обработка через Celery workers
- Кэширование на Redis

**Database**:
- Replication PostgreSQL (Primary-Replica)
- Read replicas для heavy queries
- Connection pooling

**Message Queue**:
- Несколько Celery workers на разных машинах
- Priority queues для важных задач

### Вертикальное масштабирование
- Увеличение CPU/RAM для DB
- Оптимизация indices
- Batch processing вместо real-time

## Безопасность

### Authentication
- Telegram OAuth2 для авторизации
- JWT tokens для API
- Session management в Redis

### Data Protection
- Шифрование sensitive fields в БД
- HTTPS для all API calls
- Environment variables для secrets

### Database Security
- Prepared statements (SQLAlchemy ORM)
- SQL injection prevention
- Row-level security policies

## Monitoring & Observability

### Logging
- Structured logging в файлы + stdout
- Log levels: DEBUG, INFO, WARNING, ERROR
- Correlation IDs для трейсинга

### Metrics (Prometheus)
- API request latency
- Task queue depth
- Database connections
- Error rates

### Tracing (Optional)
- OpenTelemetry integration
- Jaeger для distributed tracing

## Deployment

### Container Architecture
```
docker-compose services:
- db (PostgreSQL 15+)
- redis (Cache & Broker)
- api (FastAPI Uvicorn)
- worker (Celery)
- frontend (nginx)
```

### Production Deployment
- Kubernetes или Docker Swarm
- CI/CD pipeline (GitHub Actions)
- Database backups и disaster recovery
- Load balancing и auto-scaling

---

Для деталей см.:
- [Multi-Database изоляция](./multi-database.md)
- [Ключевые концепции](./concepts.md)
- [Технологический стек](./tech-stack.md)
