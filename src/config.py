import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID', 0))
    TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH', '')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # Настройки фактчекинга
    GPT_MODEL = os.getenv('GPT_MODEL', 'gpt-5')
    FACT_CHECK_MODEL = os.getenv('FACT_CHECK_MODEL', 'gpt-4o')
    WEB_SEARCH_EFFORT = os.getenv('WEB_SEARCH_EFFORT', 'medium')
    MAX_SOURCE_DOMAINS = int(os.getenv('MAX_SOURCE_DOMAINS', 20))
    STAGE2_INITIAL_DOMAIN_LIMIT = int(os.getenv('STAGE2_INITIAL_DOMAIN_LIMIT', 8))
    STAGE2_RETRY_DOMAIN_LIMIT = int(os.getenv('STAGE2_RETRY_DOMAIN_LIMIT', 5))
    FACT_CHECK_TIMEOUT = float(os.getenv('FACT_CHECK_TIMEOUT', 45))
    
    # Token limits
    STAGE1_MAX_TOKENS = int(os.getenv('STAGE1_MAX_TOKENS', 1500))
    STAGE2_MAX_TOKENS = int(os.getenv('STAGE2_MAX_TOKENS', 2000))
    
    # Настройки отладки
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    SEND_DEBUG_INFO = os.getenv('SEND_DEBUG_INFO', 'false').lower() == 'true'
    
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
        
        if errors:
            raise ValueError(f"Ошибки конфигурации: {', '.join(errors)}")
        return True
