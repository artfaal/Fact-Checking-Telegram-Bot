"""
Двухэтапная система фактчекинга с отладкой
"""

import logging
import asyncio
import json
import time
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from openai import AsyncOpenAI
from config import Config
from sources_config import sources_config

logger = logging.getLogger(__name__)

@dataclass
class DebugInfo:
    """Информация для отладки"""
    stage1_time: float = 0
    stage2_time: float = 0
    sources_found: List[str] = None
    sources_count: int = 0
    reasoning: str = ""
    web_search_used: bool = False
    fallback_used: bool = False
    
    def __post_init__(self):
        if self.sources_found is None:
            self.sources_found = []

class TwoStageFilter:
    """Двухэтапный фактчекер"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.gpt5_available = True
        self.sources = sources_config
        
    async def analyze_message(self, text: str, channel_name: str) -> Tuple[str, str, Optional[DebugInfo]]:
        """
        Двухэтапный анализ сообщения
        Возвращает: (категория, комментарий, отладочная_информация)
        """
        if not text or len(text.strip()) < 10:
            return "скрыто", "Слишком короткое сообщение", None
            
        debug = DebugInfo() if Config.DEBUG_MODE else None
        
        try:
            # ЭТАП 1: Определение источников для проверки
            start_time = time.time()
            sources = await self._stage1_select_sources(text, debug)
            if debug:
                debug.stage1_time = time.time() - start_time
                debug.sources_found = sources
                debug.sources_count = len(sources)
            
            # ЭТАП 2: Фактчекинг по выбранным источникам
            start_time = time.time()
            category, comment = await self._stage2_fact_check(text, sources, debug)
            if debug:
                debug.stage2_time = time.time() - start_time
            
            return category, comment, debug
            
        except Exception as e:
            logger.error(f"Ошибка двухэтапного анализа: {e}")
            if debug:
                debug.fallback_used = True
                debug.reasoning = f"Ошибка: {str(e)}"
            return "другое", "", debug
    
    async def _stage1_select_sources(self, text: str, debug: Optional[DebugInfo]) -> List[str]:
        """
        ЭТАП 1: Умный выбор источников для проверки
        """
        logger.info("🔍 ЭТАП 1: Анализируем текст для выбора источников...")
        
        prompt = f"""
Проанализируй это сообщение и определи, какие источники лучше всего подойдут для проверки фактов:

"{text}"

Определи:
1. Если упоминается конкретная компания (Discord, Google, Apple и т.д.) - нужны их официальные сайты
2. Если это финансовые новости - нужны финансовые источники  
3. Если это научная информация - нужны научные журналы
4. Если это игровые новости - нужны сайты издателей/разработчиков
5. Если это просто спам - источники не нужны

