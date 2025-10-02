#!/usr/bin/env python3
"""
Тест русского перевода и форматирования полей
"""

import asyncio
import logging
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from two_stage_filter import TwoStageFilter, DebugInfo
from command_handler import CommandHandler
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockBot:
    """Mock объект бота для тестирования"""
    def __init__(self):
        self.messages = []
    
    async def send_message(self, chat_id, text, reply_to_message_id=None):
        message = MagicMock()
        message.id = len(self.messages) + 1
        message.text = text
        self.messages.append({"chat_id": chat_id, "text": text, "reply_to": reply_to_message_id})
        return message
    
    async def edit_message_text(self, chat_id, message_id, text):
        self.messages.append({"chat_id": chat_id, "message_id": message_id, "text": text, "edited": True})
    
    async def delete_messages(self, chat_id, message_ids):
        pass

class MockMessage:
    """Mock объект сообщения для тестирования"""
    def __init__(self, text, username="testuser"):
        self.text = text
        self.caption = None
        self.chat = MagicMock()
        self.chat.id = 12345
        self.from_user = MagicMock()
        self.from_user.username = username
        self.from_user.first_name = "Test User"
        self.id = 67890

async def test_translation_functionality():
    """Тест функции перевода комментариев"""
    logger.info("🌐 Тестируем функцию перевода...")
    
    # Временно включаем перевод для тестов
    original_translate = Config.TRANSLATE_TO_RUSSIAN
    Config.TRANSLATE_TO_RUSSIAN = True
    
    try:
        filter_system = TwoStageFilter()
        
        # Создаем mock debug_info с английскими полями
        debug_info = DebugInfo()
        debug_info.detailed_findings = "The announcement was confirmed by official Discord blog post on March 15, 2024"
        debug_info.contradictions = "No contradictions found in multiple sources"
        debug_info.missing_evidence = "No additional evidence needed for this confirmed information"
        
        # Мокаем перевод, чтобы не делать реальные API вызовы
        with patch.object(filter_system, '_translate_text') as mock_translate:
            mock_translate.side_effect = [
                "Объявление подтверждено официальным блогом Discord от 15 марта 2024 года",
                "Противоречий в нескольких источниках не найдено", 
                "Дополнительных доказательств для подтвержденной информации не требуется"
            ]
            
            # Выполняем перевод
            await filter_system._translate_comment_fields(debug_info)
            
            # Проверяем результаты
            logger.info("📋 Переведенные поля:")
            logger.info(f"  Детальные выводы: {debug_info.detailed_findings}")
            logger.info(f"  Противоречия: {debug_info.contradictions}")
            logger.info(f"  Отсутствующие доказательства: {debug_info.missing_evidence}")
            
            # Проверяем что перевод был вызван
            assert mock_translate.call_count == 3
            assert "Discord" in debug_info.detailed_findings
            logger.info("✅ Перевод работает корректно")
    
    finally:
        # Восстанавливаем оригинальные настройки
        Config.TRANSLATE_TO_RUSSIAN = original_translate

async def test_formatting_with_all_fields():
    """Тест форматирования с отображением всех полей отдельно"""
    logger.info("📝 Тестируем форматирование с раздельными полями...")
    
    handler = CommandHandler()
    
    # Создаем debug_info со всеми полями
    debug_info = DebugInfo()
    debug_info.confidence_score = 85
    debug_info.verification_status = "partially_confirmed"
    debug_info.detailed_findings = "Объявление подтверждено официальным блогом Discord от 15 марта 2024 года"
    debug_info.contradictions = "Дата запуска отличается в разных источниках"
    debug_info.missing_evidence = "Точные технические детали функции не указаны"
    debug_info.sources_found = ["discord.com", "techcrunch.com", "theverge.com"]
    debug_info.reasoning = "Выбраны официальные и проверенные технологические источники"
    
    # Тестируем форматирование для fact check
    result = await handler._format_fact_check_result("новости", "Частично подтверждено", debug_info)
    
    logger.info("🎨 Результат форматирования fact check:")
    logger.info(result)
    
    # Проверяем что все поля присутствуют
    assert "📋 Детальные выводы:" in result
    assert "⚠️ Противоречия:" in result  
    assert "❓ Отсутствующие доказательства:" in result
    assert "🌐 Источники:" in result
    assert "💭 Логика выбора:" in result
    assert "85%" in result
    logger.info("✅ Все поля отображаются корректно")

