# bot/states/setup_states.py
"""FSM States для процесса onboarding (настройки пользователя)"""

from aiogram.fsm.state import State, StatesGroup


class SetupStates(StatesGroup):
    """Состояния процесса настройки нового пользователя"""

    # Сбор Telegram API ключей
    waiting_api_id = State()      # Ожидание API_ID
    waiting_api_hash = State()    # Ожидание API_HASH
    waiting_phone = State()       # Ожидание номера телефона

    # Авторизация в Telegram
    waiting_code = State()        # Ожидание кода подтверждения
    waiting_password = State()    # Ожидание пароля 2FA (если включен)

    # Опциональная настройка Claude API
    waiting_claude_key = State()  # Ожидание Claude API ключа (опционально)
