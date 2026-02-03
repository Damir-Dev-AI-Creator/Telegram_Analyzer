#!/usr/bin/env python3
"""
Скрипт для экспорта session string из существующего Telethon клиента
Используйте если уже авторизованы в Telethon на другом устройстве
"""

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# Ваши данные из https://my.telegram.org
API_ID = 12345  # Замените
API_HASH = "your_api_hash"  # Замените
PHONE = "+1234567890"  # Замените

# Создать клиент с StringSession
with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("=" * 60)
    print("📱 Экспорт Telegram Session String")
    print("=" * 60)
    print()

    # Авторизация (можно использовать QR или код)
    client.start(phone=PHONE)

    # Получить session string
    session_string = client.session.save()

    print("✅ Авторизация успешна!")
    print()
    print("📋 Ваш Session String:")
    print("=" * 60)
    print(session_string)
    print("=" * 60)
    print()
    print("💾 Сохраните этот string в безопасном месте!")
    print("   Используйте его в боте через /setup")
    print()
    print("⚠️  ВАЖНО: Никому не показывайте session string!")
    print("   Это даёт полный доступ к вашему аккаунту!")