async def test_formatting_with_missing_fields():
    """Тест форматирования когда некоторые поля отсутствуют"""
    logger.info("🧪 Тестируем форматирование с отсутствующими полями...")
    
    handler = CommandHandler()
    
    # Создаем debug_info только с некоторыми полями
    debug_info = DebugInfo()
    debug_info.confidence_score = 95
    debug_info.verification_status = "confirmed"
    debug_info.detailed_findings = "Полностью подтверждено официальными источниками"
    # contradictions и missing_evidence намеренно пустые
    debug_info.contradictions = ""
    debug_info.missing_evidence = ""
    debug_info.sources_found = ["discord.com"]
    
    result = await handler._format_fact_check_result("новости", "Достоверно", debug_info)
    
    logger.info("🎨 Результат с частичными полями:")
    logger.info(result)
    
    # Проверяем что пустые поля не отображаются
    assert "📋 Детальные выводы:" in result
    assert "⚠️ Противоречия:" not in result  # Пустое поле не должно показываться
    assert "❓ Отсутствующие доказательства:" not in result  # Пустое поле не должно показываться
    assert "🌐 Источники:" in result
    logger.info("✅ Пустые поля корректно скрываются")

async def test_integration_mock_fact_check():
    """Интеграционный тест с моком API для проверки полного цикла"""
    logger.info("🔗 Интеграционный тест полного цикла...")
    
    # Временно включаем перевод
    original_translate = Config.TRANSLATE_TO_RUSSIAN
    Config.TRANSLATE_TO_RUSSIAN = True
    
    try:
        handler = CommandHandler()
        bot = MockBot()
        message = MockMessage("Discord announced new AI moderation feature for voice channels")
        
        # Мокаем весь two_stage_filter для предсказуемого результата
        with patch.object(handler.two_stage_filter, 'analyze_message') as mock_analyze:
            # Подготавливаем mock результат с переведенными полями
            debug_info = DebugInfo()
            debug_info.confidence_score = 78
            debug_info.verification_status = "partially_confirmed"
            debug_info.detailed_findings = "Функция ИИ-модерации подтверждена в блоге Discord"
            debug_info.contradictions = "Дата запуска различается в источниках"
            debug_info.missing_evidence = "Технические детали не раскрыты"
            debug_info.sources_found = ["discord.com", "techcrunch.com"]
            debug_info.reasoning = "Выбраны официальные источники Discord и проверенные новостные сайты"
            
            mock_analyze.return_value = ("новости", "Частично подтверждено", debug_info)
            
            # Выполняем fact check
            await handler.handle_fact_check(bot, message)
            
            # Проверяем что сообщения были отправлены
            assert len(bot.messages) >= 2  # processing + result или delete
            
            # Находим итоговое сообщение результата (последнее send_message)
            result_messages = [msg for msg in bot.messages if msg.get("reply_to") is not None]
            assert len(result_messages) > 0
            
            result_text = result_messages[0]["text"]
            logger.info("📨 Итоговое сообщение:")
            logger.info(result_text)
            
            # Проверяем что все переведенные поля присутствуют
            assert "📋 Детальные выводы:" in result_text
            assert "⚠️ Противоречия:" in result_text
            assert "❓ Отсутствующие доказательства:" in result_text
            assert "🌐 Источники:" in result_text
            assert "78%" in result_text
            
            logger.info("✅ Полный цикл работает корректно с переводом и форматированием")
    
    finally:
        Config.TRANSLATE_TO_RUSSIAN = original_translate

