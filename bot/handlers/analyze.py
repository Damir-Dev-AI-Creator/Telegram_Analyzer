# bot/handlers/analyze.py
"""Обработчики команд для анализа через Claude API"""

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, Document, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import logging
import os
from datetime import datetime, timedelta

from core.queue import task_queue, TaskType
from core.config import EXPORT_FOLDER
from core.chat_utils import parse_chat_identifier, get_chat_help_text, format_chat_identifier_for_display
from bot.states.command_states import ExportAnalyzeStates

logger = logging.getLogger(__name__)

# Создаем router для этого модуля
router = Router()


@router.message(Command("analyze"))
async def cmd_analyze(message: Message):
    """
    Обработчик команды /analyze

    Формат 1: /analyze (с прикрепленным CSV файлом)
    Формат 2: /analyze имя_файла.csv

    Примеры:
        /analyze (+ прикрепить CSV файл)
        /analyze my_chat_01-01-2024_now.csv
    """
    # Проверить есть ли прикрепленный файл
    if message.document:
        await _analyze_from_document(message)
        return

    # Проверить есть ли имя файла в аргументах
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "❌ <b>Неверный формат команды</b>\n\n"
            "<b>Использование:</b>\n\n"
            "<b>Вариант 1:</b> Прикрепите CSV файл и отправьте команду\n"
            "<code>/analyze</code> (+ файл)\n\n"
            "<b>Вариант 2:</b> Укажите имя файла из папки exports\n"
            "<code>/analyze имя_файла.csv</code>\n\n"
            "Используйте /help для подробных инструкций."
        )
        return

    filename = args[1].strip()

    # Проверить существование файла
    file_path = os.path.join(EXPORT_FOLDER, filename)

    if not os.path.exists(file_path):
        await message.answer(
            f"❌ <b>Файл не найден</b>\n\n"
            f"Файл <code>{filename}</code> не найден в папке exports.\n\n"
            f"Убедитесь, что:\n"
            f"• Файл был экспортирован ранее\n"
            f"• Имя файла указано правильно\n"
            f"• Файл находится в папке exports"
        )
        return

    await _create_analyze_task(message, file_path, filename)


async def _analyze_from_document(message: Message):
    """Анализ файла из прикрепленного документа"""
    document: Document = message.document

    # Проверить расширение файла
    if not document.file_name.endswith('.csv'):
        await message.answer(
            "❌ <b>Неверный формат файла</b>\n\n"
            "Пожалуйста, отправьте CSV файл с расширением .csv"
        )
        return

    try:
        # Скачать файл
        file_info = await message.bot.get_file(document.file_id)

        # Сохранить во временную папку
        temp_path = os.path.join(EXPORT_FOLDER, document.file_name)

        await message.bot.download_file(file_info.file_path, temp_path)

        logger.info(f"File {document.file_name} downloaded to {temp_path}")

        await _create_analyze_task(message, temp_path, document.file_name)

    except Exception as e:
        logger.error(f"Error downloading file: {e}", exc_info=True)

        await message.answer(
            f"❌ <b>Ошибка загрузки файла</b>\n\n"
            f"Ошибка: {str(e)}"
        )


async def _create_analyze_task(message: Message, file_path: str, filename: str):
    """Создать задачу анализа"""
    try:
        # Добавить задачу в очередь
        task_id = await task_queue.add_task(
            task_type=TaskType.ANALYZE,
            user_id=message.from_user.id,
            data={
                'file_path': file_path,
                'filename': filename
            }
        )

        # Сразу ответить пользователю
        await message.answer(
            f"✅ <b>Задача анализа создана!</b>\n\n"
            f"🆔 Задача: #{task_id}\n"
            f"📄 Файл: <code>{filename}</code>\n"
            f"🤖 Модель: Claude Sonnet 4\n\n"
            f"⏳ Анализ начнется в течение нескольких секунд.\n"
            f"Это может занять 1-3 минуты.\n\n"
            f"Я отправлю DOCX файл с результатами анализа."
        )

        logger.info(f"Analyze task #{task_id} created for user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error creating analyze task: {e}", exc_info=True)

        await message.answer(
            f"❌ <b>Ошибка создания задачи</b>\n\n"
            f"Ошибка: {str(e)}"
        )


