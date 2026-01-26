"""
Утилиты для работы с chat identifiers (ID, username, ссылки)
"""

import re
from typing import Union


def parse_chat_identifier(chat_input: str) -> str:
    """
    Парсит различные форматы идентификаторов чатов

    Поддерживаемые форматы:
    - Числовой ID: -1001234567890
    - Username: @channelname или channelname
    - Публичная ссылка: https://t.me/channelname
    - Приватная ссылка: https://t.me/+ABC123xyz (joinchat)
    - Ссылка t.me: t.me/channelname

    Args:
        chat_input: Идентификатор чата в любом формате

    Returns:
        Очищенный идентификатор для использования с Telethon

    Raises:
        ValueError: Если формат не распознан
    """
    chat_input = chat_input.strip()

    if not chat_input:
        raise ValueError("Идентификатор чата не может быть пустым")

    # 1. Проверка числового ID (может быть отрицательным для групп/каналов)
    if chat_input.lstrip('-').isdigit():
        return chat_input

    # 2. Парсинг ссылок t.me
    # Публичные ссылки: https://t.me/channelname или t.me/channelname
    tme_pattern = r'(?:https?://)?t\.me/([a-zA-Z0-9_]+)'
    match = re.match(tme_pattern, chat_input)
    if match:
        username = match.group(1)
        return username  # Возвращаем без @, Telethon работает с обоими форматами

    # 3. Приватные ссылки с + (joinchat)
    # https://t.me/+ABC123xyz или https://t.me/joinchat/ABC123xyz
    private_pattern = r'(?:https?://)?t\.me/(?:\+|joinchat/)([a-zA-Z0-9_-]+)'
    match = re.match(private_pattern, chat_input)
    if match:
        # Для приватных ссылок возвращаем всю ссылку
        if chat_input.startswith('http'):
            return chat_input
        else:
            return f"https://t.me/+{match.group(1)}"

    # 4. Username с @ или без
    # @channelname или channelname
    username_pattern = r'@?([a-zA-Z0-9_]{5,32})'
    match = re.match(username_pattern, chat_input)
    if match:
        username = match.group(1)
        return username  # Возвращаем без @

    # Если ничего не подошло, вернем как есть и пусть Telethon попробует
    return chat_input


def format_chat_identifier_for_display(chat_input: str) -> str:
    """
    Форматирует идентификатор чата для отображения пользователю

    Args:
        chat_input: Идентификатор чата

    Returns:
        Отформатированная строка для отображения
    """
    chat_input = chat_input.strip()

    # Если это числовой ID, оставить как есть
    if chat_input.lstrip('-').isdigit():
        return f"ID: {chat_input}"

    # Если это ссылка, показать полную ссылку
    if 't.me/' in chat_input:
        return chat_input

    # Если username, добавить @
    if not chat_input.startswith('@'):
        return f"@{chat_input}"

    return chat_input


def get_chat_help_text() -> str:
    """
    Возвращает справочный текст о форматах идентификаторов чатов

    Returns:
        Форматированный HTML текст со справкой
    """
    return """<b>📱 Форматы идентификаторов чатов:</b>

<b>1. Ссылка на чат (рекомендуется):</b>
   <code>https://t.me/channelname</code>
   <code>t.me/channelname</code>

<b>2. Username:</b>
   <code>@channelname</code>
   <code>channelname</code>

<b>3. Числовой ID:</b>
   <code>-1001234567890</code>

<b>4. Приватные чаты:</b>
   <code>https://t.me/+ABC123xyz</code>
   <code>https://t.me/joinchat/ABC123xyz</code>

<b>💡 Как получить ссылку на чат:</b>
1. Откройте чат в Telegram
2. Нажмите на название чата вверху
3. Нажмите "Share" или "Поделиться"
4. Скопируйте ссылку
5. Вставьте её в команду"""


# Примеры для тестирования
if __name__ == "__main__":
    test_cases = [
        "-1001234567890",
        "@channelname",
        "channelname",
        "https://t.me/channelname",
        "t.me/channelname",
        "https://t.me/+ABC123xyz",
        "https://t.me/joinchat/ABC123xyz",
    ]

    print("=== Тестирование парсинга chat identifiers ===\n")
    for test in test_cases:
        try:
            result = parse_chat_identifier(test)
            display = format_chat_identifier_for_display(test)
            print(f"Ввод:    {test}")
            print(f"Парсинг: {result}")
            print(f"Дисплей: {display}")
            print()
        except ValueError as e:
            print(f"Ввод:  {test}")
            print(f"Ошибка: {e}\n")