async def test_comment_full_translation():
    """Тест полного перевода комментария без английских фраз"""
    logger.info("🌐 Тестируем полный перевод комментария...")
    
    # Временно включаем перевод
    original_translate = Config.TRANSLATE_TO_RUSSIAN
    Config.TRANSLATE_TO_RUSSIAN = True
    
    try:
        filter_system = TwoStageFilter()
        
        # Мокаем _run_stage2_attempt, чтобы получить предсказуемый результат
        with patch.object(filter_system, '_run_stage2_attempt') as mock_stage2:
            # Создаем debug_info с английскими полями (до перевода)
            debug_info = DebugInfo()
            debug_info.confidence_score = 15
            debug_info.verification_status = "unconfirmed"
            debug_info.detailed_findings = "No evidence found for the medical adhesive Bone-02"
            debug_info.contradictions = "No contradictions found"
            debug_info.missing_evidence = "All claims about rapid bone healing lack supporting evidence"
            
            # Мокаем перевод для предсказуемого результата
            with patch.object(filter_system, '_translate_text') as mock_translate:
                mock_translate.side_effect = [
                    "Доказательства медицинского клея Bone-02 не найдены",
                    "Противоречий не обнаружено",
                    "Все утверждения о быстром заживлении костей не имеют подтверждающих доказательств"
                ]
                
                # Имитируем вызов stage2
                mock_stage2.return_value = ("новости", "test_comment")
                
                # Вызываем analyze_message
                category, comment, result_debug = await filter_system.analyze_message(
                    "Bone-02 medical adhesive test", "Test"
                )
                
                # Проверяем что все поля переведены
                logger.info(f"📝 Результат комментария: {comment}")
                logger.info(f"📋 Детальные выводы: {result_debug.detailed_findings}")
                logger.info(f"❓ Отсутствующие доказательства: {result_debug.missing_evidence}")
                
                # Проверяем отсутствие английских фраз
                fields_to_check = [
                    result_debug.detailed_findings,
                    result_debug.contradictions, 
                    result_debug.missing_evidence
                ]
                
                english_keywords = [
                    "evidence", "found", "claims", "bone", "healing", "medical", 
                    "adhesive", "rapid", "supporting", "contradictions"
                ]
                
                for field in fields_to_check:
                    if field:  # Если поле не пустое
                        for keyword in english_keywords:
                            if keyword.lower() in field.lower():
                                logger.error(f"❌ Найдено английское слово '{keyword}' в поле: {field}")
                                assert False, f"Поле содержит английское слово '{keyword}': {field}"
                
                logger.info("✅ Все поля полностью переведены на русский язык")
                
                # Дополнительная проверка комментария через новый метод
                translated_comment = filter_system._build_translated_comment(
                    "unconfirmed", 15, result_debug
                )
                logger.info(f"📝 Переведенный комментарий: {translated_comment}")
                
                # Проверяем что в комментарии нет английских слов
                for keyword in english_keywords:
                    if keyword.lower() in translated_comment.lower():
                        logger.error(f"❌ Найдено английское слово '{keyword}' в комментарии: {translated_comment}")
                        assert False, f"Комментарий содержит английское слово '{keyword}': {translated_comment}"
                
                logger.info("✅ Комментарий полностью на русском языке")
                
    finally:
        Config.TRANSLATE_TO_RUSSIAN = original_translate

async def run_all_tests():
    """Запуск всех тестов"""
    logger.info("🚀 Запускаем тесты перевода и форматирования...")
    
    tests = [
        test_translation_functionality,
        test_formatting_with_all_fields,
        test_formatting_with_missing_fields,
        test_integration_mock_fact_check,
        test_comment_full_translation
    ]
    
    for test_func in tests:
        try:
            await test_func()
            logger.info(f"✅ {test_func.__name__} прошел успешно")
        except Exception as e:
            logger.error(f"❌ {test_func.__name__} провалился: {e}")
            raise
        
        await asyncio.sleep(0.5)  # Небольшая пауза между тестами
    
    logger.info("\n🎉 Все тесты перевода и форматирования прошли успешно!")

if __name__ == "__main__":
    asyncio.run(run_all_tests())