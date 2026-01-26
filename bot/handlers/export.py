# bot/handlers/export.py
"""Обработчик команды /export для экспорта чатов (асинхронный)"""

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import logging
from datetime import datetime, timedelta

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

    # Сохранить информацию о чате в FSM
    await state.update_data(chat_id=chat_id, chat_input=chat_input)

    # Показать меню выбора лимита сообщений
    await _show_limit_menu(message, state)


async def _show_limit_menu(message: Message, state: FSMContext):
    """Показать меню выбора лимита сообщений"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📭 Все сообщения", callback_data="limit_all"),
        ],
        [
            InlineKeyboardButton(text="💯 Последние 100", callback_data="limit_100"),
            InlineKeyboardButton(text="1️⃣K Последние 1,000", callback_data="limit_1000"),
        ],
        [
            InlineKeyboardButton(text="🔟K Последние 10,000", callback_data="limit_10000"),
            InlineKeyboardButton(text="5️⃣0K Последние 50,000", callback_data="limit_50000"),
        ],
        [
            InlineKeyboardButton(text="✏️ Кастомный лимит", callback_data="limit_custom"),
        ]
    ])

    await state.set_state(ExportStates.waiting_limit_choice)
    await message.answer(
        "📊 <b>Настройка экспорта - Шаг 1/2</b>\n\n"
        "Сколько сообщений экспортировать?",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("limit_"), ExportStates.waiting_limit_choice)
async def process_limit_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора лимита сообщений"""
    await callback.answer()

    choice = callback.data.replace("limit_", "")

    if choice == "custom":
        await state.set_state(ExportStates.waiting_custom_limit)
        await callback.message.edit_text(
            "📊 <b>Кастомный лимит</b>\n\n"
            "Введите количество сообщений для экспорта (число от 1 до 1,000,000):\n\n"
            "Или используйте /cancel для отмены."
        )
        return

    # Определить лимит
    limit_map = {
        "all": None,  # Все сообщения
        "100": 100,
        "1000": 1000,
        "10000": 10000,
        "50000": 50000
    }

    limit = limit_map.get(choice)
    await state.update_data(limit=limit)

    # Показать меню выбора периода
    await _show_date_menu(callback.message, state)


@router.message(ExportStates.waiting_custom_limit)
async def process_custom_limit(message: Message, state: FSMContext):
    """Обработка ввода кастомного лимита"""
    if message.text and message.text.startswith('/cancel'):
        await state.clear()
        await message.answer("❌ Экспорт отменен.")
        return

    try:
        limit = int(message.text.strip())
        if limit < 1 or limit > 1000000:
            await message.answer(
                "❌ Неверное значение. Введите число от 1 до 1,000,000.\n"
                "Или используйте /cancel для отмены."
            )
            return

        await state.update_data(limit=limit)
        await _show_date_menu(message, state)

    except ValueError:
        await message.answer(
            "❌ Неверный формат. Введите целое число.\n"
            "Или используйте /cancel для отмены."
        )


