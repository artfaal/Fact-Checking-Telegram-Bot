#!/usr/bin/env python3
"""
Тестирование фильтра без зависимостей от config
"""

import asyncio
import logging
import json
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestOpenAIFilter:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.gpt5_available = True

    async def analyze_message(self, text: str, channel_name: str):
        """Анализирует сообщение с веб-поиском"""
        if not text or len(text.strip()) < 10:
            return "скрыто", "Слишком короткое сообщение"
            
        try:
            fact_check_result = await self._fact_check(text)
            category = await self._categorize(text)
            
            if fact_check_result["is_garbage"]:
                return "скрыто", fact_check_result["reason"]
            elif fact_check_result["is_questionable"]:
                return category, fact_check_result["comment"]
            else:
                return category, ""
                
        except Exception as e:
            logger.error(f"Ошибка анализа OpenAI: {e}")
            return "другое", ""

    async def _fact_check(self, text: str):
        """Фактчекинг с веб-поиском"""
        prompt = f"""
Проанализируй это сообщение на предмет достоверности и качества. ОБЯЗАТЕЛЬНО используй веб-поиск для проверки фактов, если сообщение содержит конкретные утверждения, цифры, события или новости.

Сообщение: "{text}"

Определи:
1. Это откровенный мусор/спам/реклама? (да/нет)
2. Содержит недостоверные факты или сомнительную информацию? (да/нет) 
3. Если сомнительно - дай короткий комментарий (до 50 символов)

Для проверки фактов используй актуальную информацию из интернета.

Ответь СТРОГО в формате JSON:
{{
    "is_garbage": true/false,
    "is_questionable": true/false,
    "reason": "причина для мусора",
    "comment": "короткий комментарий для сомнительного"
}}
"""

        try:
            response = await self.client.responses.create(
                model="gpt-5" if self.gpt5_available else "gpt-4o",
                tools=[{
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": [
                            "reuters.com",
                            "bbc.com", 
                            "cnn.com",
                            "tass.ru",
                            "ria.ru",
                            "kommersant.ru",
                            "vedomosti.ru",
                            "gazeta.ru",
                            "rbc.ru",
                            "interfax.ru"
                        ]
                    }
                }],
                input=prompt
            )
            
            output_text = response.output_text
            logger.info(f"Полный ответ GPT: {output_text}")
            
            # Попытаемся найти JSON в ответе
            try:
                # Ищем JSON блок в тексте
                json_start = output_text.find('{')
                json_end = output_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_text = output_text[json_start:json_end]
                    result = json.loads(json_text)
                else:
                    raise json.JSONDecodeError("JSON не найден", output_text, 0)
                    
                return {
                    "is_garbage": result.get("is_garbage", False),
                    "is_questionable": result.get("is_questionable", False),
                    "reason": result.get("reason", ""),
                    "comment": result.get("comment", "")
                }
            except json.JSONDecodeError:
                logger.warning(f"Не удалось распарсить JSON ответ: {output_text}")
                return self._fallback_fact_check(text)
            
        except Exception as e:
            logger.error(f"Ошибка фактчекинга с веб-поиском: {e}")
            if "gpt-5" in str(e) and self.gpt5_available:
                logger.info("GPT-5 недоступен, переключаемся на GPT-4o")
                self.gpt5_available = False
                return await self._fact_check(text)
            return self._fallback_fact_check(text)

    async def _fallback_fact_check(self, text: str):
        """Резервный фактчекинг без веб-поиска"""
        prompt = f"""
Проанализируй это сообщение на предмет качества:

"{text}"

Определи:
1. Это откровенный мусор/спам/реклама? (да/нет)
2. Содержит сомнительную информацию? (да/нет)
3. Если сомнительно - дай короткий комментарий (до 50 символов)

Ответь СТРОГО в формате JSON:
{{
    "is_garbage": true/false,
    "is_questionable": true/false,
    "reason": "причина для мусора",
    "comment": "короткий комментарий для сомнительного"
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=200,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)
            
            return {
                "is_garbage": result.get("is_garbage", False),
                "is_questionable": result.get("is_questionable", False),
                "reason": result.get("reason", ""),
                "comment": result.get("comment", "")
            }
            
        except Exception as e:
            logger.error(f"Ошибка резервного фактчекинга: {e}")
            return {
                "is_garbage": False,
                "is_questionable": False,
                "reason": "",
                "comment": ""
            }

    async def _categorize(self, text: str):
        """Категоризация сообщения"""
        prompt = f"""
Определи категорию для этого сообщения:

"{text}"

Выбери ОДНУ категорию:
- новости (политика, экономика, события, происшествия)
- развлечения (шоу-бизнес, спорт, культура, юмор)
- другое (всё остальное)

Ответь ТОЛЬКО названием категории без дополнительного текста.
"""

        try:
            if self.gpt5_available:
                response = await self.client.chat.completions.create(
                    model="gpt-5",
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=20
                )
            else:
                response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=20,
                    temperature=0.1
                )
            
            category = response.choices[0].message.content.strip().lower()
            
            if category in ["новости", "развлечения", "другое"]:
                return category
            else:
                return "другое"
                
        except Exception as e:
            logger.error(f"Ошибка категоризации: {e}")
            return "другое"

async def test_fact_checker():
    """Тест фактчекера с веб-поиском"""
    logger.info("🔍 Тестируем фактчекер с веб-поиском...")
    
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("❌ OPENAI_API_KEY не найден")
        return False
    
    try:
        filter_ai = TestOpenAIFilter()
        
        test_messages = [
            "Спам! Купи дешевые товары прямо сейчас! Скидка 90%!",
            "Сегодня президент России подписал новый закон об образовании",
            "Новый фильм Marvel побил все рекорды в прокате за первые выходные"
        ]
        
        for i, message in enumerate(test_messages, 1):
            logger.info(f"🧪 Тест {i}: '{message}'")
            
            try:
                category, comment = await filter_ai.analyze_message(message, "test_channel")
                logger.info(f"✅ Результат: Категория='{category}', Комментарий='{comment}'")
            except Exception as e:
                logger.error(f"❌ Ошибка в тесте {i}: {e}")
            
            await asyncio.sleep(2)  # Пауза между запросами
            
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