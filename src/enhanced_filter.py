"""
Улучшенный фактчекер с умной системой источников
"""

import logging
import asyncio
import json
from typing import Dict, Tuple, List
from openai import AsyncOpenAI
from config import Config
from sources_config import sources_config

logger = logging.getLogger(__name__)

class EnhancedOpenAIFilter:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.gpt5_available = True
        self.sources = sources_config
        
    async def analyze_message(self, text: str, channel_name: str) -> Tuple[str, str]:
        """
        Анализирует сообщение с умным выбором источников
        """
        if not text or len(text.strip()) < 10:
            return "скрыто", "Слишком короткое сообщение"
            
        try:
            # Сначала определяем категорию для выбора источников
            preliminary_category = await self._quick_categorize(text)
            
            # Получаем умный список источников
            smart_sources = self.sources.get_sources_for_topic(text, preliminary_category)
            
            # Ограничиваем количество источников
            if len(smart_sources) > Config.MAX_SOURCE_DOMAINS:
                smart_sources = smart_sources[:Config.MAX_SOURCE_DOMAINS]
            
            logger.info(f"Выбрано {len(smart_sources)} источников для проверки")
            
            # Проводим фактчекинг с умными источниками
            fact_check_result = await self._smart_fact_check(text, smart_sources)
            
            # Финальная категоризация
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
    
    async def _quick_categorize(self, text: str) -> str:
        """Быстрая категоризация для выбора источников"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # Используем более быструю модель для предварительной категоризации
                messages=[{
                    "role": "user", 
                    "content": f"Определи тему одним словом: {text[:200]}... (варианты: технологии, финансы, наука, развлечения, политика, другое)"
                }],
                max_completion_tokens=10,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip().lower()
            
        except Exception as e:
            logger.error(f"Ошибка быстрой категоризации: {e}")
            return "другое"
    
    async def _smart_fact_check(self, text: str, sources: List[str]) -> Dict:
        """Умный фактчекинг с динамическими источниками"""
        
        mode_prompts = {
            "strict": "Будь очень строгим в оценке. Даже малейшие неточности или недостаток источников должны помечаться как сомнительные.",
            "permissive": "Будь более снисходительным. Помечай как мусор только откровенный спам и явную дезинформацию.",
            "smart": "Используй умный подход: анализируй контекст, источники и правдоподобность утверждений."
        }
        
        mode_instruction = mode_prompts.get(Config.FACT_CHECK_MODE, mode_prompts["smart"])
        
        prompt = f"""
{mode_instruction}

Проанализируй это сообщение на предмет достоверности и качества. ОБЯЗАТЕЛЬНО используй веб-поиск для проверки фактов, если сообщение содержит конкретные утверждения, цифры, события или новости.

Сообщение: "{text}"

Для проверки фактов приоритетно используй эти надежные источники:
{', '.join(sources[:15])}

Особое внимание удели:
1. Официальным сайтам упомянутых компаний
2. Проверенным новостным агентствам  
3. Первоисточникам информации

Определи:
1. Это откровенный мусор/спам/реклама? (да/нет)
2. Содержит недостоверные факты или сомнительную информацию? (да/нет) 
3. Если сомнительно - дай короткий комментарий (до 60 символов)

Ответь СТРОГО в формате JSON:
{{
    "is_garbage": true/false,
    "is_questionable": true/false,
    "reason": "причина для мусора",
    "comment": "короткий комментарий для сомнительного",
    "sources_used": ["список использованных источников"]
}}
"""

        try:
            response = await self.client.responses.create(
                model=Config.GPT_MODEL if self.gpt5_available else "gpt-4o",
                tools=[{
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": sources
                    }
                }],
                input=prompt
            )
            
            output_text = response.output_text
            logger.info(f"Анализ GPT: {output_text[:200]}...")
            
            try:
                # Ищем JSON в ответе
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
                    "comment": result.get("comment", ""),
                    "sources_used": result.get("sources_used", [])
                }
            except json.JSONDecodeError:
                logger.warning(f"Не удалось распарсить JSON ответ")
                return await self._fallback_fact_check(text)
            
        except Exception as e:
            logger.error(f"Ошибка умного фактчекинга: {e}")
            if "gpt-5" in str(e) and self.gpt5_available:
                logger.info("GPT-5 недоступен, переключаемся на GPT-4o")
                self.gpt5_available = False
                return await self._smart_fact_check(text, sources)
            return await self._fallback_fact_check(text)
    
    async def _fallback_fact_check(self, text: str) -> Dict:
        """Резервный фактчекинг без веб-поиска"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": f"""
Проанализируй это сообщение на предмет качества (без веб-поиска):

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
"""}],
                max_completion_tokens=200,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)
            
            return {
                "is_garbage": result.get("is_garbage", False),
                "is_questionable": result.get("is_questionable", False),
                "reason": result.get("reason", ""),
                "comment": result.get("comment", ""),
                "sources_used": []
            }
            
        except Exception as e:
            logger.error(f"Ошибка резервного фактчекинга: {e}")
            return {
                "is_garbage": False,
                "is_questionable": False,
                "reason": "",
                "comment": "",
                "sources_used": []
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
                    model=Config.GPT_MODEL,
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
    
    def add_custom_source(self, category: str, domain: str, description: str = ""):
        """Добавляет пользовательский источник"""
        return self.sources.add_custom_source(category, domain, description)
    
    def get_source_stats(self) -> Dict:
        """Возвращает статистику по источникам"""
        stats = {}
        for category, info in self.sources.sources.items():
            if not info.get("auto_detect", False):
                stats[category] = {
                    "description": info.get("description", ""),
                    "domains_count": len(info.get("domains", [])),
                    "domains": info.get("domains", [])[:5]  # Показываем только первые 5
                }
        return stats