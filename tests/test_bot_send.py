#!/usr/bin/env python3
"""
Тест отправки сообщений ботом
"""

import asyncio
import logging
from telegram_client import TelegramBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockMessage:
    def __init__(self, text):
        self.id = 123
        self.text = text
        self.caption = None
        self.photo = None
        self.video = None
        self.document = None

async def test_bot():
    """Тест отправки сообщения ботом"""
    logger.info("🤖 Тестируем Telegram бота...")
    
    try:
        bot = TelegramBot()
        await bot.start()
        
        # Создаем тестовое сообщение
        mock_message = MockMessage("Тест фактчекинга: это тестовое сообщение для проверки работы бота")
        
        # Отправляем отфильтрованное сообщение
        await bot.send_filtered_message(
            original_message=mock_message,
            channel_name="Test Channel",
            category="другое",
            gpt_comment="Тестовый комментарий GPT"
        )
        
        logger.info("✅ Тестовое сообщение отправлено!")
        
        await bot.stop()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка бота: {e}")
        return False

async def main():
    logger.info("🚀 Запуск тестов бота...")
    
    bot_ok = await test_bot()
    
    if bot_ok:
        logger.info("✅ Бот готов к работе!")
    else:
        logger.error("❌ Проблемы с ботом")

if __name__ == "__main__":
    asyncio.run(main())