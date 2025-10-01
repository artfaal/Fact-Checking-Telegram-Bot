import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID', 0))
    TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH', '')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    TARGET_CHAT_ID = int(os.getenv('TARGET_CHAT_ID', 0))
    
    # Настройки фактчекинга
    GPT_MODEL = os.getenv('GPT_MODEL', 'gpt-5')
    FACT_CHECK_MODE = os.getenv('FACT_CHECK_MODE', 'smart')  # smart, strict, permissive
    MAX_SOURCE_DOMAINS = int(os.getenv('MAX_SOURCE_DOMAINS', 20))
    ENABLE_AUTO_SOURCES = os.getenv('ENABLE_AUTO_SOURCES', 'true').lower() == 'true'
    
    @staticmethod
    def get_channels() -> List[str]:
        channels_str = os.getenv('CHANNELS', '')
        return [ch.strip() for ch in channels_str.split(',') if ch.strip()]
    
    @classmethod
    def validate(cls):
        errors = []
        if not cls.TELEGRAM_API_ID:
            errors.append("TELEGRAM_API_ID не установлен")
        if not cls.TELEGRAM_API_HASH:
            errors.append("TELEGRAM_API_HASH не установлен")
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN не установлен")
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY не установлен")
        if not cls.TARGET_CHAT_ID:
            errors.append("TARGET_CHAT_ID не установлен")
        if not cls.get_channels():
            errors.append("CHANNELS не установлены")
        
        if errors:
            raise ValueError(f"Ошибки конфигурации: {', '.join(errors)}")
        return True