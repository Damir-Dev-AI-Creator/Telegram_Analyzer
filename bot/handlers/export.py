# bot/handlers/export.py
"""Обработчик команды /export для экспорта чатов (асинхронный)"""

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import logging

from core.queue import task_queue, TaskType
from core.chat_utils import parse_chat_identifier, get_chat_help_text, format_chat_identifier_for_display
from bot.states.command_states import ExportStates

logger = logging.getLogger(__name__)

# Создаем router для этого модуля
router = Router()


@router.message(Command("export"))
async def cmd_export(message: Message, state: FSMContext):
    """
    Обработчик команды /export (асинхронный через очередь)

    Поддерживает два режима:
    1. С аргументом: /export https://t.me/chat - выполняется сразу
    2. Без аргумента: /export - бот просит отправить ссылку следующим сообщением

    Примеры:
        /export -1001234567890
        /export @durov
        /export https://t.me/telegram
    """
    # Получить аргументы команды
    args = message.text.split(maxsplit=1)

    # Режим 1: Команда с аргументом - выполнить сразу
    if len(args) >= 2:
        chat_input = args[1].strip()
        await _process_export(message, state, chat_input)
        return

    # Режим 2: Команда без аргумента - перейти в режим ожидания
    await state.set_state(ExportStates.waiting_chat_link)
    await message.answer(
        "📊 <b>Экспорт чата</b>\n\n"
        "Отправьте мне ссылку на чат, username или ID следующим сообщением:\n\n"
        f"{get_chat_help_text()}\n\n"
        "Или используйте /cancel для отмены."
    )


@router.message(ExportStates.waiting_chat_link)
async def process_export_chat_link(message: Message, state: FSMContext):
    """Обработка ссылки/ID чата после команды /export"""

    # Проверка на команду отмены
    if message.text and message.text.startswith('/cancel'):
        await state.clear()
        await message.answer("❌ Экспорт отменен.")
        return

    chat_input = message.text.strip() if message.text else ""

    if not chat_input:
        await message.answer(
            "❌ Пожалуйста, отправьте ссылку на чат, username или ID.\n"
            "Или используйте /cancel для отмены."
        )
        return

    await _process_export(message, state, chat_input)


async def _process_export(message: Message, state: FSMContext, chat_input: str):
    """
    Общая функция обработки экспорта

    Args:
        message: Сообщение от пользователя
        state: FSM контекст
        chat_input: Идентификатор чата (ссылка, username или ID)
    """
    # Парсинг и валидация идентификатора чата
    try:
        chat_id = parse_chat_identifier(chat_input)
    except ValueError as e:
        await message.answer(
            f"❌ <b>Неверный формат идентификатора чата</b>\n\n"
            f"Ошибка: {str(e)}\n\n"
            f"{get_chat_help_text()}\n\n"
            "Попробуйте еще раз или используйте /cancel для отмены."
        )
        return

    # Очистить состояние
    await state.clear()

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
        display_chat = format_chat_identifier_for_display(chat_input)

        await message.answer(
            f"✅ <b>Задача создана!</b>\n\n"
            f"🆔 Задача: #{task_id}\n"
            f"📱 Чат: <code>{display_chat}</code>\n"
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
        "❌ <b>Неверный формат команды</b>\n\n"
        "<b>Использование:</b>\n"
        "<code>/export CHAT</code>\n\n"
        f"{get_chat_help_text()}\n\n"
        "Подробности: /help"
    )
