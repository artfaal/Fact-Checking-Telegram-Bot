import logging
import asyncio
from typing import Dict, Tuple
from openai import AsyncOpenAI
from config import Config

logger = logging.getLogger(__name__)

class OpenAIFilter:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        
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
        """Фактчекинг сообщения"""
        prompt = f"""
Проанализируй это сообщение на предмет достоверности и качества:

"{text}"

Определи:
1. Это откровенный мусор/спам/реклама? (да/нет)
2. Содержит недостоверные факты или сомнительную информацию? (да/нет)
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
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            
            import json
            result = json.loads(result_text)
            
            return {
                "is_garbage": result.get("is_garbage", False),
                "is_questionable": result.get("is_questionable", False),
                "reason": result.get("reason", ""),
                "comment": result.get("comment", "")
            }
            
        except Exception as e:
            logger.error(f"Ошибка фактчекинга: {e}")
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
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
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