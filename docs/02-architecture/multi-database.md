# Multi-Database Architecture / Изоляция Multi-Database

This document describes the multi-database architecture implemented to support isolated Telegram folders, dynamic tenant routing, and thematic data separation.

---

## 1. Overview & Goals / Концепция и Задачи

Networking Brain поддерживает **несколько независимых баз данных** для изоляции и управления данными в зависимости от типа проекта, клиента или категории отслеживания.

### Goals / Задачи, которые решает Multi-DB:
1. **Разделение данных (Data Isolation)** — изолировать данные разных проектов (e.g., "Crypto" vs "Belgrade News").
2. **Масштабируемость (Scalability)** — распределить нагрузку между несколькими БД.
3. **Безопасность (Security)** — ограничить доступ к чувствительным данным.
4. **Производительность (Performance)** — меньший объем данных в каждой базе ускоряет поиск.
5. **Гибкость (Flexibility)** — легкое добавление новых проектов без влияния на существующие.

### Data Isolation Strategy
- **Base Database**: `crm` (используется для системных конфигураций).
- **Thematic Databases**: Имеют префикс `crm_` (e.g., `crm_bg_intel`, `crm_bg_rent`).
- **Dynamic Routing**: Все коннекторы и пайплайн-задачи Celery принимают параметр `db_name` для динамической маршрутизации операций к нужной базе данных.

---

## 2. Architecture & Hierarchy / Структура и Иерархия

```
User
  └── Workspace (может иметь несколько БД)
      ├── Database: crm (Base / Default)
      │   ├── Folder: Crypto
      │   │   ├── Channel: bitcoin
      │   │   ├── Channel: ethereum
      │   │   └── ...
      │   ├── Folder: Belgrade News
      │   │   ├── Channel: bg_intel
      │   │   └── ...
      ├── Database: crm_bg_rent
      │   ├── Folder: Belgrade Rent
      │   └── Folder: Competitor Tracking
```

### Configuration in `.env`
Базы данных конфигурируются следующим образом:
```env
# Default (Primary) Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/crm

# Additional Databases (dynamic prefix matching)
DATABASES__CRYPTO=postgresql+asyncpg://user:pass@db:5432/crm_crypto
DATABASES__RESEARCH=postgresql+asyncpg://user:pass@db:5432/crm_research
```

---

## 3. Core Components / Основные Компоненты

### 1. Database Manager (`src/db/database.py`)
- **`ensure_database_exists(name)`**: Автоматически создает PostgreSQL базу данных, если она еще не создана на инстансе.
- **`init_database_schema(name)`**: Инициализирует базовую схему (таблицы, индексы) и включает расширение `pgvector` для семантического поиска.
- **Connection Pooling**: Менеджер соединений кэширует сессии SQLAlchemy по имени базы для исключения перекрестного доступа (cross-talk).

```python
# src/db/database.py (DatabaseManager implementation overview)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

class DatabaseManager:
    def __init__(self):
        self.engines = {}  # db_name -> engine
    
    def get_engine(self, db_name: str = "crm"):
        if db_name not in self.engines:
            url = config.get_database_url(db_name)
            self.engines[db_name] = create_async_engine(url)
        return self.engines[db_name]
    
    async def get_session(self, db_name: str = "crm"):
        engine = self.get_engine(db_name)
        async_session = sessionmaker(engine, class_=AsyncSession)
        async with async_session() as session:
            yield session
```

### 2. Telegram Connector (`src/connectors/telegram_connector.py`)
- **Isolated Sessions**: Использует уникальные файлы сессий Telethon (`sessions/<db_name>.session`) для сохранения состояния авторизации и разделения Telegram-подключений.
- **Folder Sync**: Связывает структуру папок Telegram с конкретными БД, конвертируя названия папок в slug-имена баз.
- **ID Resolution**: Поддерживает как целочисленные (`int`), так и строковые (`str`) идентификаторы (peer IDs) для полной совместимости при ручном и автоматическом вступлении в каналы.

---

## 4. Data Model Strategy / Модели Данных

### Tables Duplicated in Each Database (Tenant Isolation)
Эти таблицы хранятся локально в каждой тематической базе данных:
```
contacts          — извлеченные контакты
messages          — сообщения из Telegram
leads             — выявленные лиды с оценками (scores)
message_embeddings— векторы сообщений (pgvector)
channel_messages  — связь между каналами и сообщениями
```

### Shared / Global Tables (Main crm Database)
Хранят общие глобальные данные для всей системы:
```
users             — учетные записи пользователей
workspaces        — рабочие пространства
user_databases    — связи пользователей с доступными им БД
```

---

## 5. Operations & Execution / Операции и Выполнение

### Global Sync Orchestration
Системные скрипты (например, `deep_sync_all_multi_db.py`) осуществляют обход всех зарегистрированных tenant-баз, соответствующих шаблону `crm_*`, и запускают синхронизацию сообщений последовательно или параллельно.

### Processing Pipeline (Celery)
Фоновые задачи Celery полностью спроектированы под концепцию Multi-DB. Задачи генерации эмбеддингов (`process_message_embeddings`) или анализа лидов запускаются изолированно в контексте конкретной переданной `db_name`, гарантируя разграничение вычислений и хранилищ.

### API Endpoint Usage
Роутеры FastAPI принимают в заголовках (`X-Database`) или в query-параметрах (`db_name`) целевую базу данных:
```python
# API Endpoint Example
@router.get("/contacts")
async def get_contacts(db_name: str = "crm"):
    async with db_manager.get_session(db_name) as session:
        contacts = await ContactService.list_contacts(session)
        return contacts
```

### Tenant Migrations via Alembic
Миграции запускаются как для основной, так и для конкретной тематической БД:
```bash
# Migrate primary DB
alembic upgrade head

# Migrate specific dynamic DB
ALEMBIC_DATABASE=crm_research alembic upgrade head
```

---

## 6. Sync Scenarios / Сценарии Синхронизации

### Scenario A: Independent Sync (Независимая синхронизация)
Пользователь мониторит одну папку в основной crm и другую в crm_research. Телеграм-сообщения скачиваются отдельно и сохраняются только в соответствующую БД.

### Scenario B: Cross-DB Migration Utility
Пример утилиты переноса контактов между базами:
```python
# src/utils/migration.py
async def migrate_contacts(from_db: str, to_db: str):
    async with db_manager.get_session(from_db) as fs, db_manager.get_session(to_db) as ts:
        contacts = await fs.query(Contact).all()
        for contact in contacts:
            new_contact = Contact(**contact.dict())
            ts.add(new_contact)
        await ts.commit()
```

---

## 7. Performance & Optimization / Оптимизация Производительности

1. **Connection Pooling**: SQLAlchemy `AsyncEngine` пулы создаются отдельно для каждой базы данных и кэшируются, предотвращая перегрузку СУБД.
2. **pgvector Indexes**: Для таблиц эмбеддингов локально в каждой базе создается HNSW индекс для обеспечения быстрого сходства косинусного расстояния.
3. **Caching Layer**: Redis кэширует частые запросы (например, статистику `/stats/tree`) с использованием ключей с префиксом базы данных (`tree:msg_counts:{db_name}`).

---

**Last Updated / Последнее обновление**: 2026-05-20  
