#!/usr/bin/env python3
"""
Демонстрация улучшенной системы фактчекинга
"""

import asyncio
import logging
import sys
from pyrogram import Client

# Добавляем src в path
sys.path.append('src')

from config import Config
from enhanced_filter import EnhancedOpenAIFilter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_enhanced():
    """Демонстрация новых возможностей"""
    logger.info("🚀 Демонстрация Enhanced Fact-Checking бота")
    
    # Создаем бота и фильтр
    bot = Client(
        "demo_enhanced",
        api_id=Config.TELEGRAM_API_ID,
        api_hash=Config.TELEGRAM_API_HASH,
        bot_token=Config.TELEGRAM_BOT_TOKEN
    )
    
    ai_filter = EnhancedOpenAIFilter()
    
    try:
        await bot.start()
        logger.info("✅ Бот запущен")
        
        # Демонстрационные сообщения с разными темами
        demo_cases = [
            {
                "text": "Discord добавил новую функцию экранного демонстрации с ИИ-фильтрацией контента",
                "type": "🎮 ТЕХНОЛОГИИ",
                "description": "Должен найти официальные источники Discord"
            },
            {
                "text": "Курс биткоина обвалился на 15% после заявления регулятора",
                "type": "💰 ФИНАНСЫ", 
                "description": "Должен использовать финансовые источники"
            },
            {
                "text": "Ученые MIT разработали новый квантовый процессор",
                "type": "🔬 НАУКА",
                "description": "Должен проверить в научных источниках"
            },
            {
                "text": "МЕГА СКИДКА! Купи iPhone за 1000 рублей! Только сегодня!",
                "type": "🗑️ СПАМ",
                "description": "Должен определить как мусор"
            }
        ]
        
        await bot.send_message(
            chat_id=Config.TARGET_CHAT_ID,
            text="🤖 **Демонстрация Enhanced Fact-Checking**\n\n"
                 "Тестирую умный выбор источников для разных типов новостей...\n\n"
                 "🎯 **Новые возможности:**\n"
                 "• Автоматический выбор официальных сайтов\n"
                 "• Тематические источники по ключевым словам\n"
                 "• Настраиваемые режимы проверки\n"
                 "• Расширенная база источников"
        )
        
        for i, case in enumerate(demo_cases, 1):
            logger.info(f"📝 Тестируем: {case['text'][:50]}...")
            
            # Получаем источники для этой темы
            sources = ai_filter.sources.get_sources_for_topic(case['text'])
            
            # Анализируем сообщение
            category, comment = await ai_filter.analyze_message(case['text'], "Demo")
            
            # Формируем результат
            sources_preview = ", ".join(sources[:5]) + (f" и ещё {len(sources)-5}" if len(sources) > 5 else "")
            
            if category == "скрыто":
                result_emoji = "🗑️"
                result_text = f"**СКРЫТО** | {comment}"
            else:
                result_emoji = {"новости": "📰", "развлечения": "🎬", "другое": "📄"}.get(category, "📄")
                result_text = f"**{category.upper()}**"
                if comment:
                    result_text += f" | 🤖 {comment}"
            
            # Отправляем результат
            message_text = f"**Тест {i}/4: {case['type']}**\n\n" \
                          f"📨 **Сообщение:**\n{case['text']}\n\n" \
                          f"🎯 **Ожидание:** {case['description']}\n\n" \
                          f"🌐 **Источники ({len(sources)}):**\n{sources_preview}\n\n" \
                          f"🤖 **Результат:** {result_emoji} {result_text}"
            
            await bot.send_message(
                chat_id=Config.TARGET_CHAT_ID,
                text=message_text
            )
            
            logger.info(f"✅ Тест {i}: {len(sources)} источников, результат: {category}")
            await asyncio.sleep(3)
        
        # Показываем статистику источников
        stats = ai_filter.get_source_stats()
        stats_text = "\n".join([
            f"• **{cat}**: {info['domains_count']} источников"
            for cat, info in stats.items()
        ])
        
        await bot.send_message(
            chat_id=Config.TARGET_CHAT_ID,
            text="📊 **Статистика источников:**\n\n"
                 f"{stats_text}\n\n"
                 f"🎉 **Демонстрация завершена!**\n\n"
                 f"💡 **Преимущества:**\n"
                 f"• Умнее определяет официальные источники\n"
                 f"• Лучше фильтрует спам и фейки\n"
                 f"• Адаптируется к разным темам\n"
                 f"• Настраивается под ваши нужды"
        )
        
        await bot.stop()
        logger.info("✅ Демонстрация завершена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка демонстрации: {e}")

if __name__ == "__main__":
    asyncio.run(demo_enhanced())