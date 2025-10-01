"""
Процессор сообщений с отладочной информацией
"""

import logging
import asyncio
from typing import Set, Optional
from pyrogram.types import Message
from two_stage_filter import TwoStageFilter, DebugInfo
from telegram_client import TelegramBot
from config import Config

logger = logging.getLogger(__name__)

class DebugMessageProcessor:
    def __init__(self):
        self.two_stage_filter = TwoStageFilter()
        self.telegram_bot = TelegramBot()
        self.processed_messages: Set[int] = set()
        
    async def start(self):
        await self.telegram_bot.start()
        logger.info("🔧 Debug процессор сообщений запущен")
        
    async def stop(self):
        await self.telegram_bot.stop()
        logger.info("🔧 Debug процессор сообщений остановлен")
        
    async def process_message(self, message: Message, channel_name: str):
        """Обрабатывает сообщение с отладочной информацией"""
        
        if message.id in self.processed_messages:
            return
            
        self.processed_messages.add(message.id)
        
        # Ограничиваем размер кэша
        if len(self.processed_messages) > 10000:
            self.processed_messages.clear()
            
        text_content = self._extract_text(message)
        
        if not text_content:
            logger.info(f"📭 Пропускаем сообщение без текста из {channel_name}")
            return
        
        logger.info(f"📨 Обрабатываем сообщение из {channel_name}: {text_content[:100]}...")
        
        try:
            # Двухэтапный анализ
            category, gpt_comment, debug_info = await self.two_stage_filter.analyze_message(
                text_content, channel_name
            )
            
            # Отправляем сообщение с отладочной информацией
            if Config.SHOW_ALL_MESSAGES:
                # В режиме отладки показываем все сообщения
                await self._send_debug_message(
                    message, channel_name, category, gpt_comment, debug_info
                )
            else:
                # Обычный режим - только не скрытые
                if category != "скрыто":
                    await self.telegram_bot.send_filtered_message(
                        original_message=message,
                        channel_name=channel_name,
                        category=category,
                        gpt_comment=gpt_comment
                    )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения из {channel_name}: {e}")
    
    async def _send_debug_message(self, message: Message, channel_name: str, 
                                category: str, gpt_comment: str, debug_info: Optional[DebugInfo]):
        """Отправляет сообщение с отладочной информацией"""
        
        try:
            # Формируем основное сообщение
            if category == "скрыто":
                status_emoji = "🗑️"
                status_text = f"**СКРЫТО** | {gpt_comment}"
            else:
                emoji_map = {"новости": "📰", "развлечения": "🎬", "другое": "📄"}
                status_emoji = emoji_map.get(category, "📄")
                status_text = f"**{category.upper()}**"
                if gpt_comment:
                    status_text += f" | 🤖 {gpt_comment}"
            
            # Формируем отладочную информацию
            debug_text = ""
            if debug_info and Config.SEND_DEBUG_INFO:
                debug_text = f"\n\n🔧 **DEBUG INFO:**\n"
                debug_text += f"⏱️ Этап 1: {debug_info.stage1_time:.2f}с | Этап 2: {debug_info.stage2_time:.2f}с\n"
                debug_text += f"🌐 Источников: {debug_info.sources_count}\n"
                
                if debug_info.sources_found:
                    sources_preview = ", ".join(debug_info.sources_found[:3])
                    if len(debug_info.sources_found) > 3:
                        sources_preview += f" и ещё {len(debug_info.sources_found)-3}"
                    debug_text += f"📋 Источники: {sources_preview}\n"
                
                if debug_info.reasoning:
                    debug_text += f"💭 Логика: {debug_info.reasoning}\n"
                
                flags = []
                if debug_info.web_search_used:
                    flags.append("🔍 веб-поиск")
                if debug_info.fallback_used:
                    flags.append("🔄 fallback")
                if flags:
                    debug_text += f"🚩 Флаги: {', '.join(flags)}"
            
            # Получаем текст сообщения
            original_text = self._extract_text(message)
            
            # Формируем итоговое сообщение
            final_text = f"📢 **{channel_name}** | {status_emoji} {status_text}\n\n"
            
            if original_text:
                # Ограничиваем длину оригинального текста
                if len(original_text) > 500:
                    original_text = original_text[:500] + "..."
                final_text += f"📝 **Сообщение:**\n{original_text}"
            
            final_text += debug_text
            
            # Отправляем с медиафайлами если есть
            if message.photo:
                await self.telegram_bot.bot.send_photo(
                    chat_id=Config.TARGET_CHAT_ID,
                    photo=message.photo.file_id,
                    caption=final_text
                )
            elif message.video:
                await self.telegram_bot.bot.send_video(
                    chat_id=Config.TARGET_CHAT_ID,
                    video=message.video.file_id,
                    caption=final_text
                )
            elif message.document:
                await self.telegram_bot.bot.send_document(
                    chat_id=Config.TARGET_CHAT_ID,
                    document=message.document.file_id,
                    caption=final_text
                )
            else:
                await self.telegram_bot.bot.send_message(
                    chat_id=Config.TARGET_CHAT_ID,
                    text=final_text
                )
            
            logger.info(f"📤 Отправлено debug сообщение из {channel_name} | {category}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки debug сообщения: {e}")
    
    def _extract_text(self, message: Message) -> str:
        """Извлекает текст из сообщения"""
        if message.text:
            return message.text
        elif message.caption:
            return message.caption
        else:
            return ""