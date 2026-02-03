#!/usr/bin/env python3
"""Тест парсинга chat identifiers без зависимостей"""

import re

def parse_chat_identifier(chat_input: str) -> str:
    """
    Парсит различные форматы идентификаторов чатов
    """
    chat_input = chat_input.strip()

    if not chat_input:
        raise ValueError("Идентификатор чата не может быть пустым")

    # 1. Проверка числового ID (может быть отрицательным для групп/каналов)
    if chat_input.lstrip('-').isdigit():
        print(f"  → Распознан как числовой ID: {chat_input}")
        return chat_input

    # 2. Парсинг ссылок t.me
    # Публичные ссылки: https://t.me/channelname или t.me/channelname
    tme_pattern = r'(?:https?://)?t\.me/([a-zA-Z0-9_]+)'
    match = re.match(tme_pattern, chat_input)
    if match:
        username = match.group(1)
        print(f"  → Распознана публичная ссылка, username: {username}")
        return username  # Возвращаем без @, Telethon работает с обоими форматами

    # 3. Приватные ссылки с + (joinchat)
    # https://t.me/+ABC123xyz или https://t.me/joinchat/ABC123xyz
    private_pattern = r'(?:https?://)?t\.me/(?:\+|joinchat/)([a-zA-Z0-9_-]+)'
    match = re.match(private_pattern, chat_input)
    if match:
        # Для приватных ссылок возвращаем всю ссылку
        print(f"  → Распознана приватная ссылка")
        if chat_input.startswith('http'):
            print(f"  → Возвращаем полную ссылку: {chat_input}")
            return chat_input
        else:
            result = f"https://t.me/+{match.group(1)}"
            print(f"  → Добавляем https://, возвращаем: {result}")
            return result

    # 4. Username с @ или без
    # @channelname или channelname
    username_pattern = r'@?([a-zA-Z0-9_]{5,32})'
    match = re.match(username_pattern, chat_input)
    if match:
        username = match.group(1)
        print(f"  → Распознан username: {username}")
        return username  # Возвращаем без @

    # Если ничего не подошло, вернем как есть и пусть Telethon попробует
    print(f"  → Не распознан, возвращаем как есть: {chat_input}")
    return chat_input


# Тестовые случаи
test_cases = [
    "https://t.me/+3tYaXMo4snplNTUy",
    "https://t.me/telegram",
    "@telegram",
    "telegram",
    "-1001234567890",
    "https://t.me/joinchat/ABC123xyz",
    "t.me/durov",
]

print("=" * 60)
print("🔍 Тестирование парсинга chat identifiers")
print("=" * 60)

for test in test_cases:
    print(f"\nВвод: {test}")
    try:
        result = parse_chat_identifier(test)
        print(f"✓ Результат: {result}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")

print("\n" + "=" * 60)
