"""
Двухэтапная система фактчекинга с отладкой
"""

import logging
import asyncio
import json
import time
import re
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
    stage2_attempts: int = 0
    
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
        logger.info("🔍 ЭТАП 1: Анализируем текст для выбора источников...")
        
        prompt = f"""
Ты — ассистент по подготовке к фактчекингу. Изучи сообщение и реши, нужен ли глубокий анализ фактов.

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
- Если проверка не нужна, выставь "needs_fact_check": false и объясни в "skip_reason".
"""

        analysis: Optional[Dict[str, Any]] = None

        try:
            primary_response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=600,
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result_text = primary_response.choices[0].message.content.strip()
            logger.info(f"📋 Ответ этапа 1: {result_text}")

            analysis = self._parse_stage1_json(result_text)
            if analysis is None:
                analysis = self._build_analysis_from_text(result_text, text)
            if analysis is None:
                logger.info("♻️ ЭТАП 1: повторяем запрос с укороченной инструкцией")
                analysis = await self._stage1_retry_prompt(text)
        except Exception as e:
            logger.error(f"❌ Ошибка этапа 1: {e}")
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
                bullet_list = "\n".join([f"• {q.strip()}" for q in prepared])
                queries_text = f"Рекомендуемые поисковые запросы:\n{bullet_list}\n\n"

        allowed_domains = [
            src.get("domain") or self._extract_domain(src.get("url"))
            for src in attempt_sources
        ]
        allowed_domains = [d for d in allowed_domains if d]

        prompt = f"""
Проверь достоверность этого сообщения, используя веб-поиск ТОЛЬКО по указанным надёжным источникам.

Источники:
{sources_text}

{queries_text}
Сообщение: "{text}"

Действия:
1. Найди факты через веб-поиск по разрешённым доменам.
2. Определи, является ли сообщение спамом или сомнительным.
3. Если информация спорная — дай краткий комментарий.
4. Определи категорию: новости / развлечения / другое.
5. Верни результат строго в JSON.

Формат ответа:
{{
  "is_garbage": true/false,
  "is_questionable": true/false,
  "category": "новости/развлечения/другое",
  "reason": "причина если мусор",
  "comment": "комментарий если сомнительно (до 120 символов)",
  "sources_checked": ["список проверенных источников"]
}}
"""

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
                max_output_tokens=600
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
                    max_output_tokens=600
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

        if result.get("is_garbage", False):
            return "скрыто", result.get("reason", "") or "Определено как спам"

        if result.get("is_questionable", False):
            category = result.get("category", "другое")
            comment = result.get("comment", "") or "Не удалось подтвердить автоматически, требуется ручная проверка"
            return category, comment

        category = result.get("category", "другое")
        comment = result.get("comment", "")
        return category, comment

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
        """Пытается распарсить JSON ответа этапа 1, восстанавливая обрезанный текст."""

        if not payload:
            return None

        def try_load(candidate: str) -> Optional[Dict[str, Any]]:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return None

        # Первая попытка — как есть
        parsed = try_load(payload)
        if parsed is not None:
            return parsed

        # Попытка добавить закрывающие скобки
        balanced = payload
        brace_diff = balanced.count('{') - balanced.count('}')
        if brace_diff > 0:
            balanced += '}' * brace_diff
        bracket_diff = balanced.count('[') - balanced.count(']')
        if bracket_diff > 0:
            balanced += ']' * bracket_diff

        parsed = try_load(balanced)
        if parsed is not None:
            logger.warning("⚠️ ЭТАП 1: восстановили JSON добавлением закрывающих скобок")
            return parsed

        # Итеративно обрезаем до последней закрывающей скобки
        for end in range(len(payload), 0, -1):
            if payload[end - 1] not in '}])\"':
                continue
            candidate = payload[:end]
            candidate = candidate.rstrip(',')
            candidate_parsed = try_load(candidate)
            if candidate_parsed is not None:
                logger.warning("⚠️ ЭТАП 1: использовали усечённый JSON")
                return candidate_parsed

        logger.warning(
            "⚠️ ЭТАП 1: не удалось распарсить JSON. Обрезанный фрагмент: %s",
            payload[:200]
        )
        return None

    def _build_analysis_from_text(self, payload: str, original_text: str) -> Optional[Dict[str, Any]]:
        """Извлекает информацию из частично обрезанного JSON."""

        if not payload:
            return None

        def capture(field: str) -> str:
            match = re.search(rf'"{field}"\s*:\s*"([^"]*)"', payload)
            return match.group(1) if match else ""

        classification = capture("classification") or "other"
        reasoning = capture("reasoning") or ""
        skip_reason = capture("skip_reason")

        candidate_pattern = re.compile(
            r'\{[^\}]*?"name"\s*:\s*"(?P<name>[^"]+)"[^\}]*?"url"\s*:\s*"(?P<url>[^"]+)"'
            r'[^\}]*?"domain"\s*:\s*"(?P<domain>[^"]+)"[^\}]*?"why"\s*:\s*"(?P<why>[^"]+)"'
            r'[^\}]*?"priority"\s*:\s*(?P<priority>\d+)',
            re.S
        )

        candidates: List[Dict[str, Any]] = []
        for match in candidate_pattern.finditer(payload):
            try:
                candidates.append({
                    "name": match.group("name"),
                    "url": match.group("url"),
                    "domain": match.group("domain"),
                    "why": match.group("why"),
                    "priority": int(match.group("priority"))
                })
            except Exception:
                continue

        if not candidates:
            return None

        analysis = {
            "needs_fact_check": True,
            "classification": classification,
            "reasoning": reasoning or "",
            "skip_reason": skip_reason,
            "source_candidates": candidates[:Config.MAX_SOURCE_DOMAINS],
            "recommended_queries": []
        }

        logger.warning("⚠️ ЭТАП 1: использовали эвристику для разбора усечённого JSON")
        return analysis

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
            analysis = self._parse_stage1_json(result_text)
            if analysis is None:
                analysis = self._build_analysis_from_text(result_text, text)
            return analysis
        except Exception as err:
            logger.error(f"❌ ЭТАП 1 retry завершился ошибкой: {err}")
            return None
