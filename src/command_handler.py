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
        
    async def handle_check_command(self, bot, message: Message):
        """Обработка команды /check"""
        
        # Извлекаем текст после команды
        text_to_check = self._extract_check_text(message.text)
        
        if not text_to_check:
            await bot.send_message(
                chat_id=message.chat.id,
                text="❓ **Как использовать:**\n\n"
                     "`/check ваш текст для проверки`\n\n"
                     "**Пример:**\n"
                     "`/check Discord объявил новую функцию ИИ-модерации`\n\n"
                     "🤖 Я проанализирую текст точно так же, как новость из канала!"
            )
            return
        
        # Показываем что начали обработку
        processing_msg = await bot.send_message(
            chat_id=message.chat.id,
            text="🔄 **Анализирую ваше сообщение...**\n\n"
                 f"📝 Текст: {text_to_check[:100]}{'...' if len(text_to_check) > 100 else ''}\n\n"
                 "⏳ Двухэтапная проверка в процессе..."
        )
        
        try:
            # Используем двухэтапную систему
            category, comment, debug_info = await self.two_stage_filter.analyze_message(
                text_to_check, "Ручная проверка"
            )
            
            # Формируем результат
            result_message = await self._format_check_result(
                text_to_check, category, comment, debug_info
            )
            
            # Обновляем сообщение с результатом
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=processing_msg.id,
                text=result_message
            )
            
            logger.info(f"✅ Обработана команда /check: {category} | {comment}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки команды /check: {e}")
            
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=processing_msg.id,
                text="❌ **Ошибка анализа**\n\n"
                     f"Произошла ошибка при обработке: {str(e)}\n\n"
                     "Попробуйте еще раз или обратитесь к администратору."
            )
    
    async def handle_fact_check(self, bot, message: Message):
        """Обработка любого текстового сообщения для проверки фактов"""
        
        text_to_check = message.text.strip()
        
        if len(text_to_check) < 10:
            await bot.send_message(
                chat_id=message.chat.id,
                text="📝 **Слишком короткое сообщение**\n\n"
                     "Отправьте текст длиной минимум 10 символов для проверки фактов.\n\n"
                     "💡 Используйте `/help` для получения справки."
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
                text_to_check, category, comment, debug_info
            )
            
            # Обновляем сообщение с результатом
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=processing_msg.id,
                text=result_message
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
Просто отправьте мне любое текстовое сообщение, и я проверю его на достоверность!

**🎯 Пример:**
```
Discord объявил новую функцию ИИ-модерации голосовых каналов
```

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
• Отладка: {debug}

