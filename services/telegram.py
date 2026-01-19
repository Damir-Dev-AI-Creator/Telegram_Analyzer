# telegram.py
"""Модуль для экспорта сообщений из Telegram (MTProto API - полный функционал)"""

import csv
import asyncio
import re
import logging
from core.config import (
    API_ID, API_HASH, PHONE, BOT_TOKEN, USE_MTPROTO,
    EXCLUDE_USER_ID, EXCLUDE_USERNAME, EXPORT_FOLDER, SESSION_PATH
)
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DAYS_RU = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье"
}


def clean_filename(name):
    """Очистка имени чата для использования в названии файла"""
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")


def parse_chat_identifier(chat_input: str) -> str:
    """
    Парсинг идентификатора чата из различных форматов

    Поддерживаемые форматы:
    - https://t.me/username
    - t.me/username
    - @username
    - username
    - -1001234567890 (ID супергруппы)
    - 1234567890 (ID канала)

    Returns:
        str: Очищенный идентификатор (@username или ID)
    """
    chat_input = chat_input.strip()

    # Если это URL
    if 't.me/' in chat_input or 'telegram.me/' in chat_input:
        # Извлекаем username из URL
        # https://t.me/test_analyzer -> test_analyzer
        # https://t.me/joinchat/ABC123 -> joinchat/ABC123 (приглашение)
        match = re.search(r't(?:elegram)?\.me/([a-zA-Z0-9_/]+)', chat_input)
        if match:
            username = match.group(1)
            # Если это invite link
            if username.startswith('joinchat/') or username.startswith('+'):
                return chat_input  # Возвращаем полную ссылку для invite
            # Добавляем @ если это username
            if not username.startswith('-') and not username.isdigit():
                return f"@{username}"
            return username

    # Если это уже username с @
    if chat_input.startswith('@'):
        return chat_input

    # Если это числовой ID (с минусом или без)
    if chat_input.lstrip('-').isdigit():
        return int(chat_input)

    # Если это просто username без @
    if re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,}$', chat_input):
        return f"@{chat_input}"

    # Возвращаем как есть
    return chat_input


