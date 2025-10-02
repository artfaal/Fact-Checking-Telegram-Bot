"""
Двухэтапная система фактчекинга с отладкой
"""

import logging
import asyncio
import json
import time
import re
from datetime import datetime
from typing import Any, Dict, Tuple, List, Optional
from dataclasses import dataclass
from urllib.parse import urlparse
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
    stage2_attempts: int = 0
    confidence_score: int = 0
    verification_status: str = ""
    detailed_findings: str = ""
    contradictions: str = ""
    missing_evidence: str = ""
    special_notes: str = ""
    
    def __post_init__(self):
        if self.sources_found is None:
            self.sources_found = []

class TwoStageFilter:
    """Двухэтапный фактчекер"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.gpt5_available = True
        self.sources = sources_config
        self.fact_check_model = Config.FACT_CHECK_MODEL or "gpt-4o"
        self.web_search_effort = Config.WEB_SEARCH_EFFORT or "medium"
        
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
            sources, analysis = await self._stage1_select_sources(text, debug)
            if debug:
                debug.stage1_time = time.time() - start_time
                debug.sources_found = [src.get("domain") or src.get("url", "") for src in sources]
                debug.sources_count = len(sources)
                debug.reasoning = analysis.get("reasoning", "")

            # Если сообщение не требует глубокого фактчекинга, завершаем на этапе 1
            if not analysis.get("requires_fact_check", True):
                category, comment = self._finalize_without_stage2(analysis)
                return category, comment, debug

            # ЭТАП 2: Фактчекинг по выбранным источникам
            start_time = time.time()
            category, comment = await self._stage2_fact_check(text, sources, analysis, debug)
            if debug:
                debug.stage2_time = time.time() - start_time
            
            return category, comment, debug
            
        except Exception as e:
            logger.error(f"Ошибка двухэтапного анализа: {e}")
            if debug:
                debug.fallback_used = True
                debug.reasoning = f"Ошибка: {str(e)}"
            return "другое", "", debug
    
    async def _stage1_select_sources(self, text: str, debug: Optional[DebugInfo]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        ЭТАП 1: Умный выбор источников для проверки
        """
        logger.info("🔍 STAGE 1: Analyzing text for source selection...")
        
        current_year = datetime.now().year
        prompt = f"""
Ты — ассистент по подготовке к фактчекингу. Изучи сообщение и реши, нужен ли глубокий анализ фактов.

ВАЖНО: Сейчас {current_year} год. Используй актуальный год в поисковых запросах.

Сообщение: "{text}"

Если проверка нужна, предложи до {Config.MAX_SOURCE_DOMAINS} надёжных сайтов (официальные страницы, профильные СМИ, базы данных), на которых можно подтвердить утверждения. Если сообщение похоже на шутку, личную заметку или спам — укажи, почему второй этап не требуется.

Ответь строго JSON-объектом:
{{
  "needs_fact_check": true/false,
  "classification": "news/entertainment/personal/spam/other",
  "reasoning": "краткое объяснение",
  "skip_reason": "почему можно пропустить фактчекинг (если нужно)",
  "source_candidates": [
    {{
      "name": "название источника",
      "url": "https://...",
      "domain": "example.com",
      "why": "зачем этот источник",
      "priority": 1
    }}
  ],
  "recommended_queries": ["поисковый запрос 1", "поисковый запрос 2"]
}}

Правила:
- Не выдумывай домены; если точного URL нет, дай главную страницу организации.
- Учитывай международные и локальные источники.
- Дублирующие сайты не включай.
- В поисковых запросах используй актуальный {current_year} год вместо устаревших дат.
- Если проверка не нужна, выставь "needs_fact_check": false и объясни в "skip_reason".
"""

        analysis: Optional[Dict[str, Any]] = None

        try:
            primary_response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=Config.STAGE1_MAX_TOKENS,
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result_text = primary_response.choices[0].message.content.strip()
            logger.info(f"📋 Stage 1 response: {result_text}")

            analysis = self._parse_stage1_json(result_text)
            if analysis is None:
                logger.info("♻️ STAGE 1: retrying with shortened prompt")
                analysis = await self._stage1_retry_prompt(text)
        except Exception as e:
            logger.error(f"❌ Stage 1 error: {e}")
            analysis = None

        if analysis is None:
            fallback_analysis = {
                "needs_fact_check": True,
                "classification": "other",
                "reasoning": "Не удалось получить ответ от модели",
                "requires_fact_check": True
            }
            backup = self._build_backup_sources(text)
            fallback_analysis["normalized_sources"] = backup
            return backup, fallback_analysis

        raw_candidates = analysis.get("source_candidates", [])
        if not isinstance(raw_candidates, list):
            logger.info("🎯 ЭТАП 1: модель предложила источники в виде %s", type(raw_candidates).__name__)
            logger.debug("📦 Сырые источники в неожиданном формате: %r", raw_candidates)
            raw_candidates = []
        else:
            logger.info("🎯 ЭТАП 1: модель предложила %s сырых источников", len(raw_candidates))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("📦 Сырые источники: %r", raw_candidates[:5])

        normalized_sources = self._normalize_candidates(raw_candidates)
        if normalized_sources:
            logger.info("✅ ЭТАП 1: после нормализации осталось %s источников", len(normalized_sources))
        else:
            logger.info("⚠️ ЭТАП 1: после нормализации источников не осталось")
        analysis["normalized_sources"] = normalized_sources

        requires_fact_check = self._needs_fact_check(analysis)
        analysis["requires_fact_check"] = requires_fact_check

        if not requires_fact_check:
            logger.info("✅ ЭТАП 1 завершен: фактчекинг не требуется")
            return [], analysis

        if not normalized_sources:
            logger.info("ℹ️ ЭТАП 1: не удалось подобрать источники, используем резервный набор")
            backup = self._build_backup_sources(text)
            analysis["normalized_sources"] = backup
            normalized_sources = backup

        logger.info(f"✅ ЭТАП 1 завершен: выбрано {len(normalized_sources)} источников")
        return normalized_sources, analysis

    async def _stage2_fact_check(
        self,
        text: str,
        sources: List[Dict[str, Any]],
        analysis: Dict[str, Any],
        debug: Optional[DebugInfo]
    ) -> Tuple[str, str]:
        """
        ЭТАП 2: Фактчекинг по выбранным источникам
        """
        logger.info(f"📊 ЭТАП 2: Проверяем факты по {len(sources)} источникам...")

        if not sources:
            # Если источники не нужны (например, спам), делаем быструю проверку
            return await self._quick_spam_check(text, debug)

        attempts = self._build_stage2_attempts(sources)
        last_error: Optional[Exception] = None

        for idx, attempt_sources in enumerate(attempts, start=1):
            logger.info(
                "🧪 ЭТАП 2: попытка %s с %s доменами", idx, len(attempt_sources)
            )

            if debug:
                debug.stage2_attempts += 1

            try:
                return await self._run_stage2_attempt(
                    text,
                    attempt_sources,
                    Config.FACT_CHECK_TIMEOUT,
                    analysis,
                    debug
                )
            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError()
                preview = [src.get("domain") or self._extract_domain(src.get("url")) or "?" for src in attempt_sources[:3]]
                preview_text = ", ".join(filter(None, preview))
                if len(attempt_sources) > 3:
                    preview_text += "..."
                logger.warning(
                    "⏰ Таймаут на попытке %s этапа 2 (домены: %s)",
                    idx,
                    preview_text or "неизвестно"
                )
                if debug:
                    base_reason = debug.reasoning if debug.reasoning else "Логика недоступна"
                    debug.reasoning = f"{base_reason} (timeout попытка {idx})"
                continue
            except Exception as e:
                last_error = e
                logger.error(f"❌ Ошибка этапа 2 на попытке {idx}: {e}")
                if "gpt-5" in str(e).lower() and self.gpt5_available:
                    logger.info("GPT-5 недоступен, переключаемся на GPT-4o")
                    self.gpt5_available = False
                    return await self._stage2_fact_check(text, sources, debug)
                if debug:
                    base_reason = debug.reasoning if debug.reasoning else "Логика недоступна"
                    debug.reasoning = f"{base_reason} (ошибка этапа 2, попытка {idx})"
                continue

        logger.warning("⚠️ Этап 2 не дал результата, переходим в fallback")
        if debug:
            debug.fallback_used = True
        if isinstance(last_error, asyncio.TimeoutError):
            if debug:
                base_reason = debug.reasoning if debug.reasoning else "Логика недоступна"
                debug.reasoning = f"{base_reason} (stage2 timeout)"
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
            answer_lower = answer.lower()
            manual_review = "Не удалось подтвердить автоматически, требуется ручная проверка"

            if "спам" in answer_lower or "мусор" in answer_lower:
                return "скрыто", "Определено как спам"

            if "развлеч" in answer_lower:
                return "развлечения", manual_review

            if "новост" in answer_lower:
                return "новости", manual_review

            if "друго" in answer_lower:
                return "другое", manual_review

            return "другое", manual_review
                
        except Exception as e:
            logger.error(f"Ошибка резервной проверки: {e}")
            return "другое", "Не удалось подтвердить автоматически, требуется ручная проверка"

    async def _run_stage2_attempt(
        self,
        text: str,
        attempt_sources: List[Dict[str, Any]],
        timeout: float,
        analysis: Optional[Dict[str, Any]],
        debug: Optional[DebugInfo]
    ) -> Tuple[str, str]:
        """Выполняет одиночную попытку этапа 2 с заданным списком источников."""

        sources_text = self._format_sources_for_prompt(attempt_sources)

        queries = analysis.get("recommended_queries") if analysis else None
        queries_text = ""
        if queries:
            prepared = [q for q in queries[:3] if isinstance(q, str) and q.strip()]
            if prepared:
                # Обновляем годы в поисковых запросах на актуальный
                updated_queries = self._update_queries_with_current_year(prepared)
                bullet_list = "\n".join([f"• {q.strip()}" for q in updated_queries])
                queries_text = f"Рекомендуемые поисковые запросы:\n{bullet_list}\n\n"

        allowed_domains = [
            src.get("domain") or self._extract_domain(src.get("url"))
            for src in attempt_sources
        ]
        allowed_domains = [d for d in allowed_domains if d]

        # Check for X.com/Twitter domains
        x_domains = [d for d in allowed_domains if 'x.com' in d or 'twitter.com' in d]
        
        # Special instructions for X.com/Twitter searches
        x_instructions = ""
        if x_domains:
            x_instructions = f"""

SPECIAL INSTRUCTIONS FOR X.COM/TWITTER:
- Search for specific tweets, posts, and statements by the mentioned people
- Look for recent posts (last 24-48 hours) as well as older content
- Pay attention to verified accounts and official statements
- Search using various formats: direct quotes, paraphrases, key phrases
- Check replies and quote tweets for additional context
- If searching fails, explicitly state "X.com search limitations encountered"
"""

        prompt = f"""
You are a strict fact-checker. Verify this message using web search ONLY on the specified reliable sources.

Sources to check:
{sources_text}

{queries_text}
Message to verify: "{text}"

CRITICAL INSTRUCTIONS:
1. Search the specified domains for EXACT information matching the message
2. Verify EVERY specific claim, detail, and statement in the message
3. Pay special attention to precise wording (e.g., "will affect" vs "will NOT affect")
4. Look for direct quotes or official statements that confirm or contradict the claims
5. If any detail cannot be confirmed or contradicts found information, mark as unconfirmed/contradictory{x_instructions}

Response in strict JSON format:
{{
  "verification_status": "confirmed|partially_confirmed|contradictory|unconfirmed",
  "confidence_score": 75,
  "category": "news|entertainment|other|spam",
  "detailed_findings": "What exactly was found/not found in sources with specific details",
  "contradictions": "Any contradictions found between message and sources",
  "direct_quotes": ["Direct quotes from sources that support or contradict the message"],
  "sources_checked": ["List of sources actually checked"],
  "missing_evidence": "What specific claims lack evidence",
  "special_notes": "Any special circumstances like fresh content, API limitations, etc."
}}

CRITICAL: confidence_score MUST be a numeric integer between 0-100, NOT text like "ninety" or "high".

Verification criteria:
- "confirmed" (90-100): Direct quotes/official statements support ALL claims
- "partially_confirmed" (60-89): Some claims supported, others unclear  
- "contradictory" (30-59): Some claims directly contradicted by sources
- "unconfirmed" (0-29): No supporting evidence found for key claims
"""

        # Special logging for X.com searches
        x_domains = [d for d in allowed_domains if 'x.com' in d or 'twitter.com' in d]
        if x_domains:
            logger.info(f"🐦 X.com поиск: проверяем домены {x_domains}")
            logger.info(f"🔍 Поисковые запросы: {queries_text.strip() if queries_text else 'Нет специальных запросов'}")
            logger.info(f"📝 Текст для проверки: {text[:100]}...")

        responses_client = self.client.responses

        try:
            create_task = responses_client.create(
                model=self.fact_check_model,
                tools=[{
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": allowed_domains
                    }
                }],
                input=prompt,
                tool_choice="auto",
                max_output_tokens=Config.STAGE2_MAX_TOKENS
            )
            initial_response = await asyncio.wait_for(create_task, timeout=timeout)
            response = await self._poll_response(responses_client, initial_response, timeout)
        except asyncio.TimeoutError:
            raise
        except Exception as err:
            if "model" in str(err).lower() and "not supported" in str(err).lower():
                logger.warning(
                    "⚠️ Модель %s не поддерживает Responses API, переключаемся на gpt-4o",
                    self.fact_check_model
                )
                self.fact_check_model = "gpt-4o"
                create_task = responses_client.create(
                    model=self.fact_check_model,
                    tools=[{
                        "type": "web_search",
                        "filters": {
                            "allowed_domains": allowed_domains
                        }
                    }],
                    input=prompt,
                    tool_choice="auto",
                    max_output_tokens=Config.STAGE2_MAX_TOKENS
                )
                initial_response = await asyncio.wait_for(create_task, timeout=timeout)
                response = await self._poll_response(responses_client, initial_response, timeout)
            else:
                raise

        if debug:
            debug.web_search_used = True

        output_text = self._extract_response_text(response)
        status = getattr(response, "status", None)
        logger.debug("📶 Статус ответа этапа 2: %s", status)
        if logger.isEnabledFor(logging.DEBUG):
            try:
                logger.debug("📝 Полный ответ этапа 2: %s", response.model_dump(exclude_none=True))
            except Exception:
                logger.debug("📝 Полный ответ этапа 2: %r", response)
        logger.info(f"📄 Ответ этапа 2: {output_text[:200]}...")
        
        # Special logging for X.com search results  
        x_domains = [d for d in allowed_domains if 'x.com' in d or 'twitter.com' in d]
        if x_domains:
            logger.info(f"🐦 X.com результат: {output_text[:300]}...")
            if 'sources_checked' in output_text.lower():
                try:
                    temp_result = json.loads(output_text if output_text.startswith('{') else output_text[output_text.find('{'):output_text.rfind('}')+1])
                    sources_checked = temp_result.get("sources_checked", [])
                    x_sources_found = [s for s in sources_checked if 'x.com' in str(s).lower() or 'twitter.com' in str(s).lower()]
                    logger.info(f"🐦 X.com источники найдены: {x_sources_found}")
                except:
                    logger.info("🐦 X.com: не удалось извлечь sources_checked из ответа")

        if not output_text:
            raise ValueError("Пустой ответ от модели этапа 2")

        try:
            result = json.loads(output_text)
        except json.JSONDecodeError:
            json_start = output_text.find('{')
            json_end = output_text.rfind('}') + 1
            if json_start == -1 or json_end <= json_start:
                raise json.JSONDecodeError("JSON не найден", output_text, 0)
            json_text = output_text[json_start:json_end]
            result = json.loads(json_text)

        # Handle new verification-based schema
        verification_status = result.get("verification_status", "")
        confidence_score = result.get("confidence_score", 0)
        
        # Validate and fix confidence_score if it's not numeric
        if not isinstance(confidence_score, (int, float)):
            logger.warning(f"⚠️ confidence_score не является числом: {confidence_score}, устанавливаем 0")
            confidence_score = 0
        else:
            confidence_score = int(confidence_score)
            if confidence_score < 0 or confidence_score > 100:
                logger.warning(f"⚠️ confidence_score вне диапазона 0-100: {confidence_score}, корректируем")
                confidence_score = max(0, min(100, confidence_score))
        category = result.get("category", "другое")
        
        # Check for spam category first
        if category == "spam":
            return "скрыто", "Определено как спам"
        
        # Fix confidence_score logic for contradictory status
        # If status is contradictory, confidence_score should reflect low trust in the claim
        if verification_status == "contradictory" and confidence_score > 50:
            # Invert confidence score - high model confidence in contradiction = low trust in claim
            confidence_score = 100 - confidence_score
            logger.info(f"🔄 Inverted confidence_score for contradictory status: {confidence_score}%")
        
        # Extract fields from API response
        detailed_findings = result.get("detailed_findings", "")
        contradictions = result.get("contradictions", "")
        missing_evidence = result.get("missing_evidence", "")
        special_notes = result.get("special_notes", "")
        
        # Save all fields to debug_info
        if debug:
            debug.confidence_score = confidence_score
            debug.verification_status = verification_status
            debug.detailed_findings = detailed_findings
            debug.contradictions = contradictions
            debug.missing_evidence = missing_evidence
            debug.special_notes = special_notes
        
        # Stage 2.5: Translate comment fields to Russian if enabled
        await self._translate_comment_fields(debug)
        
        # Build comment from translated fields
        comment = self._build_translated_comment(verification_status, confidence_score, debug)
        
        return category, comment

    async def _translate_comment_fields(self, debug: Optional[DebugInfo]) -> None:
        """Переводит текстовые поля комментария на русский язык (Stage 2.5)"""
        if not debug or not Config.TRANSLATE_TO_RUSSIAN:
            return
        
        logger.info("🌐 STAGE 2.5: Переводим комментарии на русский...")
        
        # Переводим все доступные поля
        fields_to_translate = [
            ('detailed_findings', 'детальные выводы'),
            ('contradictions', 'противоречия'),
            ('missing_evidence', 'отсутствующие доказательства'),
            ('special_notes', 'специальные примечания')
        ]
        
        for field_name, field_description in fields_to_translate:
            field_value = getattr(debug, field_name, "")
            if field_value and field_value.strip():
                try:
                    translated_text = await self._translate_text(field_value, field_description)
                    setattr(debug, field_name, translated_text)
                    logger.info(f"✅ Переведено поле {field_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка перевода поля {field_name}: {e}")
                    # Оставляем оригинальный текст при ошибке

    async def _translate_text(self, text: str, field_description: str = "текст") -> str:
        """Переводит текст на русский язык с сохранением технической точности"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user", 
                    "content": f"""Переведи этот {field_description} fact-checking системы на русский язык. 
                    
