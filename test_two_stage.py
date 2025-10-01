#!/usr/bin/env python3
"""
Тест двухэтапной системы фактчекинга
"""

import asyncio
import logging
import sys

# Добавляем src в path
sys.path.append('src')

from two_stage_filter import TwoStageFilter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_two_stage_system():
    """Тест двухэтапной системы"""
    logger.info("🚀 Тестируем двухэтапную систему фактчекинга...")
    
    filter_system = TwoStageFilter()
    
    test_cases = [
        {
            "text": "Discord объявила о новой функции экранной демонстрации с ИИ-модерацией",
            "description": "Новость о Discord - должна найти официальные источники"
        },
        {
            "text": "Биткоин упал на 20% после заявления ФРС о повышении ставки",
            "description": "Финансовая новость - финансовые источники"
        },
        {
            "text": "СУПЕР СКИДКА! iPhone за 1000 рублей! Только сегодня! Жми ссылку!",
            "description": "Спам - должен быть отфильтрован без источников"
        },
        {
            "text": "Ученые MIT создали квантовый компьютер нового поколения",
            "description": "Научная новость - научные источники"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        logger.info(f"\n🧪 === ТЕСТ {i}: {case['description']} ===")
        logger.info(f"📝 Текст: {case['text']}")
        
        try:
            # Тестируем двухэтапную систему
            category, comment, debug_info = await filter_system.analyze_message(
                case['text'], "Test Channel"
            )
            
            logger.info(f"📊 РЕЗУЛЬТАТ:")
            logger.info(f"  📂 Категория: {category}")
            logger.info(f"  💬 Комментарий: {comment}")
            
            if debug_info:
                logger.info(f"🔧 DEBUG INFO:")
                logger.info(f"  ⏱️ Этап 1: {debug_info.stage1_time:.2f}с")
                logger.info(f"  ⏱️ Этап 2: {debug_info.stage2_time:.2f}с")
                logger.info(f"  🌐 Найдено источников: {debug_info.sources_count}")
                logger.info(f"  📋 Примеры источников: {debug_info.sources_found[:5]}")
                logger.info(f"  💭 Логика выбора: {debug_info.reasoning}")
                
                if debug_info.web_search_used:
                    logger.info(f"  🔍 Использован веб-поиск: ДА")
                if debug_info.fallback_used:
                    logger.info(f"  🔄 Использован fallback: ДА")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в тесте {i}: {e}")
        
        await asyncio.sleep(2)  # Пауза между тестами
    
    logger.info("\n✅ Тестирование двухэтапной системы завершено!")

if __name__ == "__main__":
    asyncio.run(test_two_stage_system())