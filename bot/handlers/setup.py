# bot/handlers/setup.py
"""Обработчики процесса настройки (onboarding) пользователя с QR-авторизацией"""

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, BufferedInputFile
import logging
import re
import asyncio
import qrcode
from io import BytesIO
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    ApiIdInvalidError,
    SessionRevokedError
)

from bot.states.setup_states import SetupStates
from core.db_manager import get_db_manager

logger = logging.getLogger(__name__)

# Создаем router для этого модуля
router = Router()


# ======================= КОМАНДА /setup =======================

@router.message(Command("setup"))
async def cmd_setup(message: Message, state: FSMContext):
    """
    Команда /setup - начать процесс настройки

    Запускает onboarding flow для нового пользователя или перенастройки
    """
    user_id = message.from_user.id
    db = get_db_manager()

    # Проверить, существует ли пользователь
    user = await db.get_user(user_id)

    if user and user.is_configured:
        # Пользователь уже настроен - предложить перенастройку
        await message.answer(
            "⚙️ <b>Вы уже настроили бота</b>\n\n"
            "Ваши текущие данные:\n"
            f"• Telegram API: {'✅ Настроен' if user.api_id else '❌ Не настроен'}\n"
            f"• Авторизация: {'✅ Авторизован' if user.is_authorized else '❌ Не авторизован'}\n"
            f"• Claude API: {'✅ Настроен' if user.claude_api_key else '❌ Не настроен'}\n\n"
            "<b>⚠️ Внимание!</b>\n"
            "Перенастройка удалит ваши текущие данные и сессию.\n\n"
            "Хотите продолжить перенастройку?",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="✅ Да, перенастроить")],
                    [KeyboardButton(text="❌ Нет, отменить")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        await state.set_state(SetupStates.waiting_api_id)
        await state.update_data(reconfiguring=True)
        return

    # Новый пользователь - начать onboarding
    if not user:
        # Создать пользователя в БД
        user = await db.create_user(
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        logger.info(f"New user created: {user_id} (@{message.from_user.username})")

    await message.answer(
        "👋 <b>Добро пожаловать в Telegram Analyzer!</b>\n\n"
        "Этот бот поможет вам:\n"
        "• 📥 Экспортировать чаты в CSV\n"
        "• 🤖 Анализировать переписки через Claude API\n"
        "• 📊 Получать детальную статистику\n\n"
        "<b>📋 Что нужно для начала работы:</b>\n\n"
        "1️⃣ <b>Telegram API ключи</b> (обязательно)\n"
        "   • API ID\n"
        "   • API Hash\n"
        "   • Авторизация через QR-код\n\n"
        "2️⃣ <b>Claude API ключ</b> (опционально)\n"
        "   • Нужен только для функции анализа\n"
        "   • Можно добавить позже через /settings\n\n"
        "<b>🔐 Безопасность:</b>\n"
        "• Все данные хранятся зашифрованными\n"
        "• Доступ только у вас\n"
        "• Можно удалить в любой момент через /settings\n\n"
        "Готовы начать настройку?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Начать настройку")],
                [KeyboardButton(text="❌ Отменить")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    await state.set_state(SetupStates.waiting_api_id)


# ======================= ШАГ 1: API_ID =======================

@router.message(SetupStates.waiting_api_id, F.text == "✅ Начать настройку")
@router.message(SetupStates.waiting_api_id, F.text == "✅ Да, перенастроить")
async def setup_start(message: Message, state: FSMContext):
    """Начало настройки - запрос API_ID"""
    await message.answer(
        "📝 <b>Шаг 1/3: Получение Telegram API ключей</b>\n\n"
        "<b>Как получить API ключи:</b>\n\n"
        "1️⃣ Перейдите на сайт: https://my.telegram.org\n"
        "2️⃣ Войдите под своим номером телефона\n"
        "3️⃣ Перейдите в <b>API development tools</b>\n"
        "4️⃣ Создайте приложение (любое название)\n"
        "5️⃣ Скопируйте <b>API ID</b> и <b>API Hash</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Отправьте мне ваш <b>API ID</b> (это число):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.update_data(reconfiguring=False)


@router.message(SetupStates.waiting_api_id, F.text == "❌ Нет, отменить")
@router.message(SetupStates.waiting_api_id, F.text == "❌ Отменить")
async def setup_cancel(message: Message, state: FSMContext):
    """Отмена настройки"""
    await state.clear()
    await message.answer(
        "❌ <b>Настройка отменена</b>\n\n"
        "Вы можете начать настройку в любой момент командой /setup",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(SetupStates.waiting_api_id)
async def process_api_id(message: Message, state: FSMContext):
    """Обработка API_ID"""
    api_id_str = message.text.strip()

    # Валидация: должно быть числом
    if not api_id_str.isdigit():
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            "API ID должен быть числом (например: <code>12345678</code>)\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены."
        )
        return

    api_id = int(api_id_str)

    # Проверить, что API ID не слишком маленький (обычно 7-8 цифр)
    if api_id < 10000:
        await message.answer(
            "⚠️ <b>Предупреждение</b>\n\n"
            "API ID обычно состоит из 7-8 цифр.\n"
            "Вы уверены, что это правильное значение?\n\n"
            f"Вы ввели: <code>{api_id}</code>\n\n"
            "Отправьте правильное значение или /cancel для отмены."
        )
        return

    # Сохранить API_ID во временное хранилище FSM
    await state.update_data(api_id=api_id)

    await message.answer(
        f"✅ API ID сохранен: <code>{api_id}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Теперь отправьте мне <b>API Hash</b> (строка из букв и цифр):"
    )

    await state.set_state(SetupStates.waiting_api_hash)


# ======================= ШАГ 2: API_HASH =======================

@router.message(SetupStates.waiting_api_hash)
async def process_api_hash(message: Message, state: FSMContext):
    """Обработка API_HASH и запуск QR-авторизации"""
    api_hash = message.text.strip()

    # Валидация: должен быть строкой 32 символа (hex)
    if len(api_hash) != 32:
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            "API Hash должен быть строкой из 32 символов\n"
            "(например: <code>a1b2c3d4e5f6...</code>)\n\n"
            f"Вы ввели {len(api_hash)} символов.\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены."
        )
        return

    # Проверить, что это hex-строка
    if not re.match(r'^[a-fA-F0-9]{32}$', api_hash):
        await message.answer(
            "⚠️ <b>Предупреждение</b>\n\n"
            "API Hash обычно состоит только из букв (a-f) и цифр (0-9).\n\n"
            "Вы уверены, что это правильное значение?\n\n"
            f"Вы ввели: <code>{api_hash}</code>\n\n"
            "Отправьте правильное значение или /cancel для отмены."
        )
        # Но продолжаем, так как бывают исключения

    # Сохранить API_HASH во временное хранилище FSM
    await state.update_data(api_hash=api_hash)

    # Получить API_ID
    data = await state.get_data()
    api_id = data['api_id']

    await message.answer(
        "✅ API Hash сохранен\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Шаг 2/3: Авторизация в Telegram через QR-код</b>\n\n"
        "⏳ Генерирую QR-код для авторизации...\n\n"
        "Пожалуйста, подождите..."
    )

    # Запустить QR-авторизацию
    await start_qr_auth(message, state, api_id, api_hash)


# ======================= ШАГ 3: QR-АВТОРИЗАЦИЯ =======================

async def start_qr_auth(message: Message, state: FSMContext, api_id: int, api_hash: str):
    """
    Запуск QR-авторизации через Telethon

    Args:
        message: Сообщение пользователя
        state: FSM контекст
        api_id: Telegram API ID
        api_hash: Telegram API Hash
    """
    user_id = message.from_user.id

    try:
        # Создать Telethon клиент
        client = TelegramClient(
            StringSession(),
            api_id,
            api_hash,
            device_model="Telegram Analyzer Bot",
            system_version="Linux",
            app_version="1.0"
        )

        await client.connect()

        # Запустить QR-авторизацию
        qr_login = await client.qr_login()

        # Получить URL для QR-кода
        qr_url = qr_login.url

        logger.info(f"QR login started for user {user_id}, URL: {qr_url}")

        # Создать QR-код
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)

        # Создать изображение QR-кода
        qr_image = qr.make_image(fill_color="black", back_color="white")

        # Сохранить в BytesIO
        bio = BytesIO()
        qr_image.save(bio, format='PNG')
        bio.seek(0)

        # Отправить QR-код пользователю
        qr_file = BufferedInputFile(bio.read(), filename="telegram_qr.png")

        await message.answer_photo(
            photo=qr_file,
            caption=(
                "📱 <b>QR-код для авторизации готов!</b>\n\n"
                "<b>Как авторизоваться:</b>\n\n"
                "1️⃣ Откройте Telegram на телефоне\n"
                "2️⃣ Перейдите: <b>Настройки → Устройства</b>\n"
                "3️⃣ Нажмите <b>Привязать устройство</b>\n"
                "4️⃣ Отсканируйте этот QR-код\n\n"
                "⏳ <b>Жду авторизации...</b>\n\n"
                "QR-код действителен <b>5 минут</b>\n\n"
                "Отправьте /cancel для отмены"
            )
        )

        # Перейти в состояние ожидания сканирования
        await state.set_state(SetupStates.waiting_qr_scan)

        # Запустить фоновую задачу ожидания авторизации
        asyncio.create_task(wait_for_qr_auth(message, state, client, qr_login, user_id))

    except ApiIdInvalidError:
        await message.answer(
            "❌ <b>Ошибка авторизации</b>\n\n"
            "<b>Неверный API ID или API Hash</b>\n\n"
            "Пожалуйста, проверьте данные на https://my.telegram.org\n\n"
            "Начните настройку заново: /setup"
        )
        await state.clear()
        logger.error(f"Invalid API credentials for user {user_id}")

    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка создания QR-кода</b>\n\n"
            f"Ошибка: <code>{str(e)}</code>\n\n"
            "Попробуйте еще раз: /setup"
        )
        await state.clear()
        logger.error(f"Error starting QR auth for user {user_id}: {e}", exc_info=True)


