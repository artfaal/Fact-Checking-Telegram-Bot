#!/usr/bin/env python3
"""
Тест поиска по X.com для анализа проблем с поиском твитов
"""

import asyncio
import logging
import sys
import os

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from two_stage_filter import TwoStageFilter

# Настройка логирования для детального анализа
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_william_gibson_tweet():
    """Тест поиска твита Уильяма Гибсона о Викторе Цое"""
    logger.info("🧪 Тестируем поиск твита Уильяма Гибсона о Викторе Цое")
    
    # Текст из твита пользователя
    tweet_text = """«Отец Киберпанка» Уилльям Гибсон признался, что именно Виктор Цой оказал самое сильное влияние на его творчество.

Гибсон, автор культового «Нейроманта», отметил, что музыка Цоя стала для него главным источником вдохновения. Он с сожалением добавил, что большинство его читателей никогда не слышали ни о самом музыканте, ни о его песнях.

Позже по канонам, заложенным Гибсоном, появились десятки культовых произведений — от литературы до игр, включая «Cyberpunk 2077».

Об этом он написал у себя в твиттере (X) в верифтцированном аккаунте"""
    
    filter_system = TwoStageFilter()
    
    try:
        # Анализируем сообщение с детальным логированием
        category, comment, debug_info = await filter_system.analyze_message(
            tweet_text, "X.com Tweet Test"
        )
        
        logger.info("📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
        logger.info(f"  📂 Категория: {category}")
        logger.info(f"  💬 Комментарий: {comment}")
        
        if debug_info:
            logger.info("🔧 DEBUG INFO:")
            logger.info(f"  ⏱️ Этап 1: {debug_info.stage1_time:.2f}с")
            logger.info(f"  ⏱️ Этап 2: {debug_info.stage2_time:.2f}с")
            logger.info(f"  🌐 Найдено источников: {debug_info.sources_count}")
            logger.info(f"  📋 Источники: {debug_info.sources_found}")
            logger.info(f"  🔍 Веб-поиск использован: {debug_info.web_search_used}")
            
            # Проверяем наличие X.com в источниках
            x_sources = [s for s in debug_info.sources_found if 'x.com' in s.lower() or 'twitter.com' in s.lower()]
            if x_sources:
                logger.info(f"  🐦 X.com источники: {x_sources}")
            else:
                logger.warning("  ⚠️ X.com источники НЕ найдены в списке")
            
            # Выводим детальную информацию
            if debug_info.detailed_findings:
                logger.info(f"  📋 Детальные выводы: {debug_info.detailed_findings}")
            if debug_info.missing_evidence:
                logger.info(f"  ❓ Отсутствующие доказательства: {debug_info.missing_evidence}")
                
    except Exception as e:
        logger.error(f"❌ Ошибка в тесте: {e}")
        raise

async def test_simple_gibson_tsoi():
    """Упрощенный тест поиска связи Gibson-Tsoi"""
    logger.info("\n🧪 Тестируем упрощенный поиск Gibson + Tsoi")
    
    simple_text = "William Gibson Viktor Tsoi influence"
    
    filter_system = TwoStageFilter()
    
    try:
        category, comment, debug_info = await filter_system.analyze_message(
            simple_text, "Simple Gibson-Tsoi Test"
        )
        
        logger.info("📊 УПРОЩЕННЫЙ ТЕСТ:")
        logger.info(f"  📂 Категория: {category}")
        logger.info(f"  💬 Комментарий: {comment}")
        
        if debug_info and debug_info.sources_found:
            x_sources = [s for s in debug_info.sources_found if 'x.com' in s.lower() or 'twitter.com' in s.lower()]
            logger.info(f"  🐦 X.com в источниках: {'ДА' if x_sources else 'НЕТ'}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка в упрощенном тесте: {e}")

async def main():
    """Главная функция"""
    logger.info("🚀 Запуск тестов поиска по X.com")
    
    # Выполняем оба теста
    await test_william_gibson_tweet()
    await test_simple_gibson_tsoi()
    
    logger.info("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(main())