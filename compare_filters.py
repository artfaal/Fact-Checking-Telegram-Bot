#!/usr/bin/env python3
"""
Сравнение двухэтапной и простой системы
"""

import asyncio
import logging
import sys
import time

# Добавляем src в path
sys.path.append('src')

from two_stage_filter import TwoStageFilter
from simple_filter import SimpleFilter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def compare_systems():
    """Сравнение двух систем фактчекинга"""
    logger.info("🔥 Сравнение систем фактчекинга")
    
    # Инициализируем системы
    two_stage = TwoStageFilter()
    simple = SimpleFilter()
    
    test_cases = [
        "Discord добавил функцию ИИ-модерации голосовых каналов",
        "СУПЕР СКИДКА! iPhone за 999 рублей! Только сегодня!",
        "Курс доллара вырос на 5% после заявления ЦБ",
        "Вышел новый фильм Marvel с рекордными сборами"
    ]
    
    for i, text in enumerate(test_cases, 1):
        logger.info(f"\n🧪 === ТЕСТ {i}: {text[:50]}... ===")
        
        # Тестируем двухэтапную систему
        logger.info("🔹 ДВУХЭТАПНАЯ СИСТЕМА:")
        start_time = time.time()
        try:
            category1, comment1, debug1 = await two_stage.analyze_message(text, "Test")
            time1 = time.time() - start_time
            logger.info(f"  📂 Результат: {category1} | {comment1}")
            logger.info(f"  ⏱️ Время: {time1:.2f}с")
            if debug1:
                logger.info(f"  🌐 Источников: {debug1.sources_count}")
        except Exception as e:
            logger.error(f"  ❌ Ошибка: {e}")
            category1, comment1, time1 = "ошибка", str(e), 0
        
        # Тестируем простую систему
        logger.info("🔸 ПРОСТАЯ СИСТЕМА:")
        start_time = time.time()
        try:
            category2, comment2 = await simple.analyze_message(text, "Test")
            time2 = time.time() - start_time
            logger.info(f"  📂 Результат: {category2} | {comment2}")
            logger.info(f"  ⏱️ Время: {time2:.2f}с")
        except Exception as e:
            logger.error(f"  ❌ Ошибка: {e}")
            category2, comment2, time2 = "ошибка", str(e), 0
        
        # Сравнение
        logger.info("📊 СРАВНЕНИЕ:")
        if category1 == category2:
            logger.info("  ✅ Категории совпадают")
        else:
            logger.info(f"  ⚠️ Категории разные: {category1} vs {category2}")
        
        if time1 > 0 and time2 > 0:
            if time1 < time2:
                logger.info(f"  🏃 Двухэтапная быстрее на {time2-time1:.2f}с")
            elif time2 < time1:
                logger.info(f"  🏃 Простая быстрее на {time1-time2:.2f}с")
            else:
                logger.info("  ⚖️ Время примерно одинаково")
        
        await asyncio.sleep(3)  # Пауза между тестами
    
    logger.info("\n✅ Сравнение завершено!")

if __name__ == "__main__":
    asyncio.run(compare_systems())