# bot/handlers/setup.py
"""Обработчики процесса настройки (onboarding) пользователя"""

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import logging
import re
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    SessionPasswordNeededError,
    PasswordHashInvalidError,
    ApiIdInvalidError
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
        "   • Номер телефона\n\n"
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
    """Обработка API_HASH"""
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

    await message.answer(
        "✅ API Hash сохранен\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Шаг 2/3: Авторизация в Telegram</b>\n\n"
        "Отправьте мне ваш <b>номер телефона</b> в международном формате:\n\n"
        "Примеры:\n"
        "• <code>+79991234567</code> (Россия)\n"
        "• <code>+380991234567</code> (Украина)\n"
        "• <code>+1234567890</code> (США)\n\n"
        "<b>⚠️ Важно:</b> Номер должен начинаться с <code>+</code>"
    )

    await state.set_state(SetupStates.waiting_phone)


# ======================= ШАГ 3: PHONE =======================

@router.message(SetupStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка номера телефона и отправка кода авторизации"""
    phone = message.text.strip()

    # Валидация: должен начинаться с +
    if not phone.startswith('+'):
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            "Номер телефона должен начинаться с <code>+</code>\n\n"
            "Примеры:\n"
            "• <code>+79991234567</code>\n"
            "• <code>+380991234567</code>\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены."
        )
        return

    # Проверить, что после + идут только цифры
    if not phone[1:].isdigit():
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            "После <code>+</code> должны быть только цифры\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены."
        )
        return

    # Проверить длину (обычно от 10 до 15 цифр)
    if len(phone) < 10 or len(phone) > 16:
        await message.answer(
            "⚠️ <b>Предупреждение</b>\n\n"
            "Номер телефона выглядит необычно.\n"
            "Обычная длина: 11-15 символов (с кодом страны)\n\n"
            f"Вы ввели: <code>{phone}</code> ({len(phone)} символов)\n\n"
            "Отправьте правильное значение или /cancel для отмены."
        )
        return

    # Сохранить phone
    await state.update_data(phone=phone)

    # Получить сохраненные данные
    data = await state.get_data()
    api_id = data['api_id']
    api_hash = data['api_hash']

    await message.answer(
        "⏳ <b>Подключение к Telegram...</b>\n\n"
        "Пожалуйста, подождите..."
    )

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

        # Отправить код авторизации
        sent_code = await client.send_code_request(phone)

        # Сохранить session_string и phone_code_hash
        session_string = client.session.save()
        await state.update_data(
            session_string=session_string,
            phone_code_hash=sent_code.phone_code_hash
        )

        await client.disconnect()

        await message.answer(
            "✅ <b>Код отправлен!</b>\n\n"
            f"Telegram отправил код подтверждения на номер:\n"
            f"<code>{phone}</code>\n\n"
            "Отправьте мне этот код (например: <code>12345</code>)\n\n"
            "<b>⚠️ Важно:</b>\n"
            "• Код действителен 3-5 минут\n"
            "• Если код не пришел, отправьте /cancel и попробуйте еще раз"
        )

        await state.set_state(SetupStates.waiting_code)

        logger.info(f"Authorization code sent to user {message.from_user.id}")

    except ApiIdInvalidError:
        await message.answer(
            "❌ <b>Ошибка авторизации</b>\n\n"
            "<b>Неверный API ID или API Hash</b>\n\n"
            "Пожалуйста, проверьте данные на https://my.telegram.org\n\n"
            "Начните настройку заново: /setup"
        )
        await state.clear()
        logger.error(f"Invalid API credentials for user {message.from_user.id}")

    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка подключения</b>\n\n"
            f"Не удалось отправить код авторизации.\n\n"
            f"Ошибка: <code>{str(e)}</code>\n\n"
            "Попробуйте еще раз: /setup"
        )
        await state.clear()
        logger.error(f"Error sending code to user {message.from_user.id}: {e}", exc_info=True)


# ======================= ШАГ 4: CODE =======================

@router.message(SetupStates.waiting_code)
async def process_code(message: Message, state: FSMContext):
    """Обработка кода подтверждения"""
    code = message.text.strip().replace('-', '').replace(' ', '')

    # Валидация: должен быть только цифры
    if not code.isdigit():
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            "Код должен состоять только из цифр\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены."
        )
        return

    # Получить сохраненные данные
    data = await state.get_data()
    api_id = data['api_id']
    api_hash = data['api_hash']
    phone = data['phone']
    session_string = data['session_string']
    phone_code_hash = data.get('phone_code_hash')

    await message.answer(
        "⏳ <b>Проверка кода...</b>\n\n"
        "Пожалуйста, подождите..."
    )

    try:
        # Создать клиент с существующей сессией
        client = TelegramClient(
            StringSession(session_string),
            api_id,
            api_hash
        )

        await client.connect()

        try:
            # Попытка авторизации с кодом
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)

            # Успешная авторизация!
            session_string = client.session.save()

            await client.disconnect()

            # Сохранить в базу данных
            user_id = message.from_user.id
            db = get_db_manager()

            await db.update_user(
                user_id=user_id,
                api_id=api_id,
                api_hash=api_hash,
                phone=phone,
                session_string=session_string,
                is_authorized=True
            )

            logger.info(f"User {user_id} successfully authorized in Telegram")

            # Переход к опциональной настройке Claude API
            await message.answer(
                "✅ <b>Успешно авторизован!</b>\n\n"
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

        except SessionPasswordNeededError:
            # Нужен пароль 2FA
            await client.disconnect()

            await message.answer(
                "🔐 <b>Требуется пароль двухфакторной аутентификации</b>\n\n"
                "У вас включена двухфакторная аутентификация (2FA).\n\n"
                "Отправьте мне ваш <b>пароль</b> от Telegram:"
            )

            await state.set_state(SetupStates.waiting_password)
            logger.info(f"User {message.from_user.id} needs 2FA password")

    except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
        await message.answer(
            "❌ <b>Неверный или устаревший код</b>\n\n"
            "Возможные причины:\n"
            "• Код введен неправильно\n"
            "• Код устарел (более 3-5 минут)\n\n"
            "Начните настройку заново: /setup"
        )
        await state.clear()
        logger.error(f"Invalid/expired code for user {message.from_user.id}: {e}")

    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка авторизации</b>\n\n"
            f"Ошибка: <code>{str(e)}</code>\n\n"
            "Попробуйте еще раз: /setup"
        )
        await state.clear()
        logger.error(f"Error during sign in for user {message.from_user.id}: {e}", exc_info=True)


# ======================= ШАГ 5: PASSWORD (2FA) =======================

@router.message(SetupStates.waiting_password)
async def process_password(message: Message, state: FSMContext):
    """Обработка пароля 2FA"""
    password = message.text.strip()

    # Удалить сообщение с паролем для безопасности
    try:
        await message.delete()
    except Exception:
        pass  # Игнорируем ошибку если не удалось удалить

    # Получить сохраненные данные
    data = await state.get_data()
    api_id = data['api_id']
    api_hash = data['api_hash']
    phone = data['phone']
    session_string = data['session_string']

    status_msg = await message.answer(
        "⏳ <b>Проверка пароля...</b>\n\n"
        "Пожалуйста, подождите..."
    )

    try:
        # Создать клиент с существующей сессией
        client = TelegramClient(
            StringSession(session_string),
            api_id,
            api_hash
        )

        await client.connect()

        # Попытка авторизации с паролем
        await client.sign_in(password=password)

        # Успешная авторизация!
        session_string = client.session.save()

        await client.disconnect()

        # Сохранить в базу данных
        user_id = message.from_user.id
        db = get_db_manager()

        await db.update_user(
            user_id=user_id,
            api_id=api_id,
            api_hash=api_hash,
            phone=phone,
            session_string=session_string,
            is_authorized=True
        )

        logger.info(f"User {user_id} successfully authorized with 2FA")

        await status_msg.edit_text(
            "✅ <b>Успешно авторизован!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Шаг 3/3: Claude API (опционально)</b>\n\n"
            "Claude API используется для анализа переписок.\n\n"
            "<b>Как получить ключ:</b>\n"
            "1️⃣ Перейдите: https://console.anthropic.com/\n"
            "2️⃣ Зарегистрируйтесь или войдите\n"
            "3️⃣ Перейдите в API Keys\n"
            "4️⃣ Создайте новый ключ\n\n"
            "Отправьте мне ваш <b>Claude API ключ</b>\n"
            "или нажмите <b>Пропустить</b> (можно добавить позже через /settings)"
        )

        await message.answer(
            "⏭️ Пропустить",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="⏭️ Пропустить")]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

        await state.set_state(SetupStates.waiting_claude_key)

    except PasswordHashInvalidError:
        await status_msg.edit_text(
            "❌ <b>Неверный пароль</b>\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены."
        )
        logger.error(f"Invalid 2FA password for user {message.from_user.id}")

    except Exception as e:
        await status_msg.edit_text(
            f"❌ <b>Ошибка авторизации</b>\n\n"
            f"Ошибка: <code>{str(e)}</code>\n\n"
            "Попробуйте еще раз: /setup"
        )
        await state.clear()
        logger.error(f"Error during 2FA for user {message.from_user.id}: {e}", exc_info=True)


# ======================= ШАГ 6: CLAUDE API (OPTIONAL) =======================

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