async def _show_date_menu(message: Message, state: FSMContext):
    """Показать меню выбора периода дат"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 За все время", callback_data="date_all"),
        ],
        [
            InlineKeyboardButton(text="7️⃣ Последние 7 дней", callback_data="date_7days"),
            InlineKeyboardButton(text="3️⃣0 Последние 30 дней", callback_data="date_30days"),
        ],
        [
            InlineKeyboardButton(text="3️⃣ Последние 3 месяца", callback_data="date_3months"),
            InlineKeyboardButton(text="🗓 Последний год", callback_data="date_1year"),
        ],
        [
            InlineKeyboardButton(text="✏️ Кастомная дата", callback_data="date_custom"),
        ]
    ])

    await state.set_state(ExportStates.waiting_date_choice)
    await message.answer(
        "📅 <b>Настройка экспорта - Шаг 2/2</b>\n\n"
        "За какой период экспортировать сообщения?",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("date_"), ExportStates.waiting_date_choice)
async def process_date_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора периода дат"""
    await callback.answer()

    choice = callback.data.replace("date_", "")

    if choice == "custom":
        await state.set_state(ExportStates.waiting_custom_date)
        await callback.message.edit_text(
            "📅 <b>Кастомная дата</b>\n\n"
            "Введите дату начала в формате <code>ДД.ММ.ГГГГ</code>\n"
            "Например: <code>01.01.2024</code>\n\n"
            "Будут экспортированы сообщения начиная с этой даты и до настоящего момента.\n\n"
            "Или используйте /cancel для отмены."
        )
        return

    # Определить даты
    now = datetime.now()
    start_date = None

    date_map = {
        "all": None,  # За все время
        "7days": now - timedelta(days=7),
        "30days": now - timedelta(days=30),
        "3months": now - timedelta(days=90),
        "1year": now - timedelta(days=365)
    }

    start_date = date_map.get(choice)
    await state.update_data(start_date=start_date, end_date=None)

    # Начать экспорт с выбранными параметрами
    await _start_export_with_params(callback.message, state)


@router.message(ExportStates.waiting_custom_date)
async def process_custom_date(message: Message, state: FSMContext):
    """Обработка ввода кастомной даты"""
    if message.text and message.text.startswith('/cancel'):
        await state.clear()
        await message.answer("❌ Экспорт отменен.")
        return

    try:
        # Парсинг даты в формате ДД.ММ.ГГГГ
        date_str = message.text.strip()
        start_date = datetime.strptime(date_str, "%d.%m.%Y")

        # Проверка что дата не в будущем
        if start_date > datetime.now():
            await message.answer(
                "❌ Дата не может быть в будущем.\n"
                "Попробуйте еще раз или используйте /cancel для отмены."
            )
            return

        await state.update_data(start_date=start_date, end_date=None)
        await _start_export_with_params(message, state)

    except ValueError:
        await message.answer(
            "❌ Неверный формат даты. Используйте формат <code>ДД.ММ.ГГГГ</code>\n"
            "Например: <code>01.01.2024</code>\n\n"
            "Или используйте /cancel для отмены."
        )


async def _start_export_with_params(message: Message, state: FSMContext):
    """Начать экспорт с выбранными параметрами"""
    data = await state.get_data()
    chat_id = data.get('chat_id')
    chat_input = data.get('chat_input')
    limit = data.get('limit')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    # Очистить состояние
    await state.clear()

    logger.info(f"User {message.from_user.id} starting export: chat={chat_id}, limit={limit}, start_date={start_date}")

    try:
        # Добавить задачу в очередь
        task_id = await task_queue.add_task(
            task_type=TaskType.EXPORT,
            user_id=message.from_user.id,
            data={
                'chat_id': chat_id,
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'limit': limit
            }
        )

        # Форматирование для отображения
        display_chat = format_chat_identifier_for_display(chat_input)

        if limit is None:
            limit_text = "Все сообщения"
        else:
            limit_text = f"{limit:,} сообщений"

        if start_date is None:
            period_text = "За все время"
        else:
            period_text = f"С {start_date.strftime('%d.%m.%Y')}"

        await message.answer(
            f"✅ <b>Задача создана!</b>\n\n"
            f"🆔 Задача: #{task_id}\n"
            f"📱 Чат: <code>{display_chat}</code>\n"
            f"📅 Период: {period_text}\n"
            f"📊 Лимит: {limit_text}\n\n"
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


async def _process_export(message: Message, state: FSMContext, chat_input: str):
    """
    Общая функция обработки экспорта (когда чат передан сразу в команде)

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
            "Попробуйте еще раз."
        )
        return

    # Сохранить информацию о чате в FSM
    await state.update_data(chat_id=chat_id, chat_input=chat_input)

    # Показать меню выбора лимита сообщений
    await _show_limit_menu(message, state)


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
