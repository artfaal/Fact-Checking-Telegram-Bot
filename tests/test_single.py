#!/usr/bin/env python3
"""
Быстрый тест одного сообщения
"""

import asyncio
import logging
from test_filter_standalone import TestOpenAIFilter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    filter_ai = TestOpenAIFilter()
    message = "Спам! Купи дешевые товары прямо сейчас!"
    
    logger.info(f"Тестируем: '{message}'")
    category, comment = await filter_ai.analyze_message(message, "test")
    logger.info(f"Результат: {category} | {comment}")

if __name__ == "__main__":
    asyncio.run(main())