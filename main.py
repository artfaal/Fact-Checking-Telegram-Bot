#!/usr/bin/env python3
"""
Telegram Fact-Checking Bot
Мониторит каналы, фильтрует мусор через OpenAI и отправляет отфильтрованные сообщения
"""

import asyncio
import logging
import signal
import sys
from config import Config
from telegram_client import TelegramMonitor
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

class FactCheckingApp:
    def __init__(self):
        self.message_processor = MessageProcessor()
        self.telegram_monitor = None
        self.running = False
        
    async def start(self):
        """Запуск приложения"""
        try:
            Config.validate()
            logger.info("Конфигурация валидна")
            
            await self.message_processor.start()
            
            self.telegram_monitor = TelegramMonitor(
                message_handler=self.message_processor.process_message
            )
            
            await self.telegram_monitor.start()
            
            self.running = True
            logger.info("✅ Fact-checking бот запущен")
            logger.info(f"📡 Мониторим каналы: {', '.join(Config.get_channels())}")
            logger.info(f"📤 Отправляем в чат: {Config.TARGET_CHAT_ID}")
            
            await self.telegram_monitor.run_until_idle()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            await self.stop()
            
    async def stop(self):
        """Остановка приложения"""
        if not self.running:
            return
            
        logger.info("🔄 Останавливаем приложение...")
        
        try:
            if self.telegram_monitor:
                await self.telegram_monitor.stop()
                
            await self.message_processor.stop()
            
            self.running = False
            logger.info("✅ Приложение остановлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке: {e}")

async def main():
    app = FactCheckingApp()
    
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