#!/usr/bin/env python3
"""
Тестирование конфигурации и основных компонентов
"""

import asyncio
import logging
from config import Config
from openai_filter import OpenAIFilter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_config():
    """Тест конфигурации"""
    logger.info("🔧 Тестируем конфигурацию...")
    
    try:
        Config.validate()
        logger.info("✅ Конфигурация валидна")
        logger.info(f"📡 Каналы: {Config.get_channels()}")
        logger.info(f"📤 Целевой чат: {Config.TARGET_CHAT_ID}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка конфигурации: {e}")
        return False

async def test_openai():
    """Тест OpenAI фильтра"""
    logger.info("🤖 Тестируем OpenAI фильтр...")
    
    try:
        filter_ai = OpenAIFilter()
        
        test_messages = [
            "Спам! Купи дешевые товары прямо сейчас!",
            "Сегодня президент подписал новый закон об образовании",
            "Новый фильм Marvel побил все рекорды в прокате",
            "Слишком короткий"
        ]
        
        for i, message in enumerate(test_messages):
            category, comment = await filter_ai.analyze_message(message, "test_channel")
            logger.info(f"Тест {i+1}: '{message[:50]}...' -> {category} | {comment}")
            
        logger.info("✅ OpenAI фильтр работает")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка OpenAI: {e}")
        return False

async def main():
    logger.info("🚀 Запуск тестов...")
    
    config_ok = await test_config()
    
    if config_ok:
        openai_ok = await test_openai()
    else:
        logger.error("❌ Пропускаем тест OpenAI из-за ошибки конфигурации")
        openai_ok = False
    
    if config_ok and openai_ok:
        logger.info("✅ Все тесты пройдены! Приложение готово к запуску.")
    else:
        logger.error("❌ Некоторые тесты не пройдены. Проверьте настройки.")

if __name__ == "__main__":
    asyncio.run(main())