@router.message(Command("exportanalyze"))
async def cmd_export_analyze(message: Message, state: FSMContext):
    """
    Обработчик команды /exportanalyze

    Поддерживает два режима:
    1. С аргументом: /exportanalyze https://t.me/chat - выполняется сразу
    2. Без аргумента: /exportanalyze - бот просит отправить ссылку следующим сообщением

    Примеры:
        /exportanalyze -1001234567890
        /exportanalyze @durov
        /exportanalyze https://t.me/telegram
    """
    # Получить аргументы команды
    args = message.text.split(maxsplit=1)

    # Режим 1: Команда с аргументом - выполнить сразу
    if len(args) >= 2:
        chat_input = args[1].strip()
        await _process_export_analyze(message, state, chat_input)
        return

    # Режим 2: Команда без аргумента - перейти в режим ожидания
    await state.set_state(ExportAnalyzeStates.waiting_chat_link)
    await message.answer(
        "⚡ <b>Экспорт + Анализ</b>\n\n"
        "Отправьте мне ссылку на чат, username или ID следующим сообщением:\n\n"
        f"{get_chat_help_text()}\n\n"
        "<b>Что произойдет:</b>\n"
        "1. Экспортирую чат в CSV (~30 сек)\n"
        "2. Анализирую через Claude API (~1-3 мин)\n"
        "3. Отправлю оба файла\n\n"
        "Или используйте /cancel для отмены."
    )


@router.message(ExportAnalyzeStates.waiting_chat_link)
async def process_exportanalyze_chat_link(message: Message, state: FSMContext):
    """Обработка ссылки/ID чата после команды /exportanalyze"""

    # Проверка на команду отмены
    if message.text and message.text.startswith('/cancel'):
        await state.clear()
        await message.answer("❌ Экспорт+анализ отменен.")
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
    await _show_exportanalyze_limit_menu(message, state)


async def _show_exportanalyze_limit_menu(message: Message, state: FSMContext):
    """Показать меню выбора лимита сообщений для exportanalyze"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📭 Все сообщения", callback_data="ea_limit_all"),
        ],
        [
            InlineKeyboardButton(text="💯 Последние 100", callback_data="ea_limit_100"),
            InlineKeyboardButton(text="1️⃣K Последние 1,000", callback_data="ea_limit_1000"),
        ],
        [
            InlineKeyboardButton(text="🔟K Последние 10,000", callback_data="ea_limit_10000"),
            InlineKeyboardButton(text="5️⃣0K Последние 50,000", callback_data="ea_limit_50000"),
        ],
        [
            InlineKeyboardButton(text="✏️ Кастомный лимит", callback_data="ea_limit_custom"),
        ]
    ])

    await state.set_state(ExportAnalyzeStates.waiting_limit_choice)
    await message.answer(
        "📊 <b>Настройка экспорта+анализа - Шаг 1/2</b>\n\n"
        "Сколько сообщений экспортировать?",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("ea_limit_"), ExportAnalyzeStates.waiting_limit_choice)
async def process_exportanalyze_limit_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора лимита сообщений для exportanalyze"""
    await callback.answer()

    choice = callback.data.replace("ea_limit_", "")

    if choice == "custom":
        await state.set_state(ExportAnalyzeStates.waiting_custom_limit)
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
    await _show_exportanalyze_date_menu(callback.message, state)


@router.message(ExportAnalyzeStates.waiting_custom_limit)
async def process_exportanalyze_custom_limit(message: Message, state: FSMContext):
    """Обработка ввода кастомного лимита для exportanalyze"""
    if message.text and message.text.startswith('/cancel'):
        await state.clear()
        await message.answer("❌ Экспорт+анализ отменен.")
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
        await _show_exportanalyze_date_menu(message, state)

    except ValueError:
        await message.answer(
            "❌ Неверный формат. Введите целое число.\n"
            "Или используйте /cancel для отмены."
        )


async def _show_exportanalyze_date_menu(message: Message, state: FSMContext):
    """Показать меню выбора периода дат для exportanalyze"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 За все время", callback_data="ea_date_all"),
        ],
        [
            InlineKeyboardButton(text="7️⃣ Последние 7 дней", callback_data="ea_date_7days"),
            InlineKeyboardButton(text="3️⃣0 Последние 30 дней", callback_data="ea_date_30days"),
        ],
        [
            InlineKeyboardButton(text="3️⃣ Последние 3 месяца", callback_data="ea_date_3months"),
            InlineKeyboardButton(text="🗓 Последний год", callback_data="ea_date_1year"),
        ],
        [
            InlineKeyboardButton(text="✏️ Кастомная дата", callback_data="ea_date_custom"),
        ]
    ])

    await state.set_state(ExportAnalyzeStates.waiting_date_choice)
    await message.answer(
        "📅 <b>Настройка экспорта+анализа - Шаг 2/2</b>\n\n"
        "За какой период экспортировать сообщения?",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("ea_date_"), ExportAnalyzeStates.waiting_date_choice)
async def process_exportanalyze_date_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора периода дат для exportanalyze"""
    await callback.answer()

    choice = callback.data.replace("ea_date_", "")

    if choice == "custom":
        await state.set_state(ExportAnalyzeStates.waiting_custom_date)
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

    # Начать экспорт+анализ с выбранными параметрами
    await _start_exportanalyze_with_params(callback.message, state)


