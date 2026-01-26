# bot/handlers/export.py
"""Обработчик команды /export для экспорта чатов"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
import logging
import asyncio
import os
from services.telegram import export_telegram_csv
from core.config import EXPORT_FOLDER

logger = logging.getLogger(__name__)

# Создаем router для этого модуля
router = Router()


@router.message(Command("export"))
async def cmd_export(message: Message):
    """
    Обработчик команды /export

    Формат:
        /export CHAT_ID
        /export @username
        /export https://t.me/username

    Примеры:
        /export -1001234567890
        /export @durov
        /export https://t.me/telegram
    """
    # Получить аргументы команды
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "❌ <b>Неверный формат команды</b>\n\n"
            "<b>Использование:</b>\n"
            "<code>/export CHAT_ID</code>\n\n"
            "<b>Примеры:</b>\n"
            "<code>/export -1001234567890</code>\n"
            "<code>/export @channelname</code>\n"
            "<code>/export https://t.me/channelname</code>\n\n"
            "Используйте /help для подробных инструкций."
        )
        return

    chat_id = args[1].strip()

    logger.info(f"User {message.from_user.id} requested export for chat: {chat_id}")

    # Отправить сообщение о начале экспорта
    status_msg = await message.answer(
        f"⏳ <b>Начинаю экспорт...</b>\n\n"
        f"📱 Чат: <code>{chat_id}</code>\n"
        f"📅 Период: За все время\n"
        f"📊 Лимит: 10,000 сообщений\n\n"
        f"Это может занять некоторое время."
    )

    try:
        # Запустить экспорт (синхронно для MVP)
        logger.info(f"Starting export for chat {chat_id}")

        # Вызвать существующую функцию экспорта
        result_filename = await export_telegram_csv(
            chat=chat_id,
            start_date=None,  # За все время
            end_date=None,
            limit=10000
        )

        logger.info(f"Export completed: {result_filename}")

        # Обновить статус
        await status_msg.edit_text(
            f"✅ <b>Экспорт завершен!</b>\n\n"
            f"📱 Чат: <code>{chat_id}</code>\n"
            f"📄 Файл: <code>{result_filename}</code>\n\n"
            f"⏳ Отправляю файл..."
        )

        # Отправить файл пользователю
        file_path = os.path.join(EXPORT_FOLDER, result_filename)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        # Отправить документ
        document = FSInputFile(file_path)
        await message.answer_document(
            document=document,
            caption=(
                f"✅ <b>Экспорт завершен успешно!</b>\n\n"
                f"📱 Чат: <code>{chat_id}</code>\n"
                f"📄 Файл: <code>{result_filename}</code>\n\n"
                f"CSV файл готов к использованию."
            )
        )

        # Удалить статусное сообщение
        await status_msg.delete()

        logger.info(f"File sent successfully to user {message.from_user.id}")

    except ValueError as e:
        # Ошибки валидации (неверный Chat ID, не настроены параметры и т.д.)
        logger.error(f"Validation error during export: {e}")
        await status_msg.edit_text(
            f"❌ <b>Ошибка валидации</b>\n\n"
            f"📱 Чат: <code>{chat_id}</code>\n\n"
            f"Ошибка: {str(e)}\n\n"
            f"Проверьте настройки API_ID, API_HASH, PHONE."
        )

    except FileNotFoundError as e:
        # Файл не найден после экспорта
        logger.error(f"File not found after export: {e}")
        await status_msg.edit_text(
            f"❌ <b>Файл не найден</b>\n\n"
            f"📱 Чат: <code>{chat_id}</code>\n\n"
            f"Экспорт завершился, но файл не найден.\n"
            f"Проверьте папку: <code>{EXPORT_FOLDER}</code>"
        )

    except Exception as e:
        # Любые другие ошибки
        logger.error(f"Error during export: {e}", exc_info=True)

        error_message = str(e)

        # Проверка на частые ошибки
        if "Chat not found" in error_message or "No such peer" in error_message:
            error_text = (
                f"❌ <b>Чат не найден</b>\n\n"
                f"📱 Чат: <code>{chat_id}</code>\n\n"
                f"Возможные причины:\n"
                f"• Неверный Chat ID\n"
                f"• Вы не являетесь участником этого чата\n"
                f"• Чат был удален\n\n"
                f"Используйте /help для инструкций по поиску Chat ID."
            )
        elif "API_ID" in error_message or "API_HASH" in error_message or "PHONE" in error_message:
            error_text = (
                f"❌ <b>Не настроены параметры</b>\n\n"
                f"Необходимо настроить:\n"
                f"• API_ID\n"
                f"• API_HASH\n"
                f"• PHONE\n\n"
                f"Добавьте их в файл .env"
            )
        else:
            error_text = (
                f"❌ <b>Ошибка экспорта</b>\n\n"
                f"📱 Чат: <code>{chat_id}</code>\n\n"
                f"Ошибка: {error_message}\n\n"
                f"Попробуйте еще раз или проверьте логи."
            )

        await status_msg.edit_text(error_text)


@router.message(F.text.startswith("/export"))
async def cmd_export_fallback(message: Message):
    """Fallback для неправильного формата команды /export"""
    await message.answer(
        "❌ Неверный формат. Используйте:\n"
        "<code>/export CHAT_ID</code>\n\n"
        "Подробности: /help"
    )
