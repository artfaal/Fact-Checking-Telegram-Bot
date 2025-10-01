#!/usr/bin/env python3
"""
Тестирование только OpenAI интеграции
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_openai():
    """Тест OpenAI API"""
    logger.info("🤖 Тестируем OpenAI API...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("❌ OPENAI_API_KEY не найден")
        return False
    
    try:
        client = AsyncOpenAI(api_key=api_key)
        
        # Тест базовой функциональности
        logger.info("Тестируем базовый запрос...")
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Скажи 'Привет' по-русски"}],
            max_tokens=50
        )
        logger.info(f"Ответ: {response.choices[0].message.content}")
        
        # Тест GPT-5 (если доступен)
        try:
            logger.info("Тестируем GPT-5...")
            response_gpt5 = await client.chat.completions.create(
                model="gpt-5",
                messages=[{"role": "user", "content": "Скажи 'GPT-5 работает'"}],
                max_completion_tokens=50
            )
            logger.info(f"GPT-5 ответ: {response_gpt5.choices[0].message.content}")
        except Exception as e:
            logger.warning(f"GPT-5 недоступен: {e}")
        
        # Тест Responses API с веб-поиском
        try:
            logger.info("Тестируем Responses API с веб-поиском...")
            response_web = await client.responses.create(
                model="gpt-4o",
                tools=[{"type": "web_search"}],
                input="Какая сегодня погода в Москве?"
            )
            logger.info(f"Веб-поиск ответ: {response_web.output_text[:200]}...")
        except Exception as e:
            logger.warning(f"Веб-поиск недоступен: {e}")
        
        logger.info("✅ OpenAI API работает")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка OpenAI: {e}")
        return False

async def main():
    logger.info("🚀 Запуск тестов OpenAI...")
    
    openai_ok = await test_openai()
    
    if openai_ok:
        logger.info("✅ OpenAI API готов к использованию!")
    else:
        logger.error("❌ Проблемы с OpenAI API")

if __name__ == "__main__":
    asyncio.run(main())