async def wait_for_qr_auth(message: Message, state: FSMContext, client: TelegramClient, qr_login, user_id: int):
    """
    Фоновая задача ожидания авторизации через QR-код

    Args:
        message: Сообщение пользователя
        state: FSM контекст
        client: Telethon клиент
        qr_login: QR login объект
        user_id: ID пользователя
    """
    try:
        # Ждать авторизации с таймаутом 5 минут
        await asyncio.wait_for(qr_login.wait(), timeout=300)

        # Авторизация успешна!
        logger.info(f"User {user_id} successfully authorized via QR")

        # Получить информацию о пользователе
        me = await client.get_me()
        phone = me.phone

        # Сохранить session string
        session_string = client.session.save()

        # Получить API credentials
        data = await state.get_data()
        api_id = data['api_id']
        api_hash = data['api_hash']

        # Сохранить в базу данных
        db = get_db_manager()
        await db.update_user(
            user_id=user_id,
            api_id=api_id,
            api_hash=api_hash,
            phone=phone,
            session_string=session_string,
            is_authorized=True
        )

        await client.disconnect()

        # Уведомить пользователя
        await message.answer(
            "✅ <b>Успешно авторизован!</b>\n\n"
            f"📱 Телефон: <code>{phone}</code>\n"
            f"👤 Имя: {me.first_name or 'Unknown'}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Шаг 3/3: Claude API (опционально)</b>\n\n"
            "Claude API используется для анализа переписок.\n\n"
            "<b>Как получить ключ:</b>\n"
            "1️⃣ Перейдите: https://console.anthropic.com/\n"
            "2️⃣ Зарегистрируйтесь или войдите\n"
            "3️⃣ Перейдите в API Keys\n"
            "4️⃣ Создайте новый ключ\n\n"
            "Отправьте мне ваш <b>Claude API ключ</b>\n"
            "или нажмите <b>Пропустить</b> (можно добавить позже через /settings)",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="⏭️ Пропустить")]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

        await state.set_state(SetupStates.waiting_claude_key)

    except asyncio.TimeoutError:
        # Таймаут - QR не был отсканирован
        logger.warning(f"QR auth timeout for user {user_id}")

        await client.disconnect()
        await state.clear()

        await message.answer(
            "⏱️ <b>Время истекло</b>\n\n"
            "QR-код не был отсканирован в течение 5 минут.\n\n"
            "Начните настройку заново: /setup",
            reply_markup=ReplyKeyboardRemove()
        )

    except SessionRevokedError:
        logger.error(f"Session revoked during QR auth for user {user_id}")

        await client.disconnect()
        await state.clear()

        await message.answer(
            "❌ <b>Сессия отозвана</b>\n\n"
            "Возможно, вы отменили авторизацию в приложении.\n\n"
            "Начните настройку заново: /setup",
            reply_markup=ReplyKeyboardRemove()
        )

    except Exception as e:
        logger.error(f"Error during QR auth wait for user {user_id}: {e}", exc_info=True)

        try:
            await client.disconnect()
        except:
            pass

        await state.clear()

        await message.answer(
            f"❌ <b>Ошибка авторизации</b>\n\n"
            f"Ошибка: <code>{str(e)}</code>\n\n"
            "Попробуйте еще раз: /setup",
            reply_markup=ReplyKeyboardRemove()
        )