async def export_telegram_csv(chat: str, start_date: str = None, end_date: str = None, limit: int = 10000,
                              code_handler=None):
    """
    Экспорт сообщений из Telegram чата в CSV файл

    Args:
        chat: ID или username чата
        start_date: Дата начала в формате ДД-ММ-ГГГГ
        end_date: Дата конца в формате ДД-ММ-ГГГГ
        limit: Максимальное количество сообщений
        code_handler: Обработчик для получения кода авторизации (опционально)
    """

    # Проверка наличия необходимых параметров
    if not API_ID or API_ID == 0:
        raise ValueError("API_ID не настроен. Откройте настройки и введите API_ID.")

    if not API_HASH or API_HASH.strip() == "":
        raise ValueError("API_HASH не настроен. Откройте настройки и введите API_HASH.")

    # Проверка наличия хотя бы одного: PHONE или BOT_TOKEN
    has_phone = PHONE and PHONE.strip() != ""
    has_bot_token = BOT_TOKEN and BOT_TOKEN.strip() != ""

    if not has_phone and not has_bot_token:
        raise ValueError("Не настроен способ авторизации. Откройте настройки и введите:\n"
                        "- Bot Token (для работы через бота) ИЛИ\n"
                        "- Номер телефона (для User Account режима)")

    # Парсинг дат
    parsed_start_date = None
    if start_date:
        try:
            parsed_start_date = datetime.strptime(start_date, '%d-%m-%Y').replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise ValueError(f"Неверный формат даты начала. Используйте ДД-ММ-ГГГГ: {e}")

    parsed_end_date = None
    if end_date:
        try:
            parsed_end_date = datetime.strptime(end_date, '%d-%m-%Y').replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        except ValueError as e:
            raise ValueError(f"Неверный формат даты конца. Используйте ДД-ММ-ГГГГ: {e}")

    client = TelegramClient(str(SESSION_PATH), API_ID, API_HASH)

    # Функции для авторизации (только для PHONE режима)
    async def code_callback():
        """Callback для получения кода (только для User Account)"""
        if not has_phone:
            return None  # Не нужно для бота
        if code_handler:
            try:
                code = await code_handler.get_code(PHONE)
                return code
            except Exception as e:
                logger.error(f"Ошибка получения кода: {e}")
                raise
        else:
            return input('Введите код подтверждения: ')

    async def password_callback():
        """Callback для получения пароля 2FA (только для User Account)"""
        if not has_phone:
            return None  # Не нужно для бота
        if code_handler:
            try:
                password = await code_handler.get_password()
                return password
            except Exception as e:
                logger.error(f"Ошибка получения пароля: {e}")
                raise
        else:
            return input('Введите пароль двухфакторной аутентификации: ')

    try:
        # Авторизация: либо через BOT_TOKEN, либо через PHONE
        if has_bot_token and not has_phone:
            # Режим бота: используем bot_token
            await client.start(bot_token=BOT_TOKEN)
            logger.info("✅ Успешная авторизация в Telegram через Bot Token")
        else:
            # Режим User Account: используем phone
            await client.start(
                phone=PHONE,
                code_callback=code_callback,
                password=password_callback
            )
            logger.info("✅ Успешная авторизация в Telegram через номер телефона")

        # Закрываем диалог авторизации после успешного входа
        if code_handler:
            code_handler.close()

    except SessionPasswordNeededError:
        logger.warning("Требуется пароль двухфакторной аутентификации")
        password = await password_callback()
        await client.sign_in(password=password)
        if code_handler:
            code_handler.close()

    except Exception as e:
        error_msg = f"Ошибка подключения к Telegram: {e}"
        logger.error(error_msg)
        if code_handler:
            code_handler.show_error(error_msg)
        raise Exception(error_msg)

    try:
        # Парсим идентификатор чата
        parsed_chat = parse_chat_identifier(chat)
        logger.info(f"Парсинг чата: '{chat}' -> '{parsed_chat}'")

        try:
            entity = await client.get_entity(parsed_chat)
        except Exception as e:
            error_details = (
                f"Не удалось найти чат: {parsed_chat}\n\n"
                f"Возможные причины:\n"
                f"1. Если используете BOT - добавьте бота в канал как админа\n"
                f"2. Если канал приватный - вы должны быть участником\n"
                f"3. Проверьте правильность ссылки/username\n\n"
                f"Исходная ссылка: {chat}\n"
                f"Распознано как: {parsed_chat}\n"
                f"Ошибка: {str(e)}"
            )
            logger.error(error_details)
            raise ValueError(error_details)

        # Определяем имя чата для названия файла
        chat_title = getattr(entity, 'title', getattr(entity, 'username', 'chat'))
        if not chat_title:
            chat_title = "chat"

        # Корректное форматирование имени файла
        s_str = parsed_start_date.strftime('%d-%m-%Y') if parsed_start_date else "start"
        e_str = parsed_end_date.strftime('%d-%m-%Y') if parsed_end_date else "now"
        output_file = f"{clean_filename(chat_title)}_{s_str}_{e_str}.csv"

        logger.info(f"--- Запуск выгрузки ---")
        logger.info(f"Чат: {chat_title}")
        logger.info(f"Период: {s_str} - {e_str}")
        logger.info(f"Файл: {output_file}")

        messages_data = []
        message_count = 0

        # Выгрузка сообщений
        async for msg in client.iter_messages(entity, limit=limit, offset_date=parsed_end_date):
            # Проверка на дату начала
            if parsed_start_date and msg.date < parsed_start_date:
                break

            if not msg.message:
                continue

            # Исключение по User ID
            if EXCLUDE_USER_ID and EXCLUDE_USER_ID != 0 and msg.sender_id == EXCLUDE_USER_ID:
                continue

            sender = "Unknown"
            if msg.sender:
                if hasattr(msg.sender, 'first_name') and msg.sender.first_name:
                    sender = msg.sender.first_name
                    if hasattr(msg.sender, 'last_name') and msg.sender.last_name:
                        sender += f" {msg.sender.last_name}"
                elif hasattr(msg.sender, 'title'):
                    sender = msg.sender.title

            # Исключение по Username
            if EXCLUDE_USERNAME and EXCLUDE_USERNAME.strip() and EXCLUDE_USERNAME.lower() in sender.lower():
                continue

            clean_text = msg.message.replace('\n', ' ').replace('\r', ' ').strip()

            messages_data.append({
                'Date': msg.date.strftime('%d-%m-%Y %H:%M:%S'),
                'From': sender,
                'Text': clean_text
            })

            message_count += 1
            if message_count % 100 == 0:
                logger.info(f"Обработано сообщений: {message_count}")

        # Сохранение в CSV
        os.makedirs(EXPORT_FOLDER, exist_ok=True)
        output_filepath = os.path.join(EXPORT_FOLDER, output_file)

        fieldnames = ['Date', 'From', 'Text']
        with open(output_filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(messages_data)

        logger.info(f"✅ Экспорт завершен: {output_filepath}")
        logger.info(f"📊 Экспортировано сообщений: {len(messages_data)}")
        return output_file

    except Exception as e:
        logger.error(f"❌ Ошибка при экспорте: {e}")
        raise
    finally:
        await client.disconnect()


async def get_user_chats():
    """
    Получить список чатов пользователя (MTProto API + User Account)

    ⚠️ ОГРАНИЧЕНИЕ TELEGRAM API:
    - Боты НЕ МОГУТ получать список своих чатов (GetDialogsRequest запрещен)
    - Эта функция работает ТОЛЬКО с User Account (PHONE), НЕ с ботами!

    Для работы требуется:
    - API_ID, API_HASH
    - PHONE (номер телефона)

    Returns:
        List[dict]: Список чатов с информацией

    Raises:
        ValueError: Если используется BOT_TOKEN вместо PHONE
    """
    if not API_ID or API_ID == 0:
        raise ValueError("API_ID не настроен")

    if not API_HASH or API_HASH.strip() == "":
        raise ValueError("API_HASH не настроен")

    # Проверка: работает ТОЛЬКО с User Account
    if BOT_TOKEN and not PHONE:
        raise ValueError(
            "⚠️ ОГРАНИЧЕНИЕ API\n\n"
            "Боты НЕ МОГУТ получать список чатов!\n"
            "Telegram запрещает метод GetDialogsRequest для ботов.\n\n"
            "Решения:\n"
            "1. Используйте User Bot (укажите PHONE в настройках)\n"
            "2. Или вводите chat_id/username вручную"
        )

    if not PHONE or PHONE.strip() == "":
        raise ValueError("PHONE не настроен. Эта функция работает только с User Account (номер телефона).")

    client = TelegramClient(str(SESSION_PATH), API_ID, API_HASH)

    try:
        # Авторизация как пользователь (User Bot)
        await client.start(phone=PHONE)
        logger.info("✅ User Account авторизован (MTProto)")

        chats = []

        # Получение списка диалогов (работает только для User Account!)
        async for dialog in client.iter_dialogs():
            # Фильтруем только группы и каналы
            if dialog.is_group or dialog.is_channel:
                try:
                    # Проверяем права
                    permissions = await client.get_permissions(dialog.entity, 'me')

                    chat_info = {
                        'id': dialog.id,
                        'title': dialog.title,
                        'type': 'channel' if dialog.is_channel else 'group',
                        'username': getattr(dialog.entity, 'username', None),
                        'is_admin': permissions.is_admin,
                        'can_read_history': True
                    }

                    chats.append(chat_info)
                    logger.info(f"Найден чат: {chat_info['title']} (admin: {chat_info['is_admin']})")

                except Exception as e:
                    logger.warning(f"Не удалось получить информацию о чате {dialog.title}: {e}")

        logger.info(f"📋 Найдено чатов: {len(chats)}")
        return chats

    except Exception as e:
        logger.error(f"❌ Ошибка получения списка чатов: {e}")
        raise
    finally:
        await client.disconnect()


async def export_with_mode_detection(chat: str, start_date: str = None, end_date: str = None,
                                     limit: int = 10000, code_handler=None):
    """
    Универсальная функция экспорта с автоматическим выбором режима

    Выбирает MTProto или HTTP Bot API в зависимости от конфигурации

    Args:
        chat: ID или username чата
        start_date: Дата начала (работает только в MTProto)
        end_date: Дата конца (работает только в MTProto)
        limit: Максимальное количество сообщений
        code_handler: Обработчик для получения кода авторизации (только MTProto)

    Returns:
        str: Имя созданного файла
    """
    if USE_MTPROTO:
        logger.info("🚀 Используется MTProto API (полный функционал)")
        return await export_telegram_csv(chat, start_date, end_date, limit, code_handler)
    else:
        logger.info("🤖 Используется HTTP Bot API (только новые сообщения)")

        if start_date or end_date:
            logger.warning("⚠️  Даты игнорируются в HTTP Bot API режиме (история недоступна)")

        # Парсим идентификатор чата (поддержка URL)
        parsed_chat = parse_chat_identifier(chat)
        logger.info(f"HTTP Bot API: парсинг '{chat}' -> '{parsed_chat}'")

        # Импорт здесь, чтобы избежать проблем если библиотека не установлена
        from services.telegram_bot import export_telegram_bot_mode

        # HTTP Bot API может работать с @username для публичных каналов
        # или с числовым ID (для приватных или если бот добавлен)
        return await export_telegram_bot_mode(parsed_chat, limit)


if __name__ == "__main__":
    # Тестовый запуск
    asyncio.run(export_telegram_csv("@ysellchat"))