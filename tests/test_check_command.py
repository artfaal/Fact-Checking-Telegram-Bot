#!/usr/bin/env python3
"""
Тест функции проверки фактов
"""

import asyncio
import logging
import sys
import os

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import Config
from command_handler import CommandHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockMessage:
    """Мок объект для тестирования команды"""
    def __init__(self, text: str, chat_id: int):
        self.text = text
        self.chat = type('Chat', (), {'id': chat_id})()

class MockBot:
    """Мок бота для тестирования"""
    def __init__(self):
        self.messages = []
        
    async def send_message(self, chat_id, text):
        logger.info(f"📤 Отправлено: {text[:100]}...")
        message = type('Message', (), {'id': len(self.messages) + 1})()
        self.messages.append(text)
        return message
        
    async def edit_message_text(self, chat_id, message_id, text):
        logger.info(f"✏️ Отредактировано: {text[:100]}...")
        if self.messages:
            self.messages[-1] = text

async def test_check_command():
    """Тест команды /check"""
    logger.info("🧪 Тестируем команду /check...")
    
    handler = CommandHandler()
    mock_bot = MockBot()
    
    test_cases = [
        {
            "text": "/check Discord объявил новую функцию ИИ-модерации голосовых каналов",
            "description": "Новость о Discord"
        },
        {
            "text": "/check СУПЕР СКИДКА! iPhone за 999 рублей! Только сегодня!",
            "description": "Спам-сообщение"
        },
        {
            "text": "/check",
            "description": "Команда без текста"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        logger.info(f"\n🧪 === ТЕСТ {i}: {case['description']} ===")
        logger.info(f"📝 Команда: {case['text']}")
        
        # Создаем мок сообщения
        mock_message = MockMessage(case['text'], 12345)  # Фиктивный chat_id
        
        try:
            # Тестируем обработку команды
            await handler.handle_check_command(mock_bot, mock_message)
            logger.info(f"✅ Команда обработана успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в тесте {i}: {e}")
        
        await asyncio.sleep(1)  # Пауза между тестами
    
    logger.info("\n✅ Тестирование команд завершено!")

if __name__ == "__main__":
    asyncio.run(test_check_command())