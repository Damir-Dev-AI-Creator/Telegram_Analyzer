# bot/handlers/analyze.py
"""Обработчики команд для анализа через Claude API"""

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, Document
from aiogram.fsm.context import FSMContext
import logging
import os

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

    await _process_export_analyze(message, state, chat_input)


async def _process_export_analyze(message: Message, state: FSMContext, chat_input: str):
    """
    Общая функция обработки экспорта+анализа

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

    logger.info(f"User {message.from_user.id} requested export+analyze for chat: {chat_id}")

    try:
        # Добавить комбинированную задачу в очередь
        task_id = await task_queue.add_task(
            task_type=TaskType.EXPORT_ANALYZE,
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
            f"📱 Чат: <code>{display_chat}</code>\n\n"
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
