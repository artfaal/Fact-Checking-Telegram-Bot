#!/usr/bin/env python3
"""
Тестирование конфигурации
"""

import os
import sys
import logging

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_config():
    """Тест конфигурации"""
    logger.info("🧪 Тестируем конфигурацию...")
    
    try:
        # Проверяем что конфигурация загружается
        logger.info(f"📊 Модель GPT: {Config.GPT_MODEL}")
        logger.info(f"🎯 Режим фактчекинга: {Config.FACT_CHECK_MODE}")
        logger.info(f"🔧 Отладочный режим: {Config.DEBUG_MODE}")
        logger.info(f"📺 Показывать все сообщения: {Config.SHOW_ALL_MESSAGES}")
        logger.info(f"📤 Отправлять debug info: {Config.SEND_DEBUG_INFO}")
        logger.info(f"🌐 Максимум источников: {Config.MAX_SOURCE_DOMAINS}")
        
        # Проверяем валидацию
        Config.validate()
        logger.info("✅ Конфигурация валидна")
        
        # Проверяем загрузку каналов
        channels = Config.get_channels()
        logger.info(f"📡 Каналы для мониторинга: {channels}")
        
        logger.info("✅ Тест конфигурации прошел успешно")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования конфигурации: {e}")
        return False

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)