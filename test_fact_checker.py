#!/usr/bin/env python3
"""
Тестирование обновленного фактчекера
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from openai_filter import OpenAIFilter

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fact_checker():
    """Тест фактчекера с веб-поиском"""
    logger.info("🔍 Тестируем фактчекер с веб-поиском...")
    
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("❌ OPENAI_API_KEY не найден")
        return False
    
    try:
        filter_ai = OpenAIFilter()
        
        test_messages = [
            "Спам! Купи дешевые товары прямо сейчас! Скидка 90%!",
            "Сегодня президент России подписал новый закон об образовании",
            "Новый фильм Marvel побил все рекорды в прокате за первые выходные",
            "а",
            "Курс доллара сегодня упал до 50 рублей",
            "Завтра в Москве ожидается снег в октябре"
        ]
        
        for i, message in enumerate(test_messages, 1):
            logger.info(f"🧪 Тест {i}: '{message}'")
            
            try:
                category, comment = await filter_ai.analyze_message(message, "test_channel")
                logger.info(f"✅ Результат: Категория='{category}', Комментарий='{comment}'")
            except Exception as e:
                logger.error(f"❌ Ошибка в тесте {i}: {e}")
            
            await asyncio.sleep(1)  # Пауза между запросами
            
        logger.info("✅ Фактчекер протестирован")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка фактчекера: {e}")
        return False

async def main():
    logger.info("🚀 Запуск тестов фактчекера...")
    
    fact_checker_ok = await test_fact_checker()
    
    if fact_checker_ok:
        logger.info("✅ Фактчекер готов к работе!")
    else:
        logger.error("❌ Проблемы с фактчекером")

if __name__ == "__main__":
    asyncio.run(main())