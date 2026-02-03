# bot/states/setup_states.py
"""FSM States для процесса onboarding (настройки пользователя)"""

from aiogram.fsm.state import State, StatesGroup


class SetupStates(StatesGroup):
    """Состояния процесса настройки нового пользователя"""

    # Сбор Telegram API ключей
    waiting_api_id = State()      # Ожидание API_ID
    waiting_api_hash = State()    # Ожидание API_HASH

    # Авторизация в Telegram через QR-код
    waiting_qr_scan = State()     # Ожидание сканирования QR-кода

    # Опциональная настройка Claude API
    waiting_claude_key = State()  # Ожидание Claude API ключа (опционально)