@router.message(ExportAnalyzeStates.waiting_custom_date)
async def process_exportanalyze_custom_date(message: Message, state: FSMContext):
    """Обработка ввода кастомной даты для exportanalyze"""
    if message.text and message.text.startswith('/cancel'):
        await state.clear()
        await message.answer("❌ Экспорт+анализ отменен.")
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
        await _start_exportanalyze_with_params(message, state)

    except ValueError:
        await message.answer(
            "❌ Неверный формат даты. Используйте формат <code>ДД.ММ.ГГГГ</code>\n"
            "Например: <code>01.01.2024</code>\n\n"
            "Или используйте /cancel для отмены."
        )


async def _start_exportanalyze_with_params(message: Message, state: FSMContext):
    """Начать экспорт+анализ с выбранными параметрами"""
    data = await state.get_data()
    chat_id = data.get('chat_id')
    chat_input = data.get('chat_input')
    limit = data.get('limit')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    # Очистить состояние
    await state.clear()

    logger.info(f"User {message.from_user.id} starting export+analyze: chat={chat_id}, limit={limit}, start_date={start_date}")

    try:
        # Добавить комбинированную задачу в очередь
        task_id = await task_queue.add_task(
            task_type=TaskType.EXPORT_ANALYZE,
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
            f"<b>📋 План выполнения:</b>\n"
            f"1️⃣ Экспорт чата в CSV (~30 сек)\n"
            f"2️⃣ Анализ через Claude API (~1-3 мин)\n\n"
            f"⏳ Обработка начнется в течение нескольких секунд.\n"
            f"Я буду отправлять уведомления о прогрессе."
        )

        logger.info(f"Export+Analyze task #{task_id} created for user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error creating export+analyze task: {e}", exc_info=True)

        await message.answer(
            f"❌ <b>Ошибка создания задачи</b>\n\n"
            f"Ошибка: {str(e)}\n\n"
            f"Попробуйте еще раз или обратитесь к администратору."
        )


async def _process_export_analyze(message: Message, state: FSMContext, chat_input: str):
    """
    Общая функция обработки экспорта+анализа (когда чат передан сразу в команде)

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
    await _show_exportanalyze_limit_menu(message, state)


@router.message(F.text.startswith("/analyze"))
async def cmd_analyze_fallback(message: Message):
    """Fallback для неправильного формата команды /analyze"""
    await message.answer(
        "❌ Неверный формат. Используйте:\n"
        "<code>/analyze имя_файла.csv</code>\n"
        "или прикрепите CSV файл\n\n"
        "Подробности: /help"
    )


@router.message(F.text.startswith("/exportanalyze"))
async def cmd_exportanalyze_fallback(message: Message):
    """Fallback для неправильного формата команды /exportanalyze"""
    await message.answer(
        "❌ <b>Неверный формат команды</b>\n\n"
        "<b>Использование:</b>\n"
        "<code>/exportanalyze CHAT</code>\n\n"
        f"{get_chat_help_text()}\n\n"
        "Подробности: /help"
    )


@router.message(F.document)
async def handle_document_upload(message: Message):
    """
    Автоматический анализ загруженных CSV файлов без команды

    Когда пользователь загружает CSV файл без команды /analyze,
    автоматически запускается анализ этого файла.
    """
    document: Document = message.document

    # Проверить что это CSV файл
    if not document.file_name.endswith('.csv'):
        # Игнорировать файлы не CSV формата
        return

    # Проверить что пользователь настроен
    from core.db_manager import get_db_manager
    db = get_db_manager()
    user = await db.get_user(message.from_user.id)

    if not user or not user.is_configured:
        await message.answer(
            "⚠️ <b>Необходима настройка</b>\n\n"
            "Для анализа файлов сначала настройте бота командой /setup\n\n"
            "После настройки вы сможете:\n"
            "• Загружать CSV файлы для автоматического анализа\n"
            "• Использовать команду /analyze для анализа файлов\n"
            "• Экспортировать чаты командой /export"
        )
        return

    # Запустить анализ загруженного CSV файла
    await _analyze_from_document(message)
