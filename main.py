#!/usr/bin/env python3
"""
Fact-Checking Bot v3.0 - Simplified Direct Message Bot
"""

import asyncio
import logging
import os
import signal
import sys
from pyrogram import Client, filters
from pyrogram.types import Message

# Импорты из src
sys.path.append('src')
from config import Config
from command_handler import CommandHandler

# Настройка логирования
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fact_checker.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class FactCheckingBot:
    def __init__(self):
        self.bot = Client(
            "fact_checker_bot",
            api_id=Config.TELEGRAM_API_ID,
            api_hash=Config.TELEGRAM_API_HASH,
            bot_token=Config.TELEGRAM_BOT_TOKEN
        )
        self.command_handler = CommandHandler()
        self.running = False

    async def start(self):
        """Запуск бота"""
        try:
            Config.validate()
            logger.info("✅ Конфигурация валидна")
            
            await self.bot.start()
            
            # Обработчик команды /help и /start
            @self.bot.on_message(filters.command(["help", "start"]) & filters.private)  
            async def handle_help_command(client, message: Message):
                await self.command_handler.handle_help_command(client, message)
            
            # Обработчик любого текстового сообщения (кроме команд)
            @self.bot.on_message(filters.text & filters.private & ~filters.command(["help", "start"]))
            async def handle_text_message(client, message: Message):
                await self.command_handler.handle_fact_check(client, message)
            
            # Обработчик медиа сообщений с caption (фото, видео, документы с подписью)
            @self.bot.on_message((filters.photo | filters.video | filters.document) & filters.private & filters.caption)
            async def handle_media_message(client, message: Message):
                await self.command_handler.handle_fact_check(client, message)
            
            self.running = True
            logger.info("🤖 Fact-checking bot v3.0 запущен. Отправьте любое сообщение для проверки фактов!")
            
            # Ждем бесконечно
            while self.running:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            await self.stop()

    async def stop(self):
        """Остановка бота"""
        if not self.running:
            return
            
        logger.info("🔄 Останавливаем бота...")
        self.running = False
        
        try:
            await self.bot.stop()
            logger.info("✅ Бот остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке: {e}")

async def main():
    app = FactCheckingBot()
    
    # Обработка сигналов
    def signal_handler(signum, frame):
        logger.info(f"Получен сигнал {signum}, останавливаем...")
        asyncio.create_task(app.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Получен Ctrl+C, останавливаем...")
        await app.stop()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        await app.stop()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())