Ответь в формате JSON:
{{
    "topic_type": "company/finance/science/gaming/entertainment/politics/spam/other",
    "mentioned_companies": ["список компаний если есть"],
    "recommended_categories": ["technology", "finance", "science", "entertainment"],
    "reasoning": "краткое объяснение выбора"
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # Используем быструю модель для выбора источников
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=200,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            logger.info(f"📋 Ответ этапа 1: {result_text}")
            
            # Парсим ответ
            try:
                analysis = json.loads(result_text)
            except json.JSONDecodeError:
                # Fallback - используем базовый анализ
                analysis = {"topic_type": "other", "recommended_categories": ["general_news"]}
            
            if debug:
                debug.reasoning = analysis.get("reasoning", "")
            
            # Если это спам, возвращаем пустой список
            if analysis.get("topic_type") == "spam":
                return []
            
            # Собираем источники
            selected_sources = set()
            
            # Добавляем общие новостные источники
            selected_sources.update(self.sources.get_category_domains("general_news"))
            
            # Добавляем тематические источники
            for category in analysis.get("recommended_categories", []):
                selected_sources.update(self.sources.get_category_domains(category))
            
            # Добавляем официальные сайты упомянутых компаний
            for company in analysis.get("mentioned_companies", []):
                company_lower = company.lower()
                if company_lower in self.sources.sources["company_specifics"]["patterns"]:
                    company_domains = self.sources.sources["company_specifics"]["patterns"][company_lower]
                    selected_sources.update(company_domains)
            
            # Применяем автоматический выбор из существующей системы
            auto_sources = self.sources.get_sources_for_topic(text)
            selected_sources.update(auto_sources)
            
            # Ограничиваем количество
            final_sources = list(selected_sources)[:Config.MAX_SOURCE_DOMAINS]
            
            logger.info(f"✅ ЭТАП 1 завершен: выбрано {len(final_sources)} источников")
            return final_sources
            
        except Exception as e:
            logger.error(f"❌ Ошибка этапа 1: {e}")
            # Fallback - используем базовые источники
            return self.sources.get_category_domains("general_news")[:10]
    
    async def _stage2_fact_check(self, text: str, sources: List[str], debug: Optional[DebugInfo]) -> Tuple[str, str]:
        """
        ЭТАП 2: Фактчекинг по выбранным источникам
        """
        logger.info(f"📊 ЭТАП 2: Проверяем факты по {len(sources)} источникам...")
        
        if not sources:
            # Если источники не нужны (например, спам), делаем быструю проверку
            return await self._quick_spam_check(text, debug)
        
        # Формируем промт для фактчекинга
        sources_text = "\n".join([f"• {domain}" for domain in sources[:15]])
        
        prompt = f"""
Проверь достоверность этого сообщения, используя веб-поиск ТОЛЬКО по этим надежным источникам:

{sources_text}

Сообщение: "{text}"

Задача:
1. Найди информацию в указанных источниках
2. Определи: это спам/мусор или нормальное сообщение
3. Если информация сомнительная - дай краткий комментарий
4. Определи категорию: новости, развлечения или другое

Ответь в формате JSON:
{{
    "is_garbage": true/false,
    "is_questionable": true/false,  
    "category": "новости/развлечения/другое",
    "reason": "причина если мусор",
    "comment": "комментарий если сомнительно (до 60 символов)",
    "sources_checked": ["список проверенных источников"]
}}
"""

        try:
            # Используем веб-поиск с выбранными источниками
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
            
            if debug:
                debug.web_search_used = True
            
            output_text = response.output_text
            logger.info(f"📄 Ответ этапа 2: {output_text[:200]}...")
            
            # Парсим результат
            try:
                json_start = output_text.find('{')
                json_end = output_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_text = output_text[json_start:json_end]
                    result = json.loads(json_text)
                else:
                    raise json.JSONDecodeError("JSON не найден", output_text, 0)
                
                # Формируем итоговый результат
                if result.get("is_garbage", False):
                    return "скрыто", result.get("reason", "")
                elif result.get("is_questionable", False):
                    category = result.get("category", "другое")
                    comment = result.get("comment", "")
                    return category, comment
                else:
                    category = result.get("category", "другое")
                    return category, ""
                    
            except json.JSONDecodeError:
                logger.warning("Не удалось распарсить JSON, используем fallback")
                if debug:
                    debug.fallback_used = True
                return await self._fallback_check(text, debug)
            
        except Exception as e:
            logger.error(f"❌ Ошибка этапа 2: {e}")
            if "gpt-5" in str(e) and self.gpt5_available:
                logger.info("GPT-5 недоступен, переключаемся на GPT-4o")
                self.gpt5_available = False
                return await self._stage2_fact_check(text, sources, debug)
            
            if debug:
                debug.fallback_used = True
            return await self._fallback_check(text, debug)
    
    async def _quick_spam_check(self, text: str, debug: Optional[DebugInfo]) -> Tuple[str, str]:
        """Быстрая проверка на спам без веб-поиска"""
        logger.info("⚡ Быстрая проверка на спам...")
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user", 
                    "content": f"Это спам/реклама/мусор? Ответь одним словом (да/нет): {text[:200]}"
                }],
                max_completion_tokens=10,
                temperature=0.1
            )
            
            answer = response.choices[0].message.content.strip().lower()
            
            if "да" in answer or "спам" in answer:
                return "скрыто", "Определено как спам/реклама"
            else:
                return "другое", ""
                
        except Exception as e:
            logger.error(f"Ошибка быстрой проверки: {e}")
            return "другое", ""
    
    async def _fallback_check(self, text: str, debug: Optional[DebugInfo]) -> Tuple[str, str]:
        """Резервная проверка"""
        logger.info("🔄 Резервная проверка...")
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user", 
                    "content": f"""
Кратко оцени это сообщение:
"{text}"

Это: 1) спам/мусор 2) новости 3) развлечения 4) другое
Ответь одной строкой: категория | комментарий (если нужен)
"""
                }],
                max_completion_tokens=50,
                temperature=0.1
            )
            
            answer = response.choices[0].message.content.strip()
            
            if "спам" in answer.lower() or "мусор" in answer.lower():
                return "скрыто", "Определено как спам"
            elif "новости" in answer.lower():
                return "новости", ""
            elif "развлечения" in answer.lower():
                return "развлечения", ""
            else:
                return "другое", ""
                
        except Exception as e:
            logger.error(f"Ошибка резервной проверки: {e}")
            return "другое", ""