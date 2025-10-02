# 🤖 Fact-Checking Telegram Bot v3.2

Простой Telegram-бот для проверки фактов с использованием двухэтапной системы анализа на базе OpenAI GPT-5 и веб-поиска.

## ✨ Основные возможности

- **Простое использование** - отправьте любое сообщение боту для проверки фактов
- **Двухэтапная система фактчекинга**:
  - 🔍 **Этап 1**: Анализ контента → умный выбор источников для проверки
  - ✅ **Этап 2**: Строгий фактчекинг с веб-поиском по надежным источникам
- **Система верификации**:
  - ✅ **Достоверно** (90-100%) - подтверждено источниками
  - ⚠️ **Частично подтверждено** (60-89%) - частично подтверждено
  - ❌ **Противоречит источникам** (30-59%) - найдены противоречия
  - ❓ **Не подтверждено** (0-29%) - нет доказательств
  - 🤡 **Развлечения/шутки** - упрощенный формат для несерьезного контента
- **Умная фильтрация** спама, рекламы и недостоверной информации
- **Подробные объяснения** с указанием конкретных источников и причин решения

## 🚀 Быстрый запуск

### 1. Настройка

```bash
# Клонируйте репозиторий
git clone https://github.com/artfaal/Fact-Checking-Telegram-Bot.git
cd Fact-Checking-Telegram-Bot

# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установите зависимости
pip install -r requirements.txt

# Создайте файл конфигурации
cp .env.example .env
```

### 2. Настройте .env

```bash
# Обязательные параметры
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
```

### 3. Запуск

```bash
# Локально
python main.py

# Или через Docker
docker-compose up -d
```

## 💬 Использование

1. **Найдите вашего бота** в Telegram (используйте токен из @BotFather)
2. **Отправьте любое текстовое сообщение** для проверки фактов
3. **Получите детальный анализ** с процентом доверия и объяснениями

### Пример ответа

```
❓ Доверие: 20%
🤖 Комментарий: Не подтверждено - No evidence found confirming that Crystal Dynamics announced layoffs and stated they would not affect the future of the Tomb Raider series

🌐 Источники: crystald.com, square-enix-games.com, gamesindustry.biz, ign.com, kotaku.com

💭 Логика выбора: Сообщение содержит информацию о сокращении сотрудников в известной игровой студии, что требует проверки на достоверность.
```

## 🐳 Docker

```yaml
# docker-compose.yml
version: '3.8'
services:
  fact-checker:
    build: .
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    environment:
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    restart: unless-stopped
```

## 🧪 Тестирование

```bash
# Запуск всех тестов
python run_tests.py

# Отдельные тесты
python tests/test_config.py
python tests/test_check_command.py
python tests/test_two_stage.py
```

## 📊 Статистика

- **Модель Stage 1**: GPT-5 для анализа и выбора источников
- **Модель Stage 2**: GPT-4o для фактчекинга с веб-поиском
- **Источники**: 20+ категорий надежных источников
- **Время ответа**: 10-30 секунд в зависимости от сложности
- **Точность**: Улучшенная система с детекцией противоречий

## ⚙️ Конфигурация

Основные настройки в `.env`:

```bash
# Модели
GPT_MODEL=gpt-5                      # Модель для Stage 1
FACT_CHECK_MODEL=gpt-4o             # Модель для Stage 2

# Источники
MAX_SOURCE_DOMAINS=20               # Максимум доменов для проверки
STAGE2_INITIAL_DOMAIN_LIMIT=8       # Домены в первой попытке
STAGE2_RETRY_DOMAIN_LIMIT=5         # Домены при повторе

# Тайм-ауты
FACT_CHECK_TIMEOUT=45               # Таймаут факт-чека (секунды)

# Токены
STAGE1_MAX_TOKENS=1500              # Лимит токенов Stage 1
STAGE2_MAX_TOKENS=2000              # Лимит токенов Stage 2

# Веб-поиск
WEB_SEARCH_EFFORT=medium            # Уровень детализации (low/medium/high)
```

## 🔐 Безопасность

- ✅ Все секреты удалены из git истории с помощью BFG
- ✅ Pre-commit hooks с Gitleaks предотвращают утечку секретов
- ✅ `.env` файл в `.gitignore`
- ✅ Валидация JSON ответов предотвращает инъекции
- ✅ Docker контейнер работает с непривилегированным пользователем

## 📁 Структура проекта

```
├── main.py                  # Точка входа
├── src/                     # Исходный код
│   ├── config.py           # Конфигурация
│   ├── command_handler.py  # Обработка сообщений
│   ├── two_stage_filter.py # Двухэтапная система
│   └── sources_config.py   # Конфигурация источников
├── tests/                   # Тесты
├── logs/                    # Логи (Docker volume)
├── data/                    # Данные сессий (Docker volume)
├── Dockerfile              # Образ Docker
└── docker-compose.yml      # Конфигурация развертывания
```

## 🐛 Отладка

Полные логи записываются в `logs/fact_checker.log`:

```bash
# Просмотр логов
tail -f logs/fact_checker.log

# В Docker
docker-compose logs -f
```

## 📝 Лицензия

MIT License - см. [LICENSE](LICENSE) для подробностей.

## 🤝 Вклад

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📞 Поддержка

- 🐛 **Issues**: [GitHub Issues](https://github.com/artfaal/Fact-Checking-Telegram-Bot/issues)
- 📧 **Email**: [your-email@example.com]
- 💬 **Telegram**: [@your_username]

---

🤖 Generated with [Claude Code](https://claude.ai/code)