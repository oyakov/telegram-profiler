# Требования и предварительные условия

## Системные требования

### Операционная система
- **Linux** — рекомендуется (Ubuntu 20.04+, Debian 11+)
- **macOS** — поддерживается (Intel и Apple Silicon)
- **Windows** — поддерживается через WSL2 или Docker Desktop

### Оборудование
- **CPU**: 2+ cores
- **RAM**: 4GB минимум (8GB+ рекомендуется)
- **Disk**: 20GB свободного места (для БД и logs)
- **Сетевое подключение**: Стабильное интернет соединение

## Обязательное ПО

### Docker & Docker Compose
- **Docker**: 20.10+
- **Docker Compose**: 2.0+ (V2) или 1.29+

Установка:
```bash
# Ubuntu/Debian
sudo apt-get install docker.io docker-compose

# macOS
brew install docker docker-compose

# Windows
# Скачайте Docker Desktop для Windows
```

### Python (для локальной разработки)
- **Python**: 3.12+
- **pip**: latest version
- **venv**: для virtual environments

Проверка версии:
```bash
python3 --version
pip --version
```

## Учетные данные и API ключи

### Telegram API
**Обязательно** для работы с Telegram:

1. Перейдите на [https://my.telegram.org](https://my.telegram.org)
2. Авторизуйтесь своим номером телефона
3. Откройте **API Development Tools**
4. Получите:
   - `api_id` (числовой ID)
   - `api_hash` (хеш)

### Google AI Studio (рекомендуется)
**Опционально** для улучшенной AI:

1. Перейдите на [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
2. Создайте или используйте существующий API key
3. Сохраните в переменной окружения `GEMINI_API_KEY`

### LM Studio (альтернатива)
**Опционально** для локального LLM:

1. Скачайте [LM Studio](https://lmstudio.ai)
2. Загрузите модель (например, Mistral 7B)
3. Запустите локальный сервер на port 1234
4. Конфигурируйте в `.env`:
   ```
   LM_STUDIO_API_URL=http://localhost:1234
   LLM_PROVIDER=lmstudio
   ```

## Переменные окружения

Основной файл конфигурации — `.env` в корне проекта.

### Telegram
```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890  # для первой авторизации
```

### Database
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=crm
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/crm
```

### AI & LLM
```env
GEMINI_API_KEY=your_api_key
LLM_PROVIDER=gemini  # или lmstudio
LM_STUDIO_API_URL=http://localhost:1234
```

### Redis & Celery
```env
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### Frontend
```env
VITE_API_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
```

## Git конфигурация

Для разработки требуется git:

```bash
# Проверьте установку
git --version

# Конфигурируйте автора
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## IDE & Editor

### Рекомендуемые редакторы
- **VS Code** — с extensions для Python, React, Docker
- **PyCharm** — для Python разработки
- **WebStorm** — для React разработки
- **JetBrains Rider** — если используется C# для интеграций

### VS Code Extensions
```
- Python (Microsoft)
- Docker (Microsoft)
- REST Client (Huachao Mao)
- Thunder Client (or Insomnia)
- Tailwind CSS IntelliSense
- ESLint, Prettier
```

## Проверка готовности

Запустите этот скрипт для проверки всех требований:

```bash
#!/bin/bash

echo "=== System Requirements Check ==="

# Docker
echo -n "Docker: "
docker --version || echo "NOT INSTALLED"

# Docker Compose
echo -n "Docker Compose: "
docker-compose --version || echo "NOT INSTALLED"

# Python
echo -n "Python: "
python3 --version || echo "NOT INSTALLED"

# Git
echo -n "Git: "
git --version || echo "NOT INSTALLED"

# Environment check
echo ""
echo "=== Environment Variables ==="
[ -f .env ] && echo ".env file: ✓" || echo ".env file: MISSING - copy from .env.example"

echo ""
echo "=== Ready to proceed! ==="
```

## Сохранение credentials

**ВАЖНО**: Никогда не коммитьте `.env` в Git! Используйте `.env.example` как template.

```bash
# .env.example не должен содержать реальные secrets
cp .env.example .env
# добавьте реальные значения в .env
echo ".env" >> .gitignore
```

## Следующие шаги

После проверки всех требований:
1. Клонируйте репозиторий
2. Создайте и заполните `.env`
3. Запустите `docker-compose up --build`
4. Следуйте [Быстрому старту](./quick-start.md)

---

**Если есть проблемы**, см. [Troubleshooting](./quick-start.md#troubleshooting)
