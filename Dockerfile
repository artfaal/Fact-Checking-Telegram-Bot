# Multi-stage build для оптимизации размера образа
FROM python:3.11-slim as builder

# Устанавливаем системные зависимости для сборки
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Создаем виртуальное окружение
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.11-slim

# Метаданные
LABEL maintainer="fact-checking-bot" \
      description="Telegram Fact-Checking Bot with Two-Stage Analysis" \
      version="2.0"

# Создаем пользователя для безопасности
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Устанавливаем системные зависимости только для runtime
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копируем виртуальное окружение из builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Создаем рабочую директорию
WORKDIR /app

# Создаем директории для данных
RUN mkdir -p /app/logs /app/data && \
    chown -R botuser:botuser /app

# Копируем исходный код
COPY --chown=botuser:botuser src/ ./src/
COPY --chown=botuser:botuser main.py ./
COPY --chown=botuser:botuser .env.example ./

# Переключаемся на непривилегированного пользователя
USER botuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; print('Bot is healthy')" || exit 1

# Переменные окружения
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Точка входа
CMD ["python", "main.py"]