@router.message(SetupStates.waiting_qr_scan)
async def process_qr_scan_waiting(message: Message, state: FSMContext):
    """Обработка сообщений во время ожидания QR-сканирования"""
    # Пользователь отправил сообщение во время ожидания
    await message.answer(
        "⏳ <b>Ожидание авторизации...</b>\n\n"
        "Пожалуйста, отсканируйте QR-код в приложении Telegram.\n\n"
        "Если QR-код не виден, прокрутите вверх.\n\n"
        "Отправьте /cancel для отмены настройки."
    )


# ======================= CLAUDE API =======================

@router.message(SetupStates.waiting_claude_key, F.text == "⏭️ Пропустить")
async def skip_claude_key(message: Message, state: FSMContext):
    """Пропустить настройку Claude API"""
    user_id = message.from_user.id
    db = get_db_manager()

    # Отметить пользователя как настроенного
    await db.update_user(user_id=user_id, is_configured=True)

    await state.clear()

    await message.answer(
        "🎉 <b>Настройка завершена!</b>\n\n"
        "✅ Telegram API настроен\n"
        "⏭️ Claude API пропущен\n\n"
        "Вы можете:\n"
        "• Экспортировать чаты командой /export\n"
        "• Настроить Claude API позже через /settings\n\n"
        "Нажмите /help для подробной справки",
        reply_markup=ReplyKeyboardRemove()
    )

    logger.info(f"User {user_id} completed setup without Claude API")


