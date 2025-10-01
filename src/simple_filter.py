"""
Простой фильтр с предустановленными источниками из конфига
"""

import logging
import asyncio
import json
from typing import Dict, Tuple, List
from openai import AsyncOpenAI
from config import Config

logger = logging.getLogger(__name__)

class SimpleFilter:
    """Простой фильтр с фиксированным списком источников"""
    
    def __init__(self, sources: List[str] = None):
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.gpt5_available = True
        
        # Если источники не переданы, используем базовые из конфига
        self.sources = sources or [
            "reuters.com", "bbc.com", "cnn.com", "tass.ru", "ria.ru",
            "kommersant.ru", "vedomosti.ru", "gazeta.ru", "rbc.ru", "interfax.ru"
        ]
        
        logger.info(f"🔧 Простой фильтр инициализирован с {len(self.sources)} источниками")
    
    async def analyze_message(self, text: str, channel_name: str) -> Tuple[str, str]:
        """
        Простой анализ с фиксированным списком источников
        """
        if not text or len(text.strip()) < 10:
            return "скрыто", "Слишком короткое сообщение"
        
        logger.info(f"📊 Простой анализ с {len(self.sources)} источниками...")
        
        try:
            # Быстрая проверка на спам
            is_spam = await self._quick_spam_check(text)
            if is_spam:
                return "скрыто", "Определено как спам"
            
            # Фактчекинг с фиксированными источниками
            category, comment = await self._fact_check_with_sources(text)
            return category, comment
            
        except Exception as e:
            logger.error(f"❌ Ошибка простого анализа: {e}")
            return "другое", ""
    
    async def _quick_spam_check(self, text: str) -> bool:
        """Быстрая проверка на спам"""
        spam_indicators = [
            "скидка", "акция", "купи", "продам", "заработок", "млн руб",
            "жми", "переходи", "кликай", "только сегодня", "только сейчас",
            "mega", "super", "лучшая цена", "бесплатно", "!!!!"
        ]
        
        text_lower = text.lower()
        spam_count = sum(1 for indicator in spam_indicators if indicator in text_lower)
        
        # Если много спам-индикаторов, считаем спамом
        if spam_count >= 3:
            logger.info(f"⚡ Быстро определен как спам ({spam_count} индикаторов)")
            return True
        
        return False
    
    async def _fact_check_with_sources(self, text: str) -> Tuple[str, str]:
        """Фактчекинг с фиксированными источниками"""
        
        sources_text = ", ".join(self.sources)
        
        prompt = f"""
Проверь это сообщение, используя веб-поиск по надежным источникам:

Сообщение: "{text}"

Источники для проверки: {sources_text}

Определи:
1. Категорию: новости, развлечения или другое
2. Нужен ли комментарий если информация сомнительная

Ответь в формате JSON:
{{
    "category": "новости/развлечения/другое",
    "is_questionable": true/false,
    "comment": "комментарий если сомнительно (до 60 символов)"
}}
"""

        try:
            # Используем веб-поиск с источниками
            response = await self.client.responses.create(
                model=Config.GPT_MODEL if self.gpt5_available else "gpt-4o",
                tools=[{
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": self.sources
                    }
                }],
                input=prompt
            )
            
            output_text = response.output_text
            logger.info(f"📄 Ответ простого фильтра: {output_text[:150]}...")
            
            # Парсим результат
            try:
                json_start = output_text.find('{')
                json_end = output_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_text = output_text[json_start:json_end]
                    result = json.loads(json_text)
                else:
                    raise json.JSONDecodeError("JSON не найден", output_text, 0)
                
                category = result.get("category", "другое")
                
                if result.get("is_questionable", False):
                    comment = result.get("comment", "Требует проверки")
                    return category, comment
                else:
                    return category, ""
                    
            except json.JSONDecodeError:
                logger.warning("Не удалось распарсить JSON простого фильтра")
                return await self._fallback_check(text)
            
        except Exception as e:
            logger.error(f"❌ Ошибка фактчекинга простым фильтром: {e}")
            if "gpt-5" in str(e) and self.gpt5_available:
                logger.info("GPT-5 недоступен, переключаемся на GPT-4o")
                self.gpt5_available = False
                return await self._fact_check_with_sources(text)
            
            return await self._fallback_check(text)
    
    async def _fallback_check(self, text: str) -> Tuple[str, str]:
        """Резервная проверка без веб-поиска"""
        logger.info("🔄 Резервная проверка простого фильтра...")
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user", 
                    "content": f"""
Определи категорию для сообщения: "{text}"

Варианты: новости, развлечения, другое
Ответь одним словом.
"""
                }],
                max_completion_tokens=10,
                temperature=0.1
            )
            
            category = response.choices[0].message.content.strip().lower()
            
            if category in ["новости", "развлечения", "другое"]:
                return category, ""
            else:
                return "другое", ""
                
        except Exception as e:
            logger.error(f"❌ Ошибка резервной проверки: {e}")
            return "другое", ""