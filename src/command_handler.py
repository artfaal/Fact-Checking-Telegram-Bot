"""
Обработчик команд для прямой проверки сообщений
"""

import logging
import asyncio
from typing import Optional
from pyrogram.types import Message
from two_stage_filter import TwoStageFilter, DebugInfo
from config import Config

logger = logging.getLogger(__name__)

class CommandHandler:
    def __init__(self):
        # Используем двухэтапную систему фактчекинга
        self.two_stage_filter = TwoStageFilter()
        
    def _extract_text_from_message(self, message: Message) -> str:
        """Извлекает текст из сообщения (text или caption)"""
        if message.text:
            return message.text.strip()
        elif message.caption:
            return message.caption.strip()
        else:
            return ""
    
    async def handle_fact_check(self, bot, message: Message):
        """Обработка любого текстового сообщения для проверки фактов"""
        
        text_to_check = self._extract_text_from_message(message)
        
        if len(text_to_check) < 10:
            # Определяем тип сообщения для более точного сообщения об ошибке
            if message.caption is not None:
                error_text = "📝 **Слишком короткая подпись к медиа**\n\n" \
                           "Добавьте подпись длиной минимум 10 символов к изображению/видео для проверки фактов.\n\n" \
                           "💡 Используйте `/help` для получения справки."
            else:
                error_text = "📝 **Слишком короткое сообщение**\n\n" \
                           "Отправьте текст длиной минимум 10 символов для проверки фактов.\n\n" \
                           "💡 Используйте `/help` для получения справки."
            
            await bot.send_message(
                chat_id=message.chat.id,
                text=error_text
            )
            return
        
        # Показываем что начали обработку
        processing_msg = await bot.send_message(
            chat_id=message.chat.id,
            text="🔄 **Проверяю факты...**\n\n"
                 f"📝 {text_to_check[:100]}{'...' if len(text_to_check) > 100 else ''}\n\n"
                 "⏳ Двухэтапная проверка в процессе..."
        )
        
        try:
            # Используем двухэтапную систему
            category, comment, debug_info = await self.two_stage_filter.analyze_message(
                text_to_check, f"Пользователь {message.from_user.username or message.from_user.first_name}"
            )
            
            # Формируем результат
            result_message = await self._format_fact_check_result(
                category, comment, debug_info
            )
            
            # Отправляем reply на оригинальное сообщение
            await bot.send_message(
                chat_id=message.chat.id,
                text=result_message,
                reply_to_message_id=message.id
            )
            
            # Удаляем сообщение "обрабатываю"
            await bot.delete_messages(
                chat_id=message.chat.id,
                message_ids=processing_msg.id
            )
            
            logger.info(f"✅ Проверен факт: {category} | {comment}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки факта: {e}")
            
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=processing_msg.id,
                text="❌ **Ошибка анализа**\n\n"
                     f"Произошла ошибка при обработке: {str(e)}\n\n"
                     "Попробуйте еще раз или отправьте другой текст."
            )

    async def handle_help_command(self, bot, message: Message):
        """Обработка команды /help"""
        
        help_text = """
🤖 **Fact-Checking Bot v3.0 - Справка**

**💬 Как использовать:**
Отправьте мне любое сообщение, и я проверю его на достоверность!

**📝 Поддерживаемые типы сообщений:**
• Текстовые сообщения
• Фото/видео с подписью
• Документы с описанием

**🎯 Пример:**
```
Discord объявил новую функцию ИИ-модерации голосовых каналов
```
Или отправьте изображение с подписью для проверки!

**📊 Что происходит при проверке:**
1️⃣ **Этап 1:** Анализ контента → выбор источников  
2️⃣ **Этап 2:** Фактчекинг по выбранным источникам

**📂 Возможные результаты:**
• ✅ **Достоверно** (90-100%) - подтверждено источниками
• ⚠️ **Частично подтверждено** (60-89%) - частично подтверждено
• ❌ **Противоречит источникам** (30-59%) - найдены противоречия
• ❓ **Не подтверждено** (0-29%) - нет доказательств
• 🗑️ **Спам** - реклама, мусор

**⚙️ Настройки бота:**
• Модель: {model}

**💡 Команды:**
• `/help` - Показать эту справку
• `/start` - Начать работу с ботом
""".format(
            model=Config.GPT_MODEL
        )
        
        await bot.send_message(
            chat_id=message.chat.id,
            text=help_text
        )
    
    async def _format_fact_check_result(self, category: str, 
                                     comment: str, debug_info: Optional[DebugInfo]) -> str:
        """Форматирует результат проверки фактов для отправки"""
        
        # Получаем confidence_score из debug_info
        confidence_score = debug_info.confidence_score if debug_info else 0
        verification_status = debug_info.verification_status if debug_info else ""
        
        # Определяем эмодзи на основе confidence_score
        confidence_emoji = self._get_confidence_emoji(confidence_score)
        
        # Для спама - упрощенный формат
        if category == "скрыто":
            return f"{confidence_emoji} Доверие: {confidence_score}%\n🤖 Комментарий: {comment}"
        
        # Для развлечений/шуток - упрощенный формат
        if category == "развлечения" and confidence_score < 50:
            if debug_info and debug_info.reasoning:
                return f"🤡 Доверие: {confidence_score}%\n🤖 Комментарий: {comment}\n💭 Логика выбора: {debug_info.reasoning}"
            else:
                return f"🤡 Доверие: {confidence_score}%\n🤖 Комментарий: {comment}"
        
        # Основной формат для фактчекинга
        result = f"{confidence_emoji} Доверие: {confidence_score}%\n"
        result += f"🤖 Комментарий: {comment}\n"
        
        # Добавляем детальные выводы отдельным полем
        if debug_info and debug_info.detailed_findings and debug_info.detailed_findings.strip():
            result += f"\n📋 Детальные выводы: {debug_info.detailed_findings}\n"
        
        # Добавляем противоречия отдельным полем
        if debug_info and debug_info.contradictions and debug_info.contradictions.strip():
            result += f"\n⚠️ Противоречия: {debug_info.contradictions}\n"
        
        # Добавляем отсутствующие доказательства отдельным полем
        if debug_info and debug_info.missing_evidence and debug_info.missing_evidence.strip():
            result += f"\n❓ Отсутствующие доказательства: {debug_info.missing_evidence}\n"
        
        # Добавляем источники (полный список без сокращений)
        if debug_info and debug_info.sources_found:
            sources_text = ", ".join(debug_info.sources_found)
            result += f"\n🌐 Источники: {sources_text}\n"
        
        # Добавляем логику выбора
        if debug_info and debug_info.reasoning:
            result += f"\n💭 Логика выбора: {debug_info.reasoning}"
        
        return result
    
    def _get_confidence_emoji(self, confidence_score: int) -> str:
        """Возвращает подходящий эмодзи на основе confidence_score"""
        if confidence_score >= 90:
            return "✅"  # Достоверно
        elif confidence_score >= 60:
            return "⚠️"  # Частично подтверждено
        elif confidence_score >= 30:
            return "❌"  # Противоречит источникам
        else:
            return "❓"  # Не подтверждено
