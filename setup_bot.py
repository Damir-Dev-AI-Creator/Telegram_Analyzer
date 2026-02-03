#!/usr/bin/env python3
"""
Простой скрипт для первой настройки бота
Создает минимальный .env файл с BOT_TOKEN
"""

import os
from pathlib import Path


def setup_bot():
    """Первая настройка бота"""
    print("=" * 60)
    print("🤖 Telegram Analyzer Bot - Setup")
    print("=" * 60)
    print()

    # Проверить существование .env
    env_path = Path("data/.env") if Path("data").exists() else Path(".env")

    if env_path.exists():
        print(f"✅ Файл {env_path} уже существует")

        # Проверить наличие BOT_TOKEN
        with open(env_path, 'r') as f:
            content = f.read()
            if 'BOT_TOKEN=' in content and 'your_bot_token' not in content.lower():
                print("✅ BOT_TOKEN настроен")
                print()
                print("Готово! Запустите бота:")
                print("  python main.py --bot")
                return
            else:
                print("⚠️ BOT_TOKEN не настроен в .env файле")
    else:
        print(f"📝 Создаю {env_path}...")

    print()
    print("Для запуска бота нужен только BOT_TOKEN")
    print()
    print("🔑 Как получить Bot Token:")
    print("1. Откройте Telegram")
    print("2. Напишите @BotFather")
    print("3. Отправьте команду /newbot")
    print("4. Следуйте инструкциям")
    print("5. Скопируйте токен (начинается с цифр и содержит двоеточие)")
    print()
    print("Пример токена: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    print()

    bot_token = input("Введите BOT_TOKEN: ").strip()

    if not bot_token:
        print("❌ Токен не может быть пустым")
        return

    # Базовая валидация формата токена
    if ':' not in bot_token or len(bot_token) < 20:
        print("⚠️ Предупреждение: токен выглядит некорректно")
        confirm = input("Продолжить? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Отменено")
            return

    # Создать data/ если не существует
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Создать .env файл
    env_content = f"""# ===========================================
# Telegram Analyzer Bot Configuration
# ===========================================

# REQUIRED: Telegram Bot Token
BOT_TOKEN={bot_token}

# ===========================================
# Multi-User Mode
# ===========================================
# Все остальные настройки теперь per-user:
# Пользователи настраивают свои credentials через /setup
#
# - Telegram API (API_ID, API_HASH, PHONE)
# - Claude API key
# - Session data (encrypted in database)
"""

    env_path.write_text(env_content, encoding='utf-8')

    print()
    print("=" * 60)
    print("✅ Настройка завершена!")
    print("=" * 60)
    print()
    print(f"📁 Создан файл: {env_path}")
    print()
    print("🚀 Запустите бота:")
    print("  python main.py --bot")
    print()
    print("📱 После запуска откройте бота в Telegram и отправьте /start")
    print()


if __name__ == "__main__":
    try:
        setup_bot()
    except KeyboardInterrupt:
        print("\n\n❌ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
