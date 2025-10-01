#!/usr/bin/env python3
"""
Создание авторизованной сессии для мониторинга
"""

import asyncio
from pyrogram import Client
from config import Config

async def create_session():
    """Создает сессию для мониторинга каналов"""
    app = Client(
        "fact_checker_monitor",
        api_id=Config.TELEGRAM_API_ID,
        api_hash=Config.TELEGRAM_API_HASH
    )
    
    print("Создаем сессию для мониторинга каналов...")
    await app.start()
    print("✅ Сессия создана успешно!")
    await app.stop()

if __name__ == "__main__":
    asyncio.run(create_session())