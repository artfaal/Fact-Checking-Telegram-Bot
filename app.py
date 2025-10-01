#!/usr/bin/env python3
"""
Fact-Checking Telegram Bot - Главное приложение
"""

import asyncio
import logging
import signal
import sys
from pyrogram import Client, filters
from pyrogram.types import Message

# Импорты из src
sys.path.append('src')
from config import Config
from enhanced_filter import EnhancedOpenAIFilter
from telegram_client import TelegramBot

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
        self.bot = Client(
            "fact_checker_app",
            api_id=Config.TELEGRAM_API_ID,
            api_hash=Config.TELEGRAM_API_HASH,
            bot_token=Config.TELEGRAM_BOT_TOKEN
        )
        self.channels = Config.get_channels()
        self.ai_filter = EnhancedOpenAIFilter()
        self.telegram_bot = TelegramBot()
        self.channel_ids = {}
        self.running = False
        self.processed_messages = set()

    async def start(self):
        """Запуск приложения"""
        try:
            Config.validate()
            logger.info("✅ Конфигурация валидна")
            
            await self.telegram_bot.start()
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
                await self.process_message(message)
            
            # Отправляем уведомление о запуске
            await self.send_startup_notification()
            
            self.running = True
            logger.info("🔄 Fact-checking бот запущен. Нажмите Ctrl+C для остановки")
            
            # Ждем бесконечно
            while self.running:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            await self.stop()

    async def process_message(self, message: Message):
        """Обработка сообщения из канала"""
        
        if message.id in self.processed_messages:
            return
            
        self.processed_messages.add(message.id)
        
        # Ограничиваем размер кэша
        if len(self.processed_messages) > 10000:
            self.processed_messages.clear()
        
        channel_name = self.channel_ids.get(message.chat.id, "Unknown")
        text_content = self._extract_text(message)
        
        if not text_content:
            logger.info(f"📭 Пропускаем сообщение без текста из {channel_name}")
            return
            
        logger.info(f"📨 Обрабатываем сообщение из {channel_name}: {text_content[:100]}...")
        
        try:
            # Анализируем через улучшенный фильтр
            category, gpt_comment = await self.ai_filter.analyze_message(
                text_content, channel_name
            )
            
            # Отправляем результат
            await self.telegram_bot.send_filtered_message(
                original_message=message,
                channel_name=channel_name,
                category=category,
                gpt_comment=gpt_comment
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения из {channel_name}: {e}")
    
    def _extract_text(self, message: Message) -> str:
        """Извлекает текст из сообщения"""
        if message.text:
            return message.text
        elif message.caption:
            return message.caption
        else:
            return ""

    async def send_startup_notification(self):
        """Отправка расширенного уведомления о запуске"""
        try:
            channels_text = "\n".join([f"• {ch}" for ch in self.channels])
            
            # Получаем статистику источников
            source_stats = self.ai_filter.get_source_stats()
            stats_text = "\n".join([
                f"• **{cat}**: {info['domains_count']} источников"
                for cat, info in source_stats.items()
            ])
            
            await self.bot.send_message(
                chat_id=Config.TARGET_CHAT_ID,
                text=f"🤖 **Enhanced Fact-checking бот запущен!**\n\n"
                     f"📡 **Мониторю каналы:**\n{channels_text}\n\n"
                     f"🔍 **Фактчекинг:** {Config.GPT_MODEL} с умным веб-поиском\n"
                     f"⚙️ **Режим:** {Config.FACT_CHECK_MODE}\n"
                     f"📂 **Категории:** новости, развлечения, другое\n\n"
                     f"🌐 **Источники:**\n{stats_text}\n\n"
                     f"🎯 **Новые возможности:**\n"
                     f"• Умный выбор источников по теме\n"
                     f"• Автоопределение официальных сайтов\n"
                     f"• Настраиваемые режимы проверки\n"
                     f"• Расширенная фильтрация спама\n\n"
                     f"✅ **Готов к работе!**"
            )
            logger.info("📤 Расширенное уведомление о запуске отправлено")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")

    async def stop(self):
        """Остановка приложения"""
        if not self.running:
            return
            
        logger.info("🔄 Останавливаем приложение...")
        self.running = False
        
        try:
            await self.telegram_bot.stop()
            await self.bot.stop()
            logger.info("✅ Приложение остановлено")
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке: {e}")

async def main():
    app = FactCheckingApp()
    
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