# Networking Brain CRM - Документация

Полная документация проекта Networking Brain — персонального CRM с AI-powered извлечением контактов и семантическим поиском.

---

## 📋 Содержание

### [1. Введение](./01-introduction/)
- [Обзор проекта](./01-introduction/overview.md)
- [Быстрый старт](./01-introduction/quick-start.md)
- [Требования](./01-introduction/requirements.md)

### [2. Архитектура](./02-architecture/)
- [Архитектурный обзор](./02-architecture/overview.md)
- [Multi-Database изоляция](./02-architecture/multi-database.md)
- [Технологический стек](./02-architecture/tech-stack.md)
- [Ключевые концепции](./02-architecture/concepts.md)
- [Структура проекта](./02-architecture/project-structure.md)
- [Сводка архитектурных консолидаций](./02-architecture/consolidation-summary.md)

### [3. Продукт](./03-product/)
- [Определение продукта](./03-product/definition.md)
- [Руководство по продукту](./03-product/guidelines.md)
- [Метрики успеха](./03-product/metrics.md)

### [4. Разработка](./04-development/)
- [Рабочий процесс](./04-development/workflow.md)
- [Style Guide: General](./04-development/style-guides/general.md)
- [Style Guide: Python](./04-development/style-guides/python.md)
- [Требования к тестам](./04-development/testing.md)
- [Известные проблемы (Known Issues)](./04-development/known-issues.md)

### [5. Описание Функциональности](./05-features/)
- [Импорт папок Telegram](./05-features/telegram-folder-import.md)
- [Архитектура векторных эмбеддингов](./05-features/embeddings-implementation.md)
- [Быстрый старт по эмбеддингам](./05-features/embeddings-quick-start.md)

### [6. Управление Проектом](./06-project-management/)
- [Сводка реализации Celery и pgvector](./06-project-management/embeddings-implementation-summary.md)
- [Отчет по системным метрикам и здоровью](./06-project-management/system-metrics-report.md)
- [Результаты код-ревью и приоритетные улучшения](./06-project-management/code-review-report.md)
- [Кандидаты для расширения каналов Telegram](./06-project-management/expansion-candidates.md)

### [7. Паттерны и навыки разработки](./07-patterns/)
- [Паттерн: Host-side обработка Telethon](./07-patterns/pattern_host_side_processing.md)
- [Паттерн: Тематический поиск каналов](./07-patterns/pattern_thematic_discovery.md)

---

## 🚀 Быстрые ссылки

- **Начало работы**: [Быстрый старт](./01-introduction/quick-start.md)
- **Структура кода**: [Структура проекта](./02-architecture/project-structure.md)
- **Разработка**: [Рабочий процесс](./04-development/workflow.md)
- **API**: http://localhost:8000/docs (когда сервер запущен)
- **Frontend**: http://localhost:3005

---

## 🔧 Инструменты и утилиты

- **Docker Compose**: Управление всеми сервисами
- **FastAPI Docs**: Автоматическая документация API
- **Pytest**: Модульное тестирование
- **Alembic**: Миграции базы данных

---

## 📞 Контакты и поддержка

Для вопросов и обсуждения функциональности см. соответствующие разделы документации.

---

**Последнее обновление**: 2026-05-20  
