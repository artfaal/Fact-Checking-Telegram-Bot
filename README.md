# Fact-Checking Telegram Bot v3.0

Простой Telegram-бот для проверки фактов с использованием двухэтапной системы анализа на базе OpenAI GPT-5 и веб-поиска.

## 🎯 Основные возможности

- **Простое использование** - отправьте любое сообщение боту для проверки фактов
- **Двухэтапная система фактчекинга**:
  - Этап 1: Анализ контента → умный выбор источников для проверки
  - Этап 2: Строгий фактчекинг с новой системой верификации:
    - 4 статуса: confirmed, partially_confirmed, contradictory, unconfirmed
    - Числовая оценка достоверности (0-100%)
    - Детальное обоснование с указанием противоречий
- **Умная фильтрация** спама, рекламы и недостоверной информации
- **Подробные логи** и отладочная информация

## 🚀 Быстрый запуск

### 1. Настройка окружения

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd fact-checking-tg

# Создайте .env файл
cp .env.example .env
```

### 2. Заполните .env файл

```bash
# Telegram API credentials
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token

# OpenAI API key
OPENAI_API_KEY=your_openai_key

# Optional tuning
GPT_MODEL=gpt-5
FACT_CHECK_MODEL=gpt-4o
WEB_SEARCH_EFFORT=medium
MAX_SOURCE_DOMAINS=20
STAGE2_INITIAL_DOMAIN_LIMIT=8
STAGE2_RETRY_DOMAIN_LIMIT=5
FACT_CHECK_TIMEOUT=45
STAGE1_MAX_TOKENS=1500
STAGE2_MAX_TOKENS=2000
```

Все параметры имеют значения по умолчанию и настраиваются при необходимости. Отладочные логи включены всегда, поэтому переменная `DEBUG_MODE` отдельно не требуется.

### 3. Запуск через Docker (рекомендуется)

```bash
docker-compose up -d
```

### 4. Локальный запуск

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python main.py
```

## 💬 Как использовать

1. Найдите вашего бота в Telegram
2. Отправьте `/start` для начала работы
3. Отправьте любое текстовое сообщение для проверки фактов
4. Получите детальный анализ с оценкой достоверности

**Пример:**
```
Discord объявил новую функцию ИИ-модерации голосовых каналов
```

**Ответ бота:**
```
✅ Проверка фактов завершена

📰 Категория: НОВОСТИ  
🤖 Результат: Не подтверждено (доверие: 20%) - No evidence found...
```

## 📊 Возможные результаты

- ✅ **Достоверно** (90-100%) - подтверждено источниками
- ⚠️ **Частично подтверждено** (60-89%) - частично подтверждено  
- ❌ **Противоречит источникам** (30-59%) - найдены противоречия
- ❓ **Не подтверждено** (0-29%) - нет доказательств
- 🗑️ **Спам** - реклама, мусор

## 🧪 Тестирование

```bash
# Запуск всех тестов
python run_tests.py

# Запуск отдельных тестов
python tests/test_config.py
python tests/test_check_command.py
python tests/test_two_stage.py
```

## 🔒 Безопасность

- **Git история очищена**: Все API ключи удалены из истории git с помощью BFG
- **Pre-commit хуки**: Gitleaks автоматически проверяет коммиты на утечки
- **Переменные окружения**: Все секреты хранятся в .env файле

## 📄 Лицензия

MIT License

## 👥 Поддержка

- Создайте Issue в репозитории для багов
- Pull Requests приветствуются
