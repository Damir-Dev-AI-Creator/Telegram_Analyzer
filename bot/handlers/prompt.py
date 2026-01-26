# bot/handlers/prompt.py
"""Обработчик команды /setprompt для настройки кастомного промпта"""

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import logging

from bot.states.command_states import PromptStates
from core.db_manager import get_db_manager

logger = logging.getLogger(__name__)

# Создаем router для этого модуля
router = Router()

# Дефолтный промпт для справки
DEFAULT_PROMPT = """Проанализируй следующие данные из CSV файла, содержащие информацию о взаимодействиях с клиентами и работе менеджеров службы поддержки.

Менеджеры в CSV файлах имеют наименование, которое содержит в себе 'Fulfillment-Box Support', 'Support', 'Fulfillment-Box' и подобное.

Данные CSV файла:
{csv_content}

На основе этих данных предоставь анализ по следующим пунктам:

1. **Самые частые запросы клиентов** — повторяющиеся вопросы и темы обращений.

2. **Причины конфликтов и недовольства клиентов** — выяви основные проблемные области.

3. **Количество вопросов по каждому менеджеру** — статистика обработанных обращений.

4. **Среднее время ответа менеджеров** — отдельно для будней и выходных.

Формат вывода:
- Структурированный текст без таблиц
- Без упоминания номеров строк и сообщений
- Не включай методику обработки в отчёт
- Не добавляй рекомендации и советы в конце
- Это только аналитический отчёт

Предоставь анализ на русском языке."""


