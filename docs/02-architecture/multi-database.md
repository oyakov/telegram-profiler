# Multi-Database Architecture

## Концепция

Networking Brain поддерживает **несколько независимых баз данных** для изоляции и управления данными в зависимости от типа проекта, клиента или категории отслеживания.

## Зачем нужна Multi-Database?

### Задачи, которые решает

1. **Разделение данных** — изолировать данные разных проектов (e.g., "Crypto" vs "Belgrade News")
2. **Масштабируемость** — распределить нагрузку между несколькими БД
3. **Безопасность** — ограничить доступ к чувствительным данным
4. **Производительность** — меньше данных = быстрее поиск
5. **Гибкость** — легко добавлять новые проекты без влияния на существующие

## Архитектура

### Иерархия

```
User
  └── Workspace (может иметь несколько БД)
      ├── Database: crm_main
      │   ├── Folder: Crypto
      │   │   ├── Channel: bitcoin
      │   │   ├── Channel: ethereum
      │   │   └── ...
      │   ├── Folder: Belgrade News
      │   │   ├── Channel: bg_intel
      │   │   └── ...
      │   └── ...
      ├── Database: crm_research
      │   ├── Folder: Market Analysis
      │   └── Folder: Competitor Tracking
      └── Database: crm_personal (опционально)
          └── Folder: Networking Events
```

### Конфигурация в .env

```env
# Default (Primary) Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/crm

# Additional Databases (опционально)
DATABASE_URLS={
  "crm_research": "postgresql+asyncpg://user:pass@db:5432/crm_research",
  "crm_personal": "postgresql+asyncpg://user:pass@db:5432/crm_personal"
}

# Или через environment variables
DATABASES__CRYPTO=postgresql+asyncpg://user:pass@db:5432/crm_crypto
DATABASES__RESEARCH=postgresql+asyncpg://user:pass@db:5432/crm_research
```

## Модель данных

### Таблицы, которые дублируются в каждой БД

```
contacts          — извлеченные контакты
messages          — сообщения из Telegram
leads             — identified leads с scores
embeddings        — векторные представления
channel_messages  — связь между каналами и сообщениями
contact_channels  — в каких каналах активен контакт
audit_logs        — история изменений
```

### Таблицы, которые НЕ дублируются (глобальные)

```
users             — учетные записи пользователей
workspaces        — рабочие пространства
user_databases    — привязка пользователя к БД
```

### Структура таблицы user_databases

```sql
CREATE TABLE user_databases (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  database_name VARCHAR NOT NULL,
  database_url VARCHAR NOT NULL,  -- connection string
  folder_id VARCHAR,              -- опционально, для фильтрации
  created_at TIMESTAMP DEFAULT NOW(),
  is_active BOOLEAN DEFAULT true,
  
  UNIQUE(user_id, database_name)
);
```

## Использование в API

### Выбор БД через параметр

```python
# API endpoint
@router.get("/contacts")
async def get_contacts(db_name: str = "crm"):
    """
    Query параметр 'db_name' указывает, какую БД использовать
    Пример: GET /api/contacts?db_name=crm_research
    """
    session = get_session(db_name)
    contacts = session.query(Contact).all()
    return contacts
```

### В коде бэкенда

```python
# src/db/session.py
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

db_manager = DatabaseManager()
```

### В миграциях

```bash
# Migrate primary DB
alembic upgrade head

# Migrate specific DB
# Требует создания отдельного alembic env per DB (опционально)
ALEMBIC_DATABASE=crm_research alembic upgrade head
```

## Стратегия синхронизации

### Сценарий 1: Независимая синхронизация

```
User настраивает папку в crm (crypto)
  ↓ автоматическая синхронизация Telegram ↓
  Сообщения сохраняются только в crm/contacts

User настраивает ту же папку в crm_research
  ↓ отдельная синхронизация ↓
  Те же сообщения могут быть загружены второй раз
```

**Решение**: Использовать shared `messages_archive` или деduplicate на уровне API.

### Сценарий 2: Shared messages между БД

```python
# Вариант: общая таблица messages для всех БД
# (требует более сложной архитектуры)

CREATE TABLE public.messages (
  id UUID PRIMARY KEY,
  telegram_message_id INTEGER,
  channel_id INTEGER,
  content TEXT,
  created_at TIMESTAMP
);

# А в каждой БД сохранять только references:
CREATE TABLE contacts (
  id UUID PRIMARY KEY,
  name VARCHAR,
  -- другие поля
);

CREATE TABLE contact_message_refs (
  contact_id UUID REFERENCES contacts(id),
  message_id UUID REFERENCES public.messages(id),
  database_name VARCHAR  -- какой БД "видит" это сообщение
);
```

## Примеры использования

### Frontend: Выбор БД

```typescript
// src/services/api.ts
const getContacts = async (dbName: string = 'crm') => {
  const response = await fetch(`/api/contacts?db_name=${dbName}`);
  return response.json();
};

// В компоненте
const [selectedDb, setSelectedDb] = useState('crm');
const [contacts, setContacts] = useState([]);

useEffect(() => {
  getContacts(selectedDb).then(setContacts);
}, [selectedDb]);

return (
  <div>
    <select value={selectedDb} onChange={(e) => setSelectedDb(e.target.value)}>
      <option value="crm">Main Database</option>
      <option value="crm_research">Research Database</option>
      <option value="crm_personal">Personal Database</option>
    </select>
    {/* Show contacts from selected DB */}
  </div>
);
```

### Backend: Миграция между БД

```python
# src/utils/migration.py
async def migrate_contacts(from_db: str, to_db: str):
    """Migrate contacts from one database to another"""
    
    from_session = db_manager.get_session(from_db)
    to_session = db_manager.get_session(to_db)
    
    async with from_session as fs, to_session as ts:
        contacts = await fs.query(Contact).all()
        
        for contact in contacts:
            new_contact = Contact(**contact.dict())
            ts.add(new_contact)
        
        await ts.commit()
```

## Производительность

### Оптимизация

1. **Connection Pooling** — кэширование connections per DB
2. **Query Optimization** — индексы на часто используемых полях
3. **Caching Layer** — Redis для кэширования popular queries
4. **Lazy Loading** — загрузка related objects только при необходимости

### Метрики мониторинга

```
Per Database:
- Number of active connections
- Average query latency
- Slow query count
- Index usage stats
```

## Ограничения и considerations

### Консистентность данных

- Нет глобальных foreign keys между БД
- Нужна логика на уровне приложения для cross-DB references
- Async реplication требует обработки eventual consistency

### Управление миграциями

- Каждая БД может иметь разную версию схемы
- Требуется система версионирования миграций per DB
- Нужна процедура для синхронизации схем

### Масштабируемость

- Количество БД может быть ограничено ресурсами машины
- Нужно мониторить load распределение
- Возможна необходимость в database sharding в будущем

## Fallback & Recovery

### При недоступности БД

```python
async def get_contacts_with_fallback(db_name: str):
    try:
        return await db_manager.get_session(db_name).query(Contact).all()
    except DatabaseError:
        # Fallback to primary DB
        logger.warning(f"Database {db_name} unavailable, using fallback")
        return await db_manager.get_session("crm").query(Contact).all()
```

## Будущие улучшения

1. **Database Sharding** — горизонтальное разделение данных
2. **Multi-Region Replication** — репликация между регионами
3. **Automatic Failover** — переключение на replica при отказе
4. **Query Federation** — queries через несколько БД одновременно

---

**Статус**: Реализовано в v1.0  
**Ответственность**: Backend/DevOps team  
**Последнее обновление**: 2026-05-08
