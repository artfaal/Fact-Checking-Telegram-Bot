import asyncio
import logging
from typing import List, Callable, Dict, Any
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config

logger = logging.getLogger(__name__)

class TelegramMonitor:
    def __init__(self, message_handler: Callable[[Message, str], None]):
        self.app = Client(
            "fact_checker_monitor",
            api_id=Config.TELEGRAM_API_ID,
            api_hash=Config.TELEGRAM_API_HASH
        )
        self.channels = Config.get_channels()
        self.message_handler = message_handler
        self.channel_ids = {}
        
    async def start(self):
        await self.app.start()
        logger.info("Telegram клиент запущен")
        
        for channel in self.channels:
            try:
                chat = await self.app.get_chat(channel)
                self.channel_ids[chat.id] = channel
                logger.info(f"Подключен к каналу: {channel} (ID: {chat.id})")
            except Exception as e:
                logger.error(f"Ошибка подключения к каналу {channel}: {e}")
        
        if not self.channel_ids:
            raise ValueError("Не удалось подключиться ни к одному каналу")
        
        self._setup_handlers()
        
    def _setup_handlers(self):
        @self.app.on_message(filters.chat(list(self.channel_ids.keys())))
        async def handle_channel_message(client, message: Message):
            channel_name = self.channel_ids.get(message.chat.id, "Unknown")
            try:
                await self.message_handler(message, channel_name)
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения из {channel_name}: {e}")
    
    async def stop(self):
        await self.app.stop()
        logger.info("Telegram клиент остановлен")
    
    async def run_until_idle(self):
        await self.app.idle()

class TelegramBot:
    def __init__(self):
        self.bot = Client(
            "fact_checker_bot",
            api_id=Config.TELEGRAM_API_ID,
            api_hash=Config.TELEGRAM_API_HASH,
            bot_token=Config.TELEGRAM_BOT_TOKEN
        )
        self.target_chat_id = Config.TARGET_CHAT_ID
        
    async def start(self):
        await self.bot.start()
        logger.info("Telegram бот запущен")
        
    async def stop(self):
        await self.bot.stop()
        logger.info("Telegram бот остановлен")
        
    async def send_filtered_message(self, 
                                   original_message: Message, 
                                   channel_name: str,
                                   category: str,
                                   gpt_comment: str = None):
        try:
            text_parts = []
            
            if category != "скрыто":
                text_parts.append(f"📢 **{channel_name}** | 📂 {category}")
                
                if gpt_comment:
                    text_parts.append(f"🤖 *{gpt_comment}*")
                    
                if original_message.text:
                    text_parts.append(original_message.text)
                elif original_message.caption:
                    text_parts.append(original_message.caption)
                    
                message_text = "\n\n".join(text_parts)
                
                if original_message.photo:
                    await self.bot.send_photo(
                        chat_id=self.target_chat_id,
                        photo=original_message.photo.file_id,
                        caption=message_text
                    )
                elif original_message.video:
                    await self.bot.send_video(
                        chat_id=self.target_chat_id,
                        video=original_message.video.file_id,
                        caption=message_text
                    )
                elif original_message.document:
                    await self.bot.send_document(
                        chat_id=self.target_chat_id,
                        document=original_message.document.file_id,
                        caption=message_text
                    )
                else:
                    await self.bot.send_message(
                        chat_id=self.target_chat_id,
                        text=message_text
                    )
                    
                logger.info(f"Отправлено сообщение из {channel_name} в категории {category}")
            else:
                logger.info(f"Сообщение из {channel_name} скрыто как мусор")
                
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")