# core/config.py
"""Кросс-платформенная конфигурация приложения (Portable режим)"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv


# ============================================================================
# Определение базовой директории (Portable режим)
# ============================================================================

def get_base_dir() -> Path:
    """
    Возвращает базовую директорию приложения.

    Portable режим: все файлы хранятся рядом с исполняемым файлом.

    - Для .exe (PyInstaller): папка где лежит .exe
    - Для .py (разработка): папка где лежит main.py
    """
    if getattr(sys, 'frozen', False):
        # Запущено как скомпилированное приложение (PyInstaller/Nuitka)
        # sys.executable = путь к .exe файлу
        base = Path(sys.executable).parent
    else:
        # Запущено как Python скрипт
        # Ищем корень проекта (где лежит main.py)
        base = Path(__file__).parent.parent

    return base


def get_data_dir() -> Path:
    """
    Возвращает директорию для данных приложения.
    Создаёт папку 'data' рядом с приложением.

    Структура:
    YsellAnalyzer.exe (или main.py)
    └── data/
        ├── .env
        ├── telegram_session.session
        └── logs/
    """
    data_dir = get_base_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_working_dir() -> Path:
    """
    Возвращает рабочую директорию для CSV и DOCX файлов.
    Создаёт папки рядом с приложением.

    Структура:
    YsellAnalyzer.exe
    ├── data/
    ├── input_csv/      <- CSV файлы для анализа
    └── output_docx/    <- Результаты анализа
    """
    return get_base_dir()


def get_env_path() -> Path:
    """Путь к файлу .env"""
    return get_data_dir() / ".env"


def get_session_path() -> Path:
    """Путь к файлу сессии Telegram (без расширения, Telethon добавит .session)"""
    return get_data_dir() / "telegram_session"


def get_logs_dir() -> Path:
    """Путь к директории логов"""
    logs_dir = get_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_input_folder() -> Path:
    """Путь к папке с входными CSV файлами"""
    folder = get_working_dir() / "input_csv"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_output_folder() -> Path:
    """Путь к папке с выходными DOCX файлами"""
    folder = get_working_dir() / "output_docx"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# Для обратной совместимости
def get_app_data_dir() -> Path:
    """Алиас для get_data_dir() (обратная совместимость)"""
    return get_data_dir()


# ============================================================================
# Загрузка конфигурации
# ============================================================================

# Загружаем .env из правильного места
_env_path = get_env_path()
if _env_path.exists():
    load_dotenv(_env_path)


def is_configured() -> bool:
    """Проверка, настроено ли приложение"""
    return get_env_path().exists()


def get_missing_vars(mode: str = "legacy") -> list:
    """
    Получить список отсутствующих переменных

    Args:
        mode: "bot" для multi-user бота (только BOT_TOKEN),
              "legacy" для GUI/CLI (API_ID, API_HASH, etc)
    """
    if mode == "bot":
        # Для бота нужен только BOT_TOKEN
        required_vars = ['BOT_TOKEN']
    else:
        # Для legacy GUI/CLI режима
        required_vars = ['API_ID', 'API_HASH', 'PHONE', 'CLAUDE_API_KEY']

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.strip() == "":
            missing.append(var)

    return missing


# ============================================================================
# Переменные конфигурации
# ============================================================================

def _get_int(key: str, default: int = 0) -> int:
    """Безопасное получение int из env"""
    value = os.getenv(key)
    if value and value.strip():
        try:
            return int(value.strip())
        except ValueError:
            pass
    return default


def _get_str(key: str, default: str = "") -> str:
    """Безопасное получение str из env"""
    value = os.getenv(key)
    return value.strip() if value else default


# Основные параметры
API_ID: int = _get_int("API_ID", 0)
API_HASH: str = _get_str("API_HASH", "")
PHONE: str = _get_str("PHONE", "")
CLAUDE_API_KEY: str = _get_str("CLAUDE_API_KEY", "")

# Опциональные параметры
EXCLUDE_USER_ID: int = _get_int("EXCLUDE_USER_ID", 0)
EXCLUDE_USERNAME: str = _get_str("EXCLUDE_USERNAME", "")

# Telegram Bot параметры (опциональные, для работы бота)
BOT_TOKEN: str = _get_str("BOT_TOKEN", "")
OWNER_ID: int = _get_int("OWNER_ID", 0)

# Пути (используем кросс-платформенные)
EXPORT_FOLDER: str = str(get_input_folder())
OUTPUT_FOLDER: str = str(get_output_folder())
SESSION_PATH: str = str(get_session_path())
SESSION_FILE: str = SESSION_PATH  # Alias for legacy compatibility


# ============================================================================
# Валидация
# ============================================================================

def validate_config(mode: str = "legacy") -> Tuple[bool, str]:
    """
    Валидация конфигурации

    Args:
        mode: "bot" для multi-user бота,
              "legacy" для GUI/CLI режима
    """
    if not is_configured():
        # Для бота .env необязателен, создастся автоматически
        if mode == "bot":
            return True, "Bot mode: .env will be created automatically"
        return False, "Файл конфигурации не найден"

    missing = get_missing_vars(mode)
    if missing:
        return False, f"Отсутствуют переменные: {', '.join(missing)}"

    # Для режима бота проверяем только BOT_TOKEN
    if mode == "bot":
        if not BOT_TOKEN:
            return False, "BOT_TOKEN не настроен"
        return True, "Bot configuration valid"

    # Для legacy режима проверяем все переменные
    if API_ID == 0:
        return False, "API_ID не настроен или имеет неверный формат"

    if not API_HASH:
        return False, "API_HASH не настроен"

    if not PHONE:
        return False, "PHONE не настроен"

    if not CLAUDE_API_KEY:
        return False, "CLAUDE_API_KEY не настроен"

    return True, "Конфигурация валидна"


def reload_config():
    """Перезагрузка конфигурации из .env файла"""
    global API_ID, API_HASH, PHONE, CLAUDE_API_KEY
    global EXCLUDE_USER_ID, EXCLUDE_USERNAME
    global BOT_TOKEN, OWNER_ID

    load_dotenv(get_env_path(), override=True)

    API_ID = _get_int("API_ID", 0)
    API_HASH = _get_str("API_HASH", "")
    PHONE = _get_str("PHONE", "")
    CLAUDE_API_KEY = _get_str("CLAUDE_API_KEY", "")
    EXCLUDE_USER_ID = _get_int("EXCLUDE_USER_ID", 0)
    EXCLUDE_USERNAME = _get_str("EXCLUDE_USERNAME", "")
    BOT_TOKEN = _get_str("BOT_TOKEN", "")
    OWNER_ID = _get_int("OWNER_ID", 0)


def save_config(
        api_id: str,
        api_hash: str,
        phone: str,
        claude_api_key: str,
        exclude_user_id: str = "0",
        exclude_username: str = ""
) -> None:
    """Сохранение конфигурации в .env файл"""
    env_content = f"""# Telegram API Configuration
# Получите на https://my.telegram.org/apps
API_ID={api_id}
API_HASH={api_hash}
PHONE={phone}

# Claude API Configuration (Anthropic)
# Получите на https://console.anthropic.com/settings/keys
CLAUDE_API_KEY={claude_api_key}

# Optional Settings
EXCLUDE_USER_ID={exclude_user_id}
EXCLUDE_USERNAME={exclude_username}
"""

    env_path = get_env_path()
    env_path.write_text(env_content, encoding='utf-8')
    reload_config()


# ============================================================================
# Информация о системе
# ============================================================================

def get_system_info() -> dict:
    """Возвращает информацию о системе"""
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": sys.version,
        "app_data_dir": str(get_app_data_dir()),
        "working_dir": str(get_working_dir()),
        "env_path": str(get_env_path()),
    }


# Вывод информации при импорте (только в debug режиме)
if os.environ.get("YSELL_DEBUG"):
    print(f"📁 App data: {get_app_data_dir()}")
    print(f"📁 Working dir: {get_working_dir()}")
    is_valid, message = validate_config()
    print(f"⚙️ Config: {message}")