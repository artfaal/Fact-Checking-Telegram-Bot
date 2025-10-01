import logging
import asyncio
import json
from typing import Dict, Tuple
from openai import AsyncOpenAI
from config import Config

logger = logging.getLogger(__name__)

class OpenAIFilter:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.gpt5_available = True
        
    async def analyze_message(self, text: str, channel_name: str) -> Tuple[str, str]:
        """
        Анализирует сообщение и возвращает (категория, комментарий)
        Категории: 'новости', 'развлечения', 'другое', 'скрыто'
        """
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
    
    async def _fact_check(self, text: str) -> Dict:
        """Фактчекинг сообщения с веб-поиском"""
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
            
            try:
                result = json.loads(output_text)
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
    
    async def _fallback_fact_check(self, text: str) -> Dict:
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
    
    async def _categorize(self, text: str) -> str:
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