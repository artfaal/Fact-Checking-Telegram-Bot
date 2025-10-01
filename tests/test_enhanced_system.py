#!/usr/bin/env python3
"""
Тест улучшенной системы фактчекинга
"""

import asyncio
import logging
import sys
import os

# Добавляем src в path
sys.path.append('../src')
sys.path.append('src')

from enhanced_filter import EnhancedOpenAIFilter
from sources_config import sources_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_enhanced_system():
    """Тест улучшенной системы с разными типами сообщений"""
    logger.info("🚀 Тестируем улучшенную систему фактчекинга...")
    
    filter_ai = EnhancedOpenAIFilter()
    
    test_cases = [
        {
            "text": "Discord объявила о новой функции голосовых каналов с ИИ-модерацией",
            "expected_sources": ["blog.discord.com", "discord.com", "techcrunch.com"],
            "description": "Новость о Discord - должна использовать официальные источники"
        },
        {
            "text": "Курс биткоина упал до $30,000 после заявления ФРС",
            "expected_sources": ["bloomberg.com", "reuters.com", "coindesk.com"],
            "description": "Финансовая новость - должна использовать финансовые источники"
        },
        {
            "text": "Ученые открыли новый метод лечения рака",
            "expected_sources": ["nature.com", "pubmed.ncbi.nlm.nih.gov", "who.int"],
            "description": "Научная новость - должна использовать научные источники"
        },
        {
            "text": "СПАМ! Заработай миллион за день! Кликни здесь!",
            "expected_sources": [],
            "description": "Спам - должен быть отфильтрован"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        logger.info(f"\n🧪 Тест {i}: {case['description']}")
        logger.info(f"📝 Текст: {case['text']}")
        
        # Тестируем выбор источников
        sources = sources_config.get_sources_for_topic(case['text'])
        logger.info(f"🌐 Выбрано источников: {len(sources)}")
        logger.info(f"📋 Примеры источников: {sources[:5]}")
        
        # Проверяем наличие ожидаемых источников
        if case['expected_sources']:
            found_expected = [s for s in case['expected_sources'] if s in sources]
            logger.info(f"✅ Найдены ожидаемые источники: {found_expected}")
        
        # Тестируем полный анализ
        try:
            category, comment = await filter_ai.analyze_message(case['text'], "Test Channel")
            logger.info(f"📂 Категория: {category}")
            logger.info(f"💬 Комментарий: {comment}")
        except Exception as e:
            logger.error(f"❌ Ошибка анализа: {e}")
        
        await asyncio.sleep(2)  # Пауза между тестами
    
    # Тест статистики источников
    logger.info("\n📊 Статистика источников:")
    stats = filter_ai.get_source_stats()
    for category, info in stats.items():
        logger.info(f"• {category}: {info['domains_count']} источников")
        logger.info(f"  Примеры: {', '.join(info['domains'][:3])}")
    
    logger.info("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_system())