@router.message(SetupStates.waiting_claude_key)
async def process_claude_key(message: Message, state: FSMContext):
    """Обработка Claude API ключа"""
    claude_key = message.text.strip()

    # Базовая валидация (ключи Anthropic обычно начинаются с sk-ant-)
    if not claude_key.startswith('sk-ant-'):
        await message.answer(
            "⚠️ <b>Предупреждение</b>\n\n"
            "Claude API ключи обычно начинаются с <code>sk-ant-</code>\n\n"
            "Вы уверены, что это правильный ключ?\n\n"
            "Отправьте правильное значение или нажмите <b>Пропустить</b>"
        )
        return

    user_id = message.from_user.id
    db = get_db_manager()

    # Сохранить Claude API ключ и отметить как настроенного
    await db.update_user(
        user_id=user_id,
        claude_api_key=claude_key,
        is_configured=True
    )

    await state.clear()

    await message.answer(
        "🎉 <b>Настройка полностью завершена!</b>\n\n"
        "✅ Telegram API настроен\n"
        "✅ Claude API настроен\n\n"
        "Теперь вы можете:\n"
        "• Экспортировать чаты: /export\n"
        "• Анализировать переписки: /analyze\n"
        "• Экспорт + анализ: /exportanalyze\n\n"
        "Нажмите /help для подробной справки",
        reply_markup=ReplyKeyboardRemove()
    )

    logger.info(f"User {user_id} completed full setup with Claude API")


# ======================= ОТМЕНА НАСТРОЙКИ =======================

@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel_setup(message: Message, state: FSMContext):
    """Отмена процесса настройки в любом состоянии"""
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(
            "Нет активного процесса настройки.\n\n"
            "Начать настройку: /setup"
        )
        return

    await state.clear()

    await message.answer(
        "❌ <b>Настройка отменена</b>\n\n"
        "Вы можете начать настройку в любой момент командой /setup",
        reply_markup=ReplyKeyboardRemove()
    )

    logger.info(f"User {message.from_user.id} cancelled setup from state {current_state}")
