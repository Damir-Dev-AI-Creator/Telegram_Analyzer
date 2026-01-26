# bot/handlers/export.py
"""Обработчик команды /export для экспорта чатов (асинхронный)"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
import logging

from core.queue import task_queue, TaskType

logger = logging.getLogger(__name__)

# Создаем router для этого модуля
router = Router()


@router.message(Command("export"))
async def cmd_export(message: Message):
    """
    Обработчик команды /export (асинхронный через очередь)

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

    try:
        # Добавить задачу в очередь
        task_id = await task_queue.add_task(
            task_type=TaskType.EXPORT,
            user_id=message.from_user.id,
            data={
                'chat_id': chat_id,
                'start_date': None,
                'end_date': None,
                'limit': 10000
            }
        )

        # Сразу ответить пользователю
        await message.answer(
            f"✅ <b>Задача создана!</b>\n\n"
            f"🆔 Задача: #{task_id}\n"
            f"📱 Чат: <code>{chat_id}</code>\n"
            f"📅 Период: За все время\n"
            f"📊 Лимит: 10,000 сообщений\n\n"
            f"⏳ Экспорт начнется в течение нескольких секунд.\n"
            f"Я отправлю уведомление когда экспорт завершится."
        )

        logger.info(f"Task #{task_id} created for user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error creating export task: {e}", exc_info=True)

        await message.answer(
            f"❌ <b>Ошибка создания задачи</b>\n\n"
            f"Ошибка: {str(e)}\n\n"
            f"Попробуйте еще раз или обратитесь к администратору."
        )


@router.message(F.text.startswith("/export"))
async def cmd_export_fallback(message: Message):
    """Fallback для неправильного формата команды /export"""
    await message.answer(
        "❌ Неверный формат. Используйте:\n"
        "<code>/export CHAT_ID</code>\n\n"
        "Подробности: /help"
    )
