# Определение продукта

## Первоначальная концепция

Личный CRM с AI-powered извлечением контактов и семантическим поиском, разработанный как "Networking Brain" — умная система для управления профессиональной сетью.

## Начальная фокус / Starting Task

Основной starting point этой концепции — **идентификация людей, которые покупают рекламу в определённых каналах**. Система собирает этих leads и ранжирует их, используя комбинацию LLM анализа и эвристик.

### Почему это важно?

- **Продавцы** ищут покупателей рекламы (potential clients)
- **Трудно вручную** отслеживать кто и где размещает объявления
- **Много каналов** — информация разрознена
- **AI может помочь** автоматизировать процесс поиска

## Целевая аудитория

Основные пользователи Networking Brain:

### 1. Sales Professionals & SDRs
- Поиск и квалификация leads
- Управление sales pipeline
- Отслеживание взаимодействий с контактами

### 2. Solopreneurs & Business Owners
- Расширение сети контактов
- Поиск потенциальных партнеров
- Мониторинг конкурентов

### 3. Researchers & Analysts
- Сбор данных о тренде в индустрии
- Анализ рынков и конкурентов
- Мониторинг активности ключевых игроков

### 4. Community Managers
- Идентификация активных членов сообщества
- Поиск потенциальных спикеров и модераторов
- Анализ sentiment и тренды обсуждений

## Основное ценностное предложение

Networking Brain действует как **Централизованный Hub**.

### Проблема, которую решаем

**Before (без Networking Brain):**
```
Telegram Channel 1
Telegram Channel 2
Telegram Channel 3
Email inbox
LinkedIn messages
Excel spreadsheet (old)
← Данные разрозненны, трудно управлять
← Много информации теряется
← Ручное отслеживание неэффективно
← Неясно, кто "высокоценный"
```

**After (с Networking Brain):**
```
All Data → [Consolidated Hub]
          ├─ One search interface
          ├─ AI-ranked contacts
          ├─ Semantic search
          └─ Analytics & insights
```

### Что даёт Networking Brain

1. **Консолидация** — все источники данных в одном месте
2. **Автоматизация** — AI находит контакты без ручной работы
3. **Ранжирование** — система показывает самых ценных contacts first
4. **Поиск** — найти контакт за секунды по смыслу
5. **Действие** — всё, что нужно для контакта с lead (в roadmap)

## Метрики успеха

Успех продукта измеряется в первую очередь:

### 1. Search Engagement
- **Метрика**: Среднее количество searches в неделю на пользователя
- **Goal**: > 10 searches/week = пользователь активно использует
- **Почему**: Если поиск не используется, не используется и продукт

### 2. Lead Quality
- **Метрика**: Процент выявленных контактов, что действительно valuable
- **Goal**: > 70% контактов со score > 50 = качественные leads
- **Почему**: Низкое качество → не доверяют системе

### 3. Time Saved
- **Метрика**: Hours saved per week vs manual process
- **Goal**: Сэкономить > 5 hours/week на поиск контактов
- **Почему**: ROI для пользователя

### 4. Contact Coverage
- **Метрика**: % потенциальных контактов, что система нашла
- **Goal**: > 80% contacts from monitored channels
- **Почему**: Если пропускаем contacts, система неполная

### 5. User Retention
- **Метрика**: Monthly Active Users (MAU) vs sign-ups
- **Goal**: > 60% retention after 30 days
- **Почему**: Long-term viability

## Future Vision: AI Assistants

### Фаза 1 (Текущая): Foundation
✅ Консолидация данных
✅ AI-powered идентификация
✅ Семантический поиск
✅ Lead scoring

### Фаза 2: Intelligence (Q3 2026)
- Продвинутая аналитика
- Предсказательные модели
- Behavior patterns

### Фаза 3: Automation (Q4 2026)
- **Draft Messages**: AI генерирует персонализированные follow-ups
- **Auto-Categorization**: Автоматическое маркирование
- **Recommendation Engine**: "Контакты, похожие на..."

### Фаза 4: Action (2027)
- **Integrated Communication**: Отправка messages прямо из системы
- **CRM Integration**: Sync с Salesforce, HubSpot
- **Calendar Integration**: Scheduling и reminders
- **Email Plugin**: Capture contcts из email threads

**Долгосрочная цель**: Превратить Networking Brain из **passive database** в **active networking partner**, который помогает пользователю на каждом шаге sales process.

## Конкурентные преимущества

| Аспект | Существующие решения | Networking Brain |
|--------|-----------------|------------|
| Источники данных | Одна платформа | Multi-source consolidation |
| Идентификация | Ручная работа | AI-powered автоматизация |
| Поиск | Keyword-based | Semantic + scoring |
| Масштабируемость | Дорогие | Multi-database isolation |
| Кастомизация | Ограниченная | Flexible architecture |
| Cost | High | Low (self-hosted) |

## Non-Goals (Что мы НЕ делаем)

- 🚫 Заменитель LinkedIn Sales Navigator
- 🚫 Email campaign builder (for now)
- 🚫 Phone call logging system
- 🚫 Full CRM (only contacts + leads)
- 🚫 Telegram bot for spamming

---

**Эта документация определяет направление продукта и должна регулярно обновляться.**

**Последнее обновление**: 2026-05-08  
**Ответственность**: Product team
