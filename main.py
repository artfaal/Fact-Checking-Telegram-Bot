#!/usr/bin/env python3
"""
Fact-Checking Bot v2.0 - Двухэтапная система с отладкой
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
from debug_processor import DebugMessageProcessor
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

class FactCheckingAppV2:
    def __init__(self):
        self.bot = Client(
            "fact_checker_v2",
            api_id=Config.TELEGRAM_API_ID,
            api_hash=Config.TELEGRAM_API_HASH,
            bot_token=Config.TELEGRAM_BOT_TOKEN
        )
        self.channels = Config.get_channels()
        self.processor = DebugMessageProcessor()
        self.command_handler = CommandHandler()
        self.channel_ids = {}
        self.running = False

    async def start(self):
        """Запуск приложения v2.0"""
        try:
            Config.validate()
            logger.info("✅ Конфигурация валидна")
            
            await self.processor.start()
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
            
            # Настраиваем обработчик сообщений из каналов
            @self.bot.on_message(filters.chat(list(self.channel_ids.keys())))
            async def handle_channel_message(client, message: Message):
                channel_name = self.channel_ids.get(message.chat.id, "Unknown")
                await self.processor.process_message(message, channel_name)
            
            # Настраиваем обработчик команд /check
            @self.bot.on_message(filters.command(["check"]) & filters.private)
            async def handle_check_command(client, message: Message):
                await self.command_handler.handle_check_command(client, message)
            
            # Настраиваем обработчик команды /help
            @self.bot.on_message(filters.command(["help", "start"]) & filters.private)  
            async def handle_help_command(client, message: Message):
                await self.command_handler.handle_help_command(client, message)
            
            # Отправляем уведомление о запуске
            await self.send_startup_notification()
            
            self.running = True
            logger.info("🔄 Fact-checking bot v2.0 запущен. Нажмите Ctrl+C для остановки")
            
            # Ждем бесконечно
            while self.running:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            await self.stop()

    async def send_startup_notification(self):
        """Отправка уведомления о запуске v2.0"""
        try:
            channels_text = "\n".join([f"• {ch}" for ch in self.channels])
            
            mode_descriptions = {
                True: "🔧 **ОТЛАДОЧНЫЙ РЕЖИМ**\n• Показываются ВСЕ сообщения\n• Детальная информация о работе\n• Статистика обработки",
                False: "🎯 **ОБЫЧНЫЙ РЕЖИМ**\n• Только прошедшие фильтр\n• Краткие результаты"
            }
            
            mode_text = mode_descriptions[Config.DEBUG_MODE]
            
            await self.bot.send_message(
                chat_id=Config.TARGET_CHAT_ID,
                text=f"🤖 **Fact-checking Bot v2.0 запущен!**\n\n"
                     f"🆕 **Новая двухэтапная система:**\n"
                     f"1️⃣ Анализ контента → выбор источников\n"
                     f"2️⃣ Фактчекинг по выбранным источникам\n\n"
                     f"📡 **Мониторю каналы:**\n{channels_text}\n\n"
                     f"⚙️ **Настройки:**\n"
                     f"• Модель: {Config.GPT_MODEL}\n"
                     f"• Режим: {Config.FACT_CHECK_MODE}\n"
                     f"• Макс. источников: {Config.MAX_SOURCE_DOMAINS}\n\n"
                     f"{mode_text}\n\n"
                     f"🎯 **Ключевые улучшения:**\n"
                     f"• Умный выбор источников по контенту\n"
                     f"• Автопоиск официальных сайтов компаний\n"
                     f"• Двухэтапная проверка для точности\n"
                     f"• Подробная отладочная информация\n\n"
                     f"✅ **Готов к работе!**\n\n"
                     f"🔧 **Ручная проверка:**\n"
                     f"Отправьте мне `/check ваш текст` для анализа\n"
                     f"Используйте `/help` для справки"
            )
            logger.info("📤 Уведомление о запуске v2.0 отправлено")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")

    async def stop(self):
        """Остановка приложения"""
        if not self.running:
            return
            
        logger.info("🔄 Останавливаем приложение v2.0...")
        self.running = False
        
        try:
            await self.processor.stop()
            await self.bot.stop()
            logger.info("✅ Приложение v2.0 остановлено")
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке: {e}")

async def main():
    app = FactCheckingAppV2()
    
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