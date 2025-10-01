#!/usr/bin/env python3
"""
Демонстрация работы фактчекера
"""

import asyncio
import logging
from pyrogram import Client
from test_filter_standalone import TestOpenAIFilter
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo():
    """Демонстрация полной работы системы"""
    logger.info("🚀 Демонстрация fact-checking бота")
    
    # Создаем бота для отправки
    bot = Client(
        "demo_bot",
        api_id=Config.TELEGRAM_API_ID,
        api_hash=Config.TELEGRAM_API_HASH,
        bot_token=Config.TELEGRAM_BOT_TOKEN
    )
    
    # Создаем фильтр
    ai_filter = TestOpenAIFilter()
    
    try:
        await bot.start()
        logger.info("✅ Бот запущен")
        
        # Тестовые сообщения для демонстрации
        demo_messages = [
            "🗑️ СПАМ: Купи дешевые товары прямо сейчас! Скидка 90%! Только сегодня!",
            "📰 НОВОСТИ: Президент России подписал новый закон об образовании",
            "🎬 РАЗВЛЕЧЕНИЯ: Новый фильм Marvel побил все рекорды в прокате",
            "🌍 НОВОСТИ: Курс доллара сегодня упал до 50 рублей за доллар"
        ]
        
        await bot.send_message(
            chat_id=Config.TARGET_CHAT_ID,
            text="🤖 **Демонстрация Fact-Checking бота**\n\n"
                 "Сейчас проанализирую несколько сообщений с помощью GPT-5 и веб-поиска..."
        )
        
        for i, message in enumerate(demo_messages, 1):
            logger.info(f"📝 Анализирую сообщение {i}: {message[:50]}...")
            
            # Анализируем через AI
            category, comment = await ai_filter.analyze_message(message, "Демо канал")
            
            # Формируем результат
            if category == "скрыто":
                result_text = f"🗑️ **СКРЫТО** | {comment}"
                emoji = "🗑️"
            else:
                emoji = {"новости": "📰", "развлечения": "🎬", "другое": "📄"}.get(category, "📄")
                result_text = f"{emoji} **{category.upper()}**"
                if comment:
                    result_text += f" | 🤖 {comment}"
            
            # Отправляем результат
            final_message = f"**Тест {i}/4**\n\n" \
                          f"📨 Сообщение:\n{message}\n\n" \
                          f"🤖 Анализ GPT-5:\n{result_text}"
            
            await bot.send_message(
                chat_id=Config.TARGET_CHAT_ID,
                text=final_message
            )
            
            logger.info(f"✅ Результат {i}: {category} | {comment}")
            await asyncio.sleep(3)  # Пауза между сообщениями
        
        # Финальное сообщение
        await bot.send_message(
            chat_id=Config.TARGET_CHAT_ID,
            text="✅ **Демонстрация завершена!**\n\n"
                 "🔥 **Возможности бота:**\n"
                 "• GPT-5 с веб-поиском для фактчекинга\n"
                 "• Фильтрация спама и мусора\n"
                 "• Категоризация по темам\n"
                 "• Проверка достоверности фактов\n"
                 "• Сохранение медиафайлов\n\n"
                 "🚀 Готов к мониторингу реальных каналов!"
        )
        
        await bot.stop()
        logger.info("✅ Демонстрация завершена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка демонстрации: {e}")

if __name__ == "__main__":
    asyncio.run(demo())