#!/usr/bin/env python3
"""
Упрощенный мониторинг через бот
"""

import asyncio
import logging
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

class BotMonitor:
    def __init__(self):
        # Используем тот же бот для мониторинга и отправки
        self.app = Client(
            "fact_checker_bot_monitor",
            api_id=Config.TELEGRAM_API_ID,
            api_hash=Config.TELEGRAM_API_HASH,
            bot_token=Config.TELEGRAM_BOT_TOKEN
        )
        self.channels = Config.get_channels()
        self.message_processor = MessageProcessor()
        self.running = False

    async def start(self):
        """Запуск мониторинга"""
        try:
            Config.validate()
            logger.info("Конфигурация валидна")
            
            await self.message_processor.start()
            await self.app.start()
            
            logger.info("✅ Fact-checking бот запущен")
            logger.info(f"📡 Мониторим каналы: {', '.join(self.channels)}")
            logger.info(f"📤 Отправляем в чат: {Config.TARGET_CHAT_ID}")
            
            # Проверим доступ к каналам
            for channel in self.channels:
                try:
                    chat = await self.app.get_chat(channel)
                    logger.info(f"✅ Подключен к каналу: {channel} (ID: {chat.id})")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось подключиться к каналу {channel}: {e}")
            
            self.running = True
            
            # Для демонстрации - отправим тестовое сообщение
            await self.send_test_message()
            
            logger.info("🔄 Мониторинг запущен. Нажмите Ctrl+C для остановки")
            
            # Ждем бесконечно, пока не прервут
            try:
                while self.running:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info("Получен сигнал остановки")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            await self.stop()
            
    async def send_test_message(self):
        """Отправка тестового сообщения о запуске"""
        try:
            await self.app.send_message(
                chat_id=Config.TARGET_CHAT_ID,
                text="🤖 **Fact-checking бот запущен!**\n\n"
                     f"📡 Мониторю каналы: {', '.join(self.channels)}\n"
                     f"🔍 Фактчекинг через GPT-5 с веб-поиском\n"
                     f"✅ Готов к работе!"
            )
            logger.info("📤 Уведомление о запуске отправлено")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")

    async def stop(self):
        """Остановка мониторинга"""
        if not self.running:
            return
            
        logger.info("🔄 Останавливаем мониторинг...")
        
        try:
            await self.message_processor.stop()
            await self.app.stop()
            
            self.running = False
            logger.info("✅ Мониторинг остановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке: {e}")

async def main():
    monitor = BotMonitor()
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Получен Ctrl+C, останавливаем...")
        await monitor.stop()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        await monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())