@router.message(Command("setprompt"))
async def cmd_setprompt(message: Message, state: FSMContext):
    """
    Обработчик команды /setprompt

    Позволяет настроить кастомный промпт для анализа через Claude API
    """
    user_id = message.from_user.id
    db = get_db_manager()
    settings = await db.get_user_settings(user_id)
    current_prompt = settings.custom_prompt if settings and settings.custom_prompt else None

    # Кнопки управления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Установить новый", callback_data="prompt_set"),
            InlineKeyboardButton(text="👁 Показать текущий", callback_data="prompt_show")
        ],
        [
            InlineKeyboardButton(text="🔄 Сбросить на дефолтный", callback_data="prompt_reset"),
            InlineKeyboardButton(text="ℹ️ Справка", callback_data="prompt_help")
        ]
    ])

    status_text = "✅ Установлен кастомный промпт" if current_prompt else "📝 Используется дефолтный промпт"

    await message.answer(
        f"🎯 <b>Настройка промпта для анализа</b>\n\n"
        f"Статус: {status_text}\n\n"
        f"<b>Что это?</b>\n"
        f"Промпт — это инструкция для Claude AI, которая определяет как анализировать ваши чаты.\n\n"
        f"<b>Возможности:</b>\n"
        f"• Установить свой промпт\n"
        f"• Посмотреть текущий\n"
        f"• Сбросить на дефолтный\n\n"
        f"Выберите действие:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "prompt_set")
async def callback_prompt_set(callback, state: FSMContext):
    """Начать процесс установки нового промпта"""
    await state.set_state(PromptStates.waiting_prompt_text)
    await callback.message.edit_text(
        "✏️ <b>Установка кастомного промпта</b>\n\n"
        "Отправьте мне текст вашего промпта следующим сообщением.\n\n"
        "<b>⚠️ Важно:</b>\n"
        "• Используйте <code>{csv_content}</code> где нужно вставить данные CSV\n"
        "• Промпт должен быть на русском или английском\n"
        "• Рекомендуемая длина: 500-2000 символов\n\n"
        "<b>Пример:</b>\n"
        "<code>Проанализируй данные:\n{csv_content}\n\nВыведи топ-5 проблем клиентов.</code>\n\n"
        "Или используйте /cancel для отмены."
    )
    await callback.answer()


@router.message(PromptStates.waiting_prompt_text)
async def process_prompt_text(message: Message, state: FSMContext):
    """Обработка текста промпта"""

    # Проверка на команду отмены
    if message.text and message.text.startswith('/cancel'):
        await state.clear()
        await message.answer("❌ Установка промпта отменена.")
        return

    prompt_text = message.text.strip() if message.text else ""

    if not prompt_text:
        await message.answer(
            "❌ Промпт не может быть пустым.\n"
            "Отправьте текст промпта или используйте /cancel для отмены."
        )
        return

    # Валидация
    if len(prompt_text) < 50:
        await message.answer(
            "❌ Промпт слишком короткий (минимум 50 символов).\n"
            "Отправьте более подробный промпт или используйте /cancel для отмены."
        )
        return

    if len(prompt_text) > 10000:
        await message.answer(
            "❌ Промпт слишком длинный (максимум 10000 символов).\n"
            "Сократите промпт или используйте /cancel для отмены."
        )
        return

    # Предупреждение если нет {csv_content}
    warning = ""
    if "{csv_content}" not in prompt_text:
        warning = "\n\n⚠️ <b>Предупреждение:</b> Промпт не содержит <code>{csv_content}</code>. " \
                  "Данные CSV не будут вставлены в промпт!"

    # Сохранить в БД
    try:
        db = get_db_manager()
        await db.update_user_settings(
            user_id=message.from_user.id,
            custom_prompt=prompt_text
        )

        await state.clear()

        await message.answer(
            f"✅ <b>Кастомный промпт установлен!</b>\n\n"
            f"📊 Длина: {len(prompt_text)} символов\n"
            f"🤖 Модель: Claude Sonnet 4\n\n"
            f"Теперь все анализы будут использовать ваш промпт.{warning}\n\n"
            f"Для изменения используйте /setprompt снова."
        )

        logger.info(f"User {message.from_user.id} set custom prompt ({len(prompt_text)} chars)")

    except Exception as e:
        logger.error(f"Error saving custom prompt: {e}", exc_info=True)
        await message.answer(
            f"❌ <b>Ошибка сохранения промпта</b>\n\n"
            f"Ошибка: {str(e)}\n\n"
            f"Попробуйте еще раз или обратитесь к администратору."
        )
        await state.clear()


@router.callback_query(F.data == "prompt_show")
async def callback_prompt_show(callback, state: FSMContext):
    """Показать текущий промпт"""
    user_id = callback.from_user.id
    db = get_db_manager()
    settings = await db.get_user_settings(user_id)

    if settings and settings.custom_prompt:
        prompt = settings.custom_prompt
        prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt

        await callback.message.edit_text(
            f"👁 <b>Ваш текущий кастомный промпт:</b>\n\n"
            f"<code>{prompt_preview}</code>\n\n"
            f"📊 Длина: {len(prompt)} символов\n\n"
            f"<b>Команды:</b>\n"
            f"/setprompt - Изменить промпт"
        )
    else:
        prompt_preview = DEFAULT_PROMPT[:500] + "..."
        await callback.message.edit_text(
            f"👁 <b>Текущий промпт (дефолтный):</b>\n\n"
            f"<code>{prompt_preview}</code>\n\n"
            f"📝 Используется стандартный промпт анализа.\n\n"
            f"<b>Команды:</b>\n"
            f"/setprompt - Установить свой промпт"
        )

    await callback.answer()


@router.callback_query(F.data == "prompt_reset")
async def callback_prompt_reset(callback, state: FSMContext):
    """Сбросить промпт на дефолтный"""
    user_id = callback.from_user.id
    db = get_db_manager()

    try:
        await db.update_user_settings(
            user_id=user_id,
            custom_prompt=None
        )

        await callback.message.edit_text(
            f"🔄 <b>Промпт сброшен на дефолтный</b>\n\n"
            f"Теперь будет использоваться стандартный промпт анализа.\n\n"
            f"<b>Команды:</b>\n"
            f"/setprompt - Установить кастомный промпт"
        )

        logger.info(f"User {user_id} reset prompt to default")

    except Exception as e:
        logger.error(f"Error resetting prompt: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ <b>Ошибка сброса промпта</b>\n\n"
            f"Ошибка: {str(e)}"
        )

    await callback.answer()


@router.callback_query(F.data == "prompt_help")
async def callback_prompt_help(callback, state: FSMContext):
    """Показать справку по промптам"""
    await callback.message.edit_text(
        "ℹ️ <b>Справка по кастомным промптам</b>\n\n"
        "<b>Что такое промпт?</b>\n"
        "Это инструкция для Claude AI, описывающая как анализировать ваши данные.\n\n"
        "<b>Как использовать:</b>\n"
        "1. Используйте /setprompt\n"
        "2. Выберите 'Установить новый'\n"
        "3. Отправьте текст промпта\n"
        "4. В промпте используйте <code>{csv_content}</code> для вставки данных\n\n"
        "<b>Примеры задач:</b>\n"
        "• Анализ времени ответа менеджеров\n"
        "• Выявление частых проблем клиентов\n"
        "• Статистика по темам обращений\n"
        "• Оценка качества обслуживания\n\n"
        "<b>Советы:</b>\n"
        "✅ Будьте конкретны в инструкциях\n"
        "✅ Укажите нужный формат вывода\n"
        "✅ Пишите на русском или английском\n"
        "❌ Не делайте промпт слишком сложным\n\n"
        "<b>Команды:</b>\n"
        "/setprompt - Настроить промпт"
    )
    await callback.answer()