**💡 Команды:**
• `/help` - Показать эту справку
• `/start` - Начать работу с ботом
""".format(
            model=Config.GPT_MODEL,
            debug="включена" if Config.DEBUG_MODE else "выключена"
        )
        
        await bot.send_message(
            chat_id=message.chat.id,
            text=help_text
        )
    
    def _extract_check_text(self, command_text: str) -> Optional[str]:
        """Извлекает текст для проверки из команды"""
        if not command_text:
            return None
            
        # Убираем команду /check и лишние пробелы
        text = command_text.replace('/check', '', 1).strip()
        
        # Проверяем что что-то осталось
        if len(text) < 5:
            return None
            
        return text
    
    async def _format_check_result(self, original_text: str, category: str, 
                                 comment: str, debug_info: Optional[DebugInfo]) -> str:
        """Форматирует результат проверки для отправки"""
        
        # Определяем эмодзи и статус
        if category == "скрыто":
            status_emoji = "🗑️"
            status_text = f"**СКРЫТО**"
            result_text = comment
        else:
            emoji_map = {"новости": "📰", "развлечения": "🎬", "другое": "📄"}
            status_emoji = emoji_map.get(category, "📄")
            status_text = f"**{category.upper()}**"
            result_text = comment if comment else "Информация обработана"
        
        # Основной результат
        result = f"✅ **Анализ завершен**\n\n"
        result += f"📝 **Ваше сообщение:**\n{original_text}\n\n"
        result += f"{status_emoji} **Результат:** {status_text}\n"
        
        if result_text:
            result += f"🤖 **Комментарий:** {result_text}\n"
        
        # Добавляем отладочную информацию если включена
        if debug_info and Config.SEND_DEBUG_INFO:
            result += f"\n🔧 **DEBUG INFO:**\n"
            result += f"⏱️ **Время выполнения:**\n"
            result += f"• Этап 1 (выбор источников): {debug_info.stage1_time:.2f}с\n"
            result += f"• Этап 2 (фактчекинг): {debug_info.stage2_time:.2f}с\n"
            result += f"• Общее время: {debug_info.stage1_time + debug_info.stage2_time:.2f}с\n\n"

            if debug_info.stage2_attempts:
                result += f"🔁 **Попыток этапа 2:** {debug_info.stage2_attempts}\n"

            result += f"🌐 **Источники:** {debug_info.sources_count} доменов\n"
            
            if debug_info.sources_found:
                sources_preview = debug_info.sources_found[:5]
                sources_text = ", ".join(sources_preview)
                if len(debug_info.sources_found) > 5:
                    sources_text += f" и ещё {len(debug_info.sources_found)-5}"
                result += f"📋 **Проверено:** {sources_text}\n"
            
            if debug_info.reasoning:
                result += f"💭 **Логика выбора:** {debug_info.reasoning}\n"
            
            # Флаги работы
            flags = []
            if debug_info.web_search_used:
                flags.append("🔍 веб-поиск")
            if debug_info.fallback_used:
                flags.append("🔄 резервный режим")
            
            if flags:
                result += f"🚩 **Использовано:** {', '.join(flags)}\n"
        
        result += f"\n💡 **Подсказка:** Отправьте любое сообщение для проверки фактов"
        
        return result
    
    async def _format_fact_check_result(self, original_text: str, category: str, 
                                     comment: str, debug_info: Optional[DebugInfo]) -> str:
        """Форматирует результат проверки фактов для отправки"""
        
        # Определяем эмодзи и статус
        if category == "скрыто":
            status_emoji = "🗑️"
            status_text = f"**СПАМ**"
            result_text = comment
        else:
            emoji_map = {"новости": "📰", "развлечения": "🎬", "другое": "📄"}
            status_emoji = emoji_map.get(category, "📄")
            status_text = f"**{category.upper()}**"
            result_text = comment if comment else "Информация обработана"
        
        # Основной результат
        result = f"✅ **Проверка фактов завершена**\n\n"
        result += f"📝 **Ваше сообщение:**\n{original_text}\n\n"
        result += f"{status_emoji} **Категория:** {status_text}\n"
        
        if result_text:
            result += f"🤖 **Результат:** {result_text}\n"
        
        # Добавляем отладочную информацию если включена
        if debug_info and Config.SEND_DEBUG_INFO:
            result += f"\n🔧 **DEBUG INFO:**\n"
            result += f"⏱️ **Время выполнения:**\n"
            result += f"• Этап 1 (выбор источников): {debug_info.stage1_time:.2f}с\n"
            result += f"• Этап 2 (фактчекинг): {debug_info.stage2_time:.2f}с\n"
            result += f"• Общее время: {debug_info.stage1_time + debug_info.stage2_time:.2f}с\n\n"

            if debug_info.stage2_attempts:
                result += f"🔁 **Попыток этапа 2:** {debug_info.stage2_attempts}\n"

            result += f"🌐 **Источники:** {debug_info.sources_count} доменов\n"
            
            if debug_info.sources_found:
                sources_preview = debug_info.sources_found[:5]
                sources_text = ", ".join(sources_preview)
                if len(debug_info.sources_found) > 5:
                    sources_text += f" и ещё {len(debug_info.sources_found)-5}"
                result += f"📋 **Проверено:** {sources_text}\n"
            
            if debug_info.reasoning:
                result += f"💭 **Логика выбора:** {debug_info.reasoning}\n"
            
            # Флаги работы
            flags = []
            if debug_info.web_search_used:
                flags.append("🔍 веб-поиск")
            if debug_info.fallback_used:
                flags.append("🔄 резервный режим")
            
            if flags:
                result += f"🚩 **Использовано:** {', '.join(flags)}\n"
        
        result += f"\n💡 **Отправьте любое сообщение для новой проверки**"
        
        return result
