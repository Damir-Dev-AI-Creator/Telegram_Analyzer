# core/bootstrap.py
"""Автоматическая инициализация приложения при первом запуске"""

import sys
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional

from .config import (
    get_app_data_dir,
    get_data_dir,
    get_base_dir,
    get_working_dir,
    get_input_folder,
    get_output_folder,
    get_logs_dir,
    is_configured
)
from .utils import (
    check_python_version,
    check_dependencies,
    setup_logging,
    is_windows,
    is_macos,
    is_linux
)


class BootstrapError(Exception):
    """Исключение при ошибке инициализации"""
    pass


class AppBootstrap:
    """
    Класс для инициализации приложения.

    Автоматически:
    - Проверяет версию Python
    - Проверяет и устанавливает зависимости
    - Создает необходимые директории
    - Настраивает логирование
    """

    MIN_PYTHON_VERSION = (3, 9)

    def __init__(self, auto_install_deps: bool = False):
        """
        Args:
            auto_install_deps: Автоматически устанавливать отсутствующие зависимости
        """
        self.auto_install_deps = auto_install_deps
        self.logger = None
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def initialize(self) -> Tuple[bool, str]:
        """
        Полная инициализация приложения.

        Returns:
            (успех, сообщение)
        """
        try:
            # 1. Проверка Python
            if not self._check_python():
                return False, self._format_errors()

            # 2. Проверка/установка зависимостей
            if not self._check_and_install_dependencies():
                return False, self._format_errors()

            # 3. Создание директорий
            self._create_directories()

            # 4. Настройка логирования
            self._setup_logging()

            # 5. Проверка конфигурации
            self._check_configuration()

            # Успех
            message = "✅ Инициализация завершена успешно"
            if self.warnings:
                message += "\n\n⚠️ Предупреждения:\n" + "\n".join(self.warnings)

            return True, message

        except Exception as e:
            self.errors.append(f"Неожиданная ошибка: {str(e)}")
            return False, self._format_errors()

    def _check_python(self) -> bool:
        """Проверка версии Python"""
        if not check_python_version(self.MIN_PYTHON_VERSION):
            self.errors.append(
                f"❌ Требуется Python {'.'.join(map(str, self.MIN_PYTHON_VERSION))}+\n"
                f"   Установлен: {sys.version}"
            )
            return False
        return True

    def _check_and_install_dependencies(self) -> bool:
        """Проверка и установка зависимостей"""
        all_installed, missing = check_dependencies()

        if all_installed:
            return True

        if not self.auto_install_deps:
            self.errors.append(
                f"❌ Отсутствуют зависимости:\n"
                f"   {', '.join(missing)}\n\n"
                f"   Установите командой:\n"
                f"   pip install {' '.join(missing)}"
            )
            return False

        # Попытка автоматической установки
        print(f"📦 Установка зависимостей: {', '.join(missing)}")
        try:
            for package in missing:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", package,
                    "--quiet", "--break-system-packages"
                ])

            # Повторная проверка
            all_installed, still_missing = check_dependencies()
            if not all_installed:
                self.errors.append(
                    f"❌ Не удалось установить: {', '.join(still_missing)}"
                )
                return False

            return True

        except subprocess.CalledProcessError as e:
            self.errors.append(f"❌ Ошибка установки зависимостей: {e}")
            return False

    def _create_directories(self) -> None:
        """Создание необходимых директорий"""
        # Выводим базовую директорию
        base = get_base_dir()
        print(f"📍 Базовая директория: {base}")
        print()

        directories = [
            ("Данные (.env, сессия)", get_data_dir()),
            ("Входные CSV", get_input_folder()),
            ("Выходные DOCX", get_output_folder()),
            ("Логи", get_logs_dir()),
        ]

        for name, path in directories:
            try:
                path.mkdir(parents=True, exist_ok=True)
                # Показываем относительный путь от базовой директории
                try:
                    rel_path = path.relative_to(base)
                    print(f"📁 {name}: ./{rel_path}")
                except ValueError:
                    print(f"📁 {name}: {path}")
            except Exception as e:
                self.warnings.append(f"Не удалось создать {name}: {e}")

    def _setup_logging(self) -> None:
        """Настройка логирования"""
        try:
            self.logger = setup_logging(get_logs_dir())
            self.logger.info("Приложение инициализировано")
        except Exception as e:
            self.warnings.append(f"Ошибка настройки логирования: {e}")

    def _check_configuration(self) -> None:
        """Проверка наличия конфигурации"""
        if not is_configured():
            self.warnings.append(
                "Приложение не настроено. При запуске откроется окно настройки."
            )

    def _format_errors(self) -> str:
        """Форматирование списка ошибок"""
        return "\n\n".join(self.errors)

    @staticmethod
    def quick_check() -> Tuple[bool, Optional[str]]:
        """
        Быстрая проверка готовности к запуску.
        Не создает файлы и папки.

        Returns:
            (готов_к_запуску, причина_если_нет)
        """
        # Python версия
        if not check_python_version((3, 9)):
            return False, f"Требуется Python 3.9+, установлен {sys.version}"

        # Зависимости
        all_ok, missing = check_dependencies()
        if not all_ok:
            return False, f"Отсутствуют пакеты: {', '.join(missing)}"

        return True, None


def run_bootstrap(auto_install: bool = False) -> bool:
    """
    Удобная функция для запуска инициализации.

    Args:
        auto_install: Автоматически устанавливать зависимости

    Returns:
        True если инициализация успешна
    """
    print("=" * 50)
    print("  🚀 Инициализация Ysell Analyzer")
    print("=" * 50)
    print()

    bootstrap = AppBootstrap(auto_install_deps=auto_install)
    success, message = bootstrap.initialize()

    print()
    print(message)
    print()

    return success


if __name__ == "__main__":
    # Запуск с автоустановкой зависимостей
    import argparse

    parser = argparse.ArgumentParser(description="Инициализация Ysell Analyzer")
    parser.add_argument(
        "--auto-install",
        action="store_true",
        help="Автоматически устанавливать отсутствующие зависимости"
    )

    args = parser.parse_args()
    success = run_bootstrap(auto_install=args.auto_install)
    sys.exit(0 if success else 1)