ВАЖНО:
- Сохрани всю техническую точность
- Переведи названия компаний и источников на русский, если это общепринято
- Сохрани специфические термины и даты
- Используй профессиональный тон

Исходный текст:
{text}

Переведенный текст:"""
                }],
                max_completion_tokens=500,
                temperature=0.1,
                timeout=10
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка перевода: {e}")
            return text  # Возвращаем оригинал при ошибке

    def _build_translated_comment(self, verification_status: str, confidence_score: int, debug: Optional[DebugInfo]) -> str:
        """Формирует комментарий на основе уже переведенных полей из debug_info"""
        
        # Получаем переведенные поля из debug_info (если есть)
        detailed_findings = debug.detailed_findings if debug else ""
        contradictions = debug.contradictions if debug else ""
        missing_evidence = debug.missing_evidence if debug else ""
        special_notes = debug.special_notes if debug else ""
        
        # Формируем комментарий на основе verification_status
        if verification_status == "confirmed" and confidence_score >= 90:
            comment = "Достоверно"
            if detailed_findings:
                comment += f" - {detailed_findings}"
        elif verification_status == "partially_confirmed" and confidence_score >= 60:
            comment = "Частично подтверждено"
            if detailed_findings:
                comment += f" - {detailed_findings}"
            elif contradictions:
                comment += f" - некоторые детали не совпадают: {contradictions}"
        elif verification_status == "contradictory":
            comment = "Противоречит источникам"
            if contradictions:
                comment += f" - {contradictions}"
            elif detailed_findings:
                comment += f" - {detailed_findings}"
        elif verification_status == "unconfirmed" or confidence_score < 30:
            comment = "Не подтверждено"
            if missing_evidence:
                comment += f" - {missing_evidence}"
            elif detailed_findings:
                comment += f" - {detailed_findings}"
        else:
            # Fallback for edge cases
            comment = "Требует дополнительной проверки"
            if detailed_findings:
                comment += f" - {detailed_findings}"
        
        # Добавляем специальные примечания если есть
        if special_notes and special_notes.strip():
            comment += f" [Примечание: {special_notes}]"
        
        return comment

    def _build_stage2_attempts(self, sources: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Формирует последовательность попыток для этапа 2 с разными лимитами доменов."""

        unique_sources: List[Dict[str, Any]] = []
        seen = set()
        for candidate in sources:
            domain = candidate.get("domain") or self._extract_domain(candidate.get("url"))
            url = candidate.get("url") or ""
            if not domain and not url:
                continue
            key = (domain or "", url)
            if key in seen:
                continue
            seen.add(key)
            normalized = dict(candidate)
            normalized["domain"] = domain
            if url:
                normalized["url"] = url
            elif domain:
                normalized["url"] = f"https://{domain}"
            unique_sources.append(normalized)

        if not unique_sources:
            return [[]]

        limits: List[int] = []
        if Config.STAGE2_INITIAL_DOMAIN_LIMIT:
            limits.append(Config.STAGE2_INITIAL_DOMAIN_LIMIT)
        if Config.STAGE2_RETRY_DOMAIN_LIMIT and Config.STAGE2_RETRY_DOMAIN_LIMIT != Config.STAGE2_INITIAL_DOMAIN_LIMIT:
            limits.append(Config.STAGE2_RETRY_DOMAIN_LIMIT)
        limits.append(len(unique_sources))

        attempts: List[List[Dict[str, Any]]] = []
        for limit in limits:
            if limit is None or limit <= 0:
                continue
            trimmed = unique_sources[:limit]
            if not trimmed:
                continue
            if trimmed not in attempts:
                attempts.append(trimmed)

        if not attempts:
            attempts.append(unique_sources)
        elif attempts[-1] != unique_sources:
            attempts.append(unique_sources)

        return attempts

    def _needs_fact_check(self, analysis: Dict[str, Any]) -> bool:
        """Определяет необходимость второго этапа на основании анализа этапа 1."""
        if "needs_fact_check" in analysis:
            return bool(analysis.get("needs_fact_check"))

        topic_type = (analysis.get("classification") or analysis.get("topic_type") or "").lower()

        if topic_type in {"spam", "entertainment"}:
            return False

        if topic_type == "personal":
            return False

        return True

    def _finalize_without_stage2(self, analysis: Dict[str, Any]) -> Tuple[str, str]:
        """Формирует итог без запуска второго этапа фактчекинга."""
        classification = (analysis.get("classification") or analysis.get("topic_type") or "").lower()
        skip_reason = analysis.get("skip_reason") or analysis.get("reasoning") or "Не требует фактчекинга"

        if classification == "spam":
            return "скрыто", skip_reason or "Определено как спам"

        if classification == "entertainment":
            return "развлечения", skip_reason if skip_reason else ""

        if classification == "personal":
            return "другое", skip_reason or "Непроверяемое личное сообщение"

        if classification == "news":
            return "новости", skip_reason or "Не требует дополнительной проверки"

        return "другое", skip_reason or "Не требует фактчекинга"

    def _normalize_candidates(self, candidates: Any) -> List[Dict[str, Any]]:
        """Приводит список кандидатов к единому виду."""

        if not isinstance(candidates, list):
            return []

        normalized: List[Dict[str, Any]] = []

        for item in candidates:
            if isinstance(item, dict):
                url = item.get("url") or item.get("link") or ""
                domain = item.get("domain") or self._extract_domain(url)
                if not domain and not url:
                    continue
                name = item.get("name") or domain or url
                why = item.get("why") or item.get("reason") or item.get("note", "")
                priority = item.get("priority")
                try:
                    priority = int(priority)
                except (TypeError, ValueError):
                    priority = len(normalized) + 1
                normalized.append({
                    "name": name,
                    "url": url or (f"https://{domain}" if domain else ""),
                    "domain": domain,
                    "why": why,
                    "priority": priority
                })
            elif isinstance(item, str):
                domain = self._extract_domain(item)
                url = item if item.startswith("http") else (f"https://{item}" if domain else "")
                normalized.append({
                    "name": domain or item,
                    "url": url,
                    "domain": domain,
                    "why": "Источник предложен моделью",
                    "priority": len(normalized) + 1
                })

        filtered = [src for src in normalized if src.get("domain") or src.get("url")]
        filtered.sort(key=lambda s: s.get("priority", 999))
        return filtered[:Config.MAX_SOURCE_DOMAINS]

    def _build_backup_sources(self, text: str) -> List[Dict[str, Any]]:
        """Формирует резервный список источников из конфигурации."""

        fallback_domains = list(self.sources.get_category_domains("general_news"))
        fallback_domains += list(self.sources.get_sources_for_topic(text))

        unique: List[Dict[str, Any]] = []
        seen = set()
        for domain in fallback_domains:
            if not domain or domain in seen:
                continue
            seen.add(domain)
            unique.append({
                "name": domain,
                "url": f"https://{domain}",
                "domain": domain,
                "why": "Резервный источник",
                "priority": len(unique) + 1
            })

        return unique[:Config.MAX_SOURCE_DOMAINS]

    def _extract_domain(self, value: Optional[str]) -> Optional[str]:
        """Извлекает домен из URL или сырой строки."""

        if not value:
            return None

        candidate = value.strip()
        if not candidate or " " in candidate:
            return None

        parsed = urlparse(candidate if candidate.startswith("http") else f"https://{candidate}")
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain or None

    def _update_queries_with_current_year(self, queries: List[str]) -> List[str]:
        """Обновляет поисковые запросы, заменяя устаревшие годы на текущий год."""
        current_year = datetime.now().year
        updated_queries = []
        
        for query in queries:
            # Заменяем годы от 2020 до текущего года-1 на текущий год
            # Примеры: "Крым принадлежность 2023" -> "Крым принадлежность 2025"
            updated_query = query
            for old_year in range(2020, current_year):
                if str(old_year) in query:
                    updated_query = updated_query.replace(str(old_year), str(current_year))
                    logger.info(f"🗓️ Обновлен год в запросе: {old_year} -> {current_year}")
                    break
            
            updated_queries.append(updated_query)
        
        return updated_queries

    def _format_sources_for_prompt(self, sources: List[Dict[str, Any]]) -> str:
        """Форматирует список источников для передачи в модель."""

        lines: List[str] = []
        for src in sources[:15]:
            name = src.get("name") or src.get("domain") or src.get("url")
            url = src.get("url") or (f"https://{src.get('domain')}" if src.get("domain") else "")
            why = src.get("why")
            segments = [segment for segment in [name, url, why] if segment]
            if segments:
                lines.append("• " + " — ".join(segments))

        if not lines:
            return "• (источники не указаны)"

        return "\n".join(lines)

    def _extract_response_text(self, response: Any) -> str:
        """Извлекает текст из объекта ответа Responses API."""

        direct_text = getattr(response, "output_text", None)
        if direct_text:
            return direct_text.strip()

        data: Dict[str, Any] = {}
        if hasattr(response, "model_dump"):
            try:
                data = response.model_dump(exclude_none=True)
            except Exception:
                data = {}
        elif hasattr(response, "dict"):
            try:
                data = response.dict(exclude_none=True)
            except Exception:
                data = {}

        chunks: List[str] = []
        for item in data.get("output", []) or []:
            if isinstance(item, dict):
                item_type = item.get("type")
                if item_type == "message":
                    content = item.get("content") or []
                    chunks.extend(self._extract_text_from_content(content))
                elif item_type == "tool_call":
                    tool = item.get("tool_call") or {}
                    output = tool.get("output") or tool.get("result") or tool.get("response")
                    chunks.extend(self._extract_text_from_tool_output(output))
            else:
                content = getattr(item, "content", None)
                if content:
                    chunks.extend(self._extract_text_from_content(content))

        if chunks:
            return "\n".join(chunks).strip()

        # Последняя попытка — попробовать получить тело ответа целиком
        raw = data.get("response") or data.get("output_text")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()

        return ""

    def _extract_text_from_content(self, content: Any) -> List[str]:
        """Вытягивает текстовые сегменты из контента message."""

        segments: List[str] = []
        for part in content:
            if isinstance(part, dict):
                text_value = part.get("text")
                if text_value:
                    segments.append(text_value)
            else:
                text_value = getattr(part, "text", None)
                if text_value:
                    segments.append(text_value)
        return segments

    def _parse_stage1_json(self, payload: str) -> Optional[Dict[str, Any]]:
        """Simple JSON parsing with fallback to None on truncation."""
        if not payload:
            return None
        
        try:
            return json.loads(payload)
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ STAGE1: Failed to parse JSON (likely truncated): {str(e)[:100]}")
            logger.debug(f"Truncated JSON: {payload[:300]}")
            return None


    def _extract_text_from_tool_output(self, output: Any) -> List[str]:
        """Достает читаемый текст из результата выполнения инструмента."""

        segments: List[str] = []
        if isinstance(output, str):
            segments.append(output)
        elif isinstance(output, list):
            for item in output:
                if isinstance(item, dict):
                    if item.get("type") == "text" and item.get("text"):
                        segments.append(item["text"])
                    elif item.get("title") or item.get("url") or item.get("snippet"):
                        title = item.get("title")
                        snippet = item.get("snippet")
                        url = item.get("url")
                        pieces = [piece for piece in [title, snippet, url] if piece]
                        if pieces:
                            segments.append(" — ".join(pieces))
                elif isinstance(item, str):
                    segments.append(item)
        elif isinstance(output, dict):
            if output.get("text"):
                segments.append(output["text"])
            if output.get("content"):
                segments.extend(self._extract_text_from_tool_output(output["content"]))
        return segments

    async def _poll_response(self, responses_client, response: Any, timeout: float) -> Any:
        """Ожидает завершения Responses API с таймаутом."""

        start = time.time()
        current = response

        while getattr(current, "status", "completed") in {"in_progress", "queued", "requires_action"}:
            remaining = timeout - (time.time() - start)
            if remaining <= 0:
                raise asyncio.TimeoutError("Polling timed out")
            await asyncio.sleep(min(1.5, remaining))
            current = await responses_client.get(current.id)

        return current

    async def _stage1_retry_prompt(self, text: str) -> Optional[Dict[str, Any]]:
        """Повторный запрос для этапа 1 с упрощёнными требованиями."""

        retry_prompt = f"""
Верни валидный JSON (до 6 источников) для проверки фактов по сообщению:
"{text}"

Строго следуй формату:
{{
  "needs_fact_check": true/false,
  "classification": "news/entertainment/personal/spam/other",
  "reasoning": "...",
  "skip_reason": "...",
  "source_candidates": [
    {{"name": "...", "url": "https://...", "domain": "...", "why": "...", "priority": 1}}
  ],
  "recommended_queries": ["..."]
}}

Никакого текста вне JSON.
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": retry_prompt}],
                max_completion_tokens=400,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            result_text = response.choices[0].message.content.strip()
            logger.info(f"📋 Ответ этапа 1 (retry): {result_text}")
            return self._parse_stage1_json(result_text)
        except Exception as err:
            logger.error(f"❌ ЭТАП 1 retry завершился ошибкой: {err}")
            return None
