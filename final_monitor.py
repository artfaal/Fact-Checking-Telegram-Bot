#!/usr/bin/env python3
"""
Финальная версия мониторинга с обработкой сообщений
"""

import asyncio
import logging
import signal
import sys
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from message_processor import MessageProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fact_checker.log'),
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
        self.channels = Config.get_channels()
        self.message_processor = MessageProcessor()
        self.channel_ids = {}
        self.running = False

    async def start(self):
        """Запуск бота"""
        try:
            Config.validate()
            logger.info("Конфигурация валидна")
            
            await self.message_processor.start()
            await self.bot.start()
            
            # Получаем ID каналов
            for channel in self.channels:
                try:
                    chat = await self.bot.get_chat(channel)
                    self.channel_ids[chat.id] = channel
                    logger.info(f"✅ Подключен к каналу: {channel} (ID: {chat.id})")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось подключиться к каналу {channel}: {e}")
            
            if not self.channel_ids:
                raise ValueError("Не удалось подключиться ни к одному каналу")
            
            # Настраиваем обработчик сообщений
            @self.bot.on_message(filters.chat(list(self.channel_ids.keys())))
            async def handle_message(client, message: Message):
                channel_name = self.channel_ids.get(message.chat.id, "Unknown")
                logger.info(f"📨 Новое сообщение из {channel_name}: {message.text[:100] if message.text else 'медиа'}...")
                
                try:
                    await self.message_processor.process_message(message, channel_name)
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки сообщения из {channel_name}: {e}")
            
            # Отправляем уведомление о запуске
            await self.send_startup_notification()
            
            self.running = True
            logger.info("🔄 Мониторинг запущен. Нажмите Ctrl+C для остановки")
            
            # Ждем бесконечно
            while self.running:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            await self.stop()

    async def send_startup_notification(self):
        """Отправка уведомления о запуске"""
        try:
            channels_text = "\n".join([f"• {ch}" for ch in self.channels])
            await self.bot.send_message(
                chat_id=Config.TARGET_CHAT_ID,
                text=f"🤖 **Fact-checking бот запущен!**\n\n"
                     f"📡 **Мониторю каналы:**\n{channels_text}\n\n"
                     f"🔍 **Фактчекинг:** GPT-5 с веб-поиском\n"
                     f"📂 **Категории:** новости, развлечения, другое\n"
                     f"🗑️ **Фильтрация:** спам, мусор, недостоверные факты\n\n"
                     f"✅ **Готов к работе!**"
            )
            logger.info("📤 Уведомление о запуске отправлено")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")

    async def stop(self):
        """Остановка бота"""
        if not self.running:
            return
            
        logger.info("🔄 Останавливаем бот...")
        self.running = False
        
        try:
            await self.message_processor.stop()
            await self.bot.stop()
            logger.info("✅ Бот остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке: {e}")

async def main():
    bot = FactCheckingBot()
    
    # Обработка сигналов
    def signal_handler(signum, frame):
        logger.info(f"Получен сигнал {signum}, останавливаем...")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Получен Ctrl+C, останавливаем...")
        await bot.stop()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        await bot.stop()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())