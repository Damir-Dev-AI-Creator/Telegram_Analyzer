# telegram.py
"""Модуль для экспорта сообщений из Telegram (multi-user version)"""

import csv
import asyncio
import re
import logging
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import os
from typing import Optional

from core.db_manager import get_db_manager
from core.config import API_ID, API_HASH, PHONE, SESSION_FILE

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


async def export_telegram_csv(
    user_id: int,
    chat: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10000
) -> str:
    """
    Экспорт сообщений из Telegram чата в CSV файл (per-user version)

    Args:
        user_id: Telegram User ID владельца
        chat: ID или username чата
        start_date: Дата начала в формате ДД-ММ-ГГГГ (опционально)
        end_date: Дата конца в формате ДД-ММ-ГГГГ (опционально)
        limit: Максимальное количество сообщений (по умолчанию 10000)

    Returns:
        str: Путь к созданному CSV файлу

    Raises:
        ValueError: Если пользователь не настроен или не авторизован
        Exception: Другие ошибки при экспорте
    """
    db = get_db_manager()

    # Получить данные пользователя из БД
    user = await db.get_user(user_id)

    if not user:
        raise ValueError(f"Пользователь {user_id} не найден в базе данных. Запустите /setup для настройки.")

    if not user.is_configured:
        raise ValueError(f"Пользователь {user_id} не настроен. Запустите /setup для настройки.")

    if not user.is_authorized:
        raise ValueError(f"Пользователь {user_id} не авторизован в Telegram. Запустите /setup для авторизации.")

    # Получить настройки пользователя
    settings = await db.get_user_settings(user_id)

    # Получить расшифрованную сессию
    session_string = await db.get_user_session(user_id)

    if not session_string:
        raise ValueError(f"Сессия пользователя {user_id} не найдена. Запустите /setup для авторизации.")

    logger.info(f"Starting export for user {user_id}, chat: {chat}")

    # Парсинг дат (поддержка двух форматов: ISO и ДД-ММ-ГГГГ)
    parsed_start_date = None
    if start_date:
        try:
            # Попробовать ISO формат (YYYY-MM-DDTHH:MM:SS)
            parsed_start_date = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            try:
                # Попробовать формат ДД-ММ-ГГГГ
                parsed_start_date = datetime.strptime(start_date, '%d-%m-%Y').replace(tzinfo=timezone.utc)
            except ValueError as e:
                raise ValueError(f"Неверный формат даты начала. Используйте ДД-ММ-ГГГГ или ISO формат: {e}")

    parsed_end_date = None
    if end_date:
        try:
            # Попробовать ISO формат
            parsed_end_date = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            try:
                # Попробовать формат ДД-ММ-ГГГГ
                parsed_end_date = datetime.strptime(end_date, '%d-%m-%Y').replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
            except ValueError as e:
                raise ValueError(f"Неверный формат даты конца. Используйте ДД-ММ-ГГГГ или ISO формат: {e}")

    # Создать клиент из сохраненной сессии
    client = TelegramClient(
        StringSession(session_string),
        user.api_id,
        user.api_hash,
        device_model=f"Telegram Analyzer Bot (User {user_id})",
        system_version="Linux",
        app_version="1.0"
    )

    try:
        await client.connect()

        # Проверить авторизацию
        if not await client.is_user_authorized():
            raise ValueError(f"Сессия пользователя {user_id} истекла. Запустите /setup для повторной авторизации.")

        logger.info(f"✅ User {user_id} authorized in Telegram")

        # Получить информацию о чате с обработкой ошибок
        logger.info(f"🔍 Attempting to get entity for chat: {chat} (type: {type(chat).__name__})")

        try:
            entity = await client.get_entity(chat)
            logger.info(f"✅ Successfully got entity: {getattr(entity, 'title', getattr(entity, 'username', 'unknown'))}")
        except ValueError as e:
            error_msg = str(e).lower()
            if "not part of" in error_msg or "cannot get entity" in error_msg:
                raise ValueError(
                    f"❌ Вы не являетесь участником этого чата.\n\n"
                    f"📱 Чат: {chat}\n\n"
                    f"Для экспорта чата необходимо:\n"
                    f"1. Вступить в чат/группу/канал в Telegram\n"
                    f"2. После вступления повторить команду экспорта\n\n"
                    f"💡 Telegram API не позволяет экспортировать чаты, где вы не состоите."
                )
            else:
                raise ValueError(f"Не удалось получить информацию о чате: {e}")
        except Exception as e:
            raise ValueError(f"Ошибка при получении чата: {e}")

        # Определяем имя чата для названия файла
        chat_title = getattr(entity, 'title', getattr(entity, 'username', 'chat'))
        if not chat_title:
            chat_title = "chat"

        # Корректное форматирование имени файла
        s_str = parsed_start_date.strftime('%d-%m-%Y') if parsed_start_date else "start"
        e_str = parsed_end_date.strftime('%d-%m-%Y') if parsed_end_date else "now"
        output_file = f"{clean_filename(chat_title)}_{s_str}_{e_str}.csv"

        logger.info(f"--- Starting export for user {user_id} ---")
        logger.info(f"Chat: {chat_title}")
        logger.info(f"Period: {s_str} - {e_str}")
        logger.info(f"File: {output_file}")

        messages_data = []
        message_count = 0

        # Получить настройки фильтрации из БД
        exclude_user_id = settings.exclude_user_id if settings else 0
        exclude_username = settings.exclude_username if settings else ""

        # Выгрузка сообщений
        async for msg in client.iter_messages(entity, limit=limit, offset_date=parsed_end_date):
            # Проверка на дату начала
            if parsed_start_date and msg.date < parsed_start_date:
                break

            if not msg.message:
                continue

            # Исключение по User ID (из настроек пользователя)
            if exclude_user_id and exclude_user_id != 0 and msg.sender_id == exclude_user_id:
                continue

            sender = "Unknown"
            if msg.sender:
                if hasattr(msg.sender, 'first_name') and msg.sender.first_name:
                    sender = msg.sender.first_name
                    if hasattr(msg.sender, 'last_name') and msg.sender.last_name:
                        sender += f" {msg.sender.last_name}"
                elif hasattr(msg.sender, 'title'):
                    sender = msg.sender.title

            # Исключение по Username (из настроек пользователя)
            if exclude_username and exclude_username.strip() and exclude_username.lower() in sender.lower():
                continue

            clean_text = msg.message.replace('\n', ' ').replace('\r', ' ').strip()

            messages_data.append({
                'Date': msg.date.strftime('%d-%m-%Y %H:%M:%S'),
                'From': sender,
                'Text': clean_text
            })

            message_count += 1
            if message_count % 100 == 0:
                logger.info(f"Processed messages: {message_count}")

        # Создать per-user папку для экспортов
        user_export_folder = os.path.join("data", "users", str(user_id), "exports")
        os.makedirs(user_export_folder, exist_ok=True)
        output_filepath = os.path.join(user_export_folder, output_file)

        fieldnames = ['Date', 'From', 'Text']
        with open(output_filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(messages_data)

        logger.info(f"✅ Export completed: {output_filepath}")
        logger.info(f"📊 Exported messages: {len(messages_data)}")

        # Вернуть полный путь к файлу
        return output_filepath

    except Exception as e:
        logger.error(f"❌ Export error for user {user_id}: {e}", exc_info=True)
        raise
    finally:
        await client.disconnect()

# ==================== LEGACY EXPORT FOR GUI/CONSOLE ====================

async def export_telegram_csv_legacy(
    chat: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10000,
    code_handler=None
) -> str:
    """
    Legacy export function for GUI and console modes (single-user).
    Uses API credentials from .env file instead of database.
    
    Args:
        chat: ID or username of the chat
        start_date: Start date in DD-MM-YYYY format (optional)
        end_date: End date in DD-MM-YYYY format (optional)
        limit: Maximum number of messages (default 10000)
        code_handler: Handler for 2FA codes (optional, deprecated)
    
    Returns:
        str: Path to the created CSV file
    
    Raises:
        ValueError: If API credentials are not configured in .env
        Exception: Other errors during export
    """
    from core.config import get_input_folder, get_output_folder
    
    # Check if API credentials are configured in .env
    if not API_ID or not API_HASH:
        raise ValueError(
            "API credentials not found in .env file.\n"
            "Please add API_ID and API_HASH to your .env file.\n"
            "Get them from: https://my.telegram.org"
        )
    
    logger.info(f"[LEGACY] Starting export for chat: {chat}")
    
    # Parse dates (DD-MM-YYYY format)
    parsed_start_date = None
    if start_date:
        try:
            parsed_start_date = datetime.strptime(start_date, '%d-%m-%Y').replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise ValueError(f"Invalid start date format. Use DD-MM-YYYY: {e}")
    
    parsed_end_date = None
    if end_date:
        try:
            parsed_end_date = datetime.strptime(end_date, '%d-%m-%Y').replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        except ValueError as e:
            raise ValueError(f"Invalid end date format. Use DD-MM-YYYY: {e}")
    
    # Get session file path
    session_path = SESSION_FILE if SESSION_FILE else os.path.join("data", "telegram_session")
    
    # Create Telethon client
    client = TelegramClient(
        session_path,
        API_ID,
        API_HASH,
        device_model="Telegram Analyzer (Legacy)",
        system_version="Windows",
        app_version="1.0"
    )
    
    try:
        await client.connect()
        
        # Check authorization
        if not await client.is_user_authorized():
            if PHONE:
                # Try to authorize with phone
                await client.send_code_request(PHONE)
                logger.warning("[LEGACY] Phone authorization required but not supported in automated mode")
                raise ValueError(
                    "Telegram session expired. Please use bot mode for authorization:\n"
                    "python main.py --bot"
                )
            else:
                raise ValueError(
                    "Not authorized in Telegram. Please use bot mode:\n"
                    "python main.py --bot"
                )
        
        logger.info(f"[LEGACY] ✅ Authorized in Telegram")
        
        # Get chat entity
        logger.info(f"[LEGACY] 🔍 Getting entity for chat: {chat}")
        try:
            entity = await client.get_entity(chat)
            logger.info(f"[LEGACY] ✅ Got entity: {getattr(entity, 'title', getattr(entity, 'username', 'unknown'))}")
        except ValueError as e:
            error_msg = str(e).lower()
            if "not part of" in error_msg or "cannot get entity" in error_msg:
                raise ValueError(
                    f"You are not a member of this chat: {chat}\n"
                    f"Join the chat in Telegram first, then try again."
                )
            else:
                raise ValueError(f"Failed to get chat info: {e}")
        
        # Get chat title for filename
        chat_title = getattr(entity, 'title', getattr(entity, 'username', 'chat'))
        if not chat_title:
            chat_title = "chat"
        
        # Format filename
        s_str = parsed_start_date.strftime('%d-%m-%Y') if parsed_start_date else "start"
        e_str = parsed_end_date.strftime('%d-%m-%Y') if parsed_end_date else "now"
        output_file = f"{clean_filename(chat_title)}_{s_str}_{e_str}.csv"
        
        logger.info(f"[LEGACY] --- Starting export ---")
        logger.info(f"[LEGACY] Chat: {chat_title}")
        logger.info(f"[LEGACY] Period: {s_str} - {e_str}")
        logger.info(f"[LEGACY] File: {output_file}")
        
        messages_data = []
        message_count = 0
        
        # Export messages
        async for msg in client.iter_messages(entity, limit=limit, offset_date=parsed_end_date):
            # Check start date
            if parsed_start_date and msg.date < parsed_start_date:
                break
            
            if not msg.message:
                continue
            
            sender = "Unknown"
            if msg.sender:
                if hasattr(msg.sender, 'first_name') and msg.sender.first_name:
                    sender = msg.sender.first_name
                    if hasattr(msg.sender, 'last_name') and msg.sender.last_name:
                        sender += f" {msg.sender.last_name}"
                elif hasattr(msg.sender, 'title'):
                    sender = msg.sender.title
            
            clean_text = msg.message.replace('\n', ' ').replace('\r', ' ').strip()
            
            messages_data.append({
                'Date': msg.date.strftime('%d-%m-%Y %H:%M:%S'),
                'From': sender,
                'Text': clean_text
            })
            
            message_count += 1
            if message_count % 100 == 0:
                logger.info(f"[LEGACY] Processed messages: {message_count}")
        
        # Save to input_csv folder (legacy behavior)
        input_folder = get_input_folder()
        input_folder.mkdir(parents=True, exist_ok=True)
        output_filepath = os.path.join(str(input_folder), output_file)
        
        fieldnames = ['Date', 'From', 'Text']
        with open(output_filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(messages_data)
        
        logger.info(f"[LEGACY] ✅ Export completed: {output_filepath}")
        logger.info(f"[LEGACY] 📊 Exported messages: {len(messages_data)}")
        
        return output_filepath
    
    except Exception as e:
        logger.error(f"[LEGACY] ❌ Export error: {e}", exc_info=True)
        raise
    finally:
        await client.disconnect()
