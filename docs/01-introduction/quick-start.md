# Быстрый старт

## Требования

- Docker & Docker Compose
- Telegram API Credentials (`api_id` и `api_hash`)
- (Опционально) Google AI Studio API Key или LM Studio

## Установка за 5 шагов

### 1. Клонирование репозитория

```bash
git clone https://github.com/oyakov/telegram-profiler.git
cd telegram-profiler
```

### 2. Конфигурация переменных окружения

```bash
cp .env.example .env
```

Отредактируйте `.env` с вашими учетными данными:
- `TELEGRAM_API_ID` — ваш Telegram API ID
- `TELEGRAM_API_HASH` — ваш Telegram API Hash
- `GEMINI_API_KEY` — Google AI API key (опционально)

### 3. Запуск с Docker Compose

```bash
docker-compose up --build
```

Это запустит:
- **PostgreSQL** — база данных с pgvector
- **Redis** — брокер задач
- **FastAPI Backend** — API на `http://localhost:8000`
- **Celery Worker** — обработка фоновых задач
- **React Frontend** — UI на `http://localhost:3005`

### 4. Первый запуск

1. Откройте [http://localhost:3005](http://localhost:3005)
2. Авторизуйтесь через Telegram
3. Добавьте папку для отслеживания (e.g., "Crypto", "Belgrade News")
4. Выберите каналы для мониторинга
5. Запустите синхронизацию

### 5. Изучите интерфейс

- **Dashboard (Обзор)** — статистика и recent leads
- **Search** — семантический поиск контактов
- **Contacts** — управление контактами и ведение notes
- **Settings** — конфигурация и управление папками
- **Audit** — история изменений

## API Документация

Интерактивная Swagger документация доступна на:
```
http://localhost:8000/docs
```

## Типичный workflow

### Новый пользователь

1. **Setup** → Добавить папку → Добавить каналы
2. **Monitor** → Ждать обнаружения контактов
3. **Review** → Проверить качество leads
4. **Search** → Найти контакты по критериям
5. **Contact** → Взаимодействовать с leads

### Опытный пользователь

- Управление несколькими БД
- Настройка scoring параметров
- Использование тематического открытия
- Аналитика трендов

## Типичные операции

### Добавить канал для отслеживания

```bash
curl -X POST http://localhost:8000/api/channels \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "crypto",
    "channel_username": "bitcoin",
    "auto_join": true,
    "mute": true
  }'
```

### Поиск контактов

```bash
curl -X POST http://localhost:8000/api/contacts/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "developer looking for funding",
    "limit": 10
  }'
```

### Получить leads

```bash
curl http://localhost:8000/api/leads?sort=score&limit=20
```

## Troubleshooting

### Database connection failed
- Убедитесь, что PostgreSQL запущен: `docker-compose ps`
- Проверьте переменные окружения в `.env`

### Telegram auth не работает
- Убедитесь, что `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` правильные
- Сессии хранятся в `sessions/` — удалите их и переавторизуйтесь

### API returns 503
- Проверьте, работают ли все сервисы: `docker-compose logs backend`
- Перезагрузите контейнеры: `docker-compose restart`

## Следующие шаги

- [Полная архитектура](../02-architecture/overview.md)
- [Style Guides](../04-development/style-guides/)
- [Feature Documentation](../05-features/)

---

**Нужна помощь?** Смотрите полную документацию в разделах выше.
