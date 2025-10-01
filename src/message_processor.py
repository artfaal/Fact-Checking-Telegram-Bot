import logging
import asyncio
from typing import Set
from pyrogram.types import Message
from openai_filter import OpenAIFilter
from telegram_client import TelegramBot

logger = logging.getLogger(__name__)

class MessageProcessor:
    def __init__(self):
        self.openai_filter = OpenAIFilter()
        self.telegram_bot = TelegramBot()
        self.processed_messages: Set[int] = set()
        
    async def start(self):
        await self.telegram_bot.start()
        logger.info("Процессор сообщений запущен")
        
    async def stop(self):
        await self.telegram_bot.stop()
        logger.info("Процессор сообщений остановлен")
        
    async def process_message(self, message: Message, channel_name: str):
        """Обрабатывает сообщение из канала"""
        
        if message.id in self.processed_messages:
            return
            
        self.processed_messages.add(message.id)
        
        if len(self.processed_messages) > 10000:
            self.processed_messages.clear()
            
        text_content = self._extract_text(message)
        
        if not text_content:
            logger.info(f"Пропускаем сообщение без текста из {channel_name}")
            return
            
        logger.info(f"Обрабатываем сообщение из {channel_name}: {text_content[:100]}...")
        
        try:
            category, gpt_comment = await self.openai_filter.analyze_message(
                text_content, channel_name
            )
            
            await self.telegram_bot.send_filtered_message(
                original_message=message,
                channel_name=channel_name,
                category=category,
                gpt_comment=gpt_comment
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения из {channel_name}: {e}")
            
    def _extract_text(self, message: Message) -> str:
        """Извлекает текст из сообщения"""
        if message.text:
            return message.text
        elif message.caption:
            return message.caption
        else:
            return ""
            
    def _clean_text(self, text: str) -> str:
        """Базовая очистка текста"""
        if not text:
            return ""
            
        text = text.strip()
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('—') and len(line) > 3:
                cleaned_lines.append(line)
                
        return '\n'.join(cleaned_lines)