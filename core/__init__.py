# core/__init__.py
"""Ядро приложения - конфигурация, утилиты, инициализация"""

from .config import (
    get_base_dir,
    get_data_dir,
    get_app_data_dir,
    get_working_dir,
    get_input_folder,
    get_output_folder,
    get_logs_dir,
    get_env_path,
    get_session_path,
    is_configured,
    validate_config,
    reload_config,
    save_config,
    API_ID,
    API_HASH,
    PHONE,
    CLAUDE_API_KEY,
    EXCLUDE_USER_ID,
    EXCLUDE_USERNAME,
    EXPORT_FOLDER,
    OUTPUT_FOLDER,
)

from .utils import (
    ClipboardManager,
    setup_platform_specifics,
    is_windows,
    is_macos,
    is_linux,
    get_modifier_key,
    check_dependencies,
    check_python_version,
    validate_date,
    validate_phone,
    validate_api_hash,
    clean_filename,
    safe_remove_file,
    get_csv_files,
)

from .bootstrap import AppBootstrap, run_bootstrap

__all__ = [
    # Config
    'get_app_data_dir',
    'get_working_dir',
    'get_input_folder',
    'get_output_folder',
    'is_configured',
    'validate_config',
    'reload_config',
    'save_config',
    # Utils
    'ClipboardManager',
    'setup_platform_specifics',
    'is_windows',
    'is_macos',
    'is_linux',
    # Bootstrap
    'AppBootstrap',
    'run_bootstrap',
]