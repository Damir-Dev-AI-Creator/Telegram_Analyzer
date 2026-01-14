# telegram.py
"""Модуль для экспорта сообщений из Telegram"""

import csv
import asyncio
import re
import logging
from core.config import API_ID, API_HASH, PHONE, EXCLUDE_USER_ID, EXCLUDE_USERNAME, EXPORT_FOLDER, SESSION_PATH
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

    if not PHONE or PHONE.strip() == "":
        raise ValueError("PHONE не настроен. Откройте настройки и введите номер телефона.")

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

    # Функции для авторизации
    async def code_callback():
        """Callback для получения кода"""
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
        """Callback для получения пароля 2FA"""
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
        # ИСПРАВЛЕНО: правильное использование параметра password
        await client.start(
            phone=PHONE,
            code_callback=code_callback,
            password=password_callback  # ✅ ИСПРАВЛЕНО: было password_callback без скобок
        )

        logger.info("✅ Успешная авторизация в Telegram")

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
        entity = await client.get_entity(chat)

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


if __name__ == "__main__":
    # Тестовый запуск
    asyncio.run(export_telegram_csv("@ysellchat"))