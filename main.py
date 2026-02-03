#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ysell Analyzer - Главная точка входа

Приложение для экспорта и анализа Telegram чатов
с использованием Claude API (Anthropic).

Использование:
    python main.py           # GUI режим (по умолчанию)
    python main.py --console # Консольный режим
    python main.py --init    # Только инициализация
    python main.py --paths   # Показать пути
"""

import sys
import os

# Минимальная версия Python
MIN_PYTHON = (3, 9)


def check_python_version():
    """Проверка версии Python перед любыми импортами"""
    if sys.version_info < MIN_PYTHON:
        print(f"❌ Ошибка: требуется Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} или выше")
        print(f"   Текущая версия: {sys.version}")
        print()
        print("Установите актуальную версию Python:")
        print("  - Windows: https://www.python.org/downloads/")
        print("  - macOS: brew install python")
        print("  - Linux: sudo apt install python3.11")
        sys.exit(1)


def setup_paths():
    """Настройка путей для импорта модулей"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)


def check_dependencies_quick(mode='gui'):
    """Быстрая проверка критических зависимостей

    Args:
        mode: 'gui' для GUI режима (с customtkinter), 'bot' для бота (без GUI)
    """
    # Базовые зависимости для всех режимов
    critical_packages = {
        'telethon': 'telethon',
        'pandas': 'pandas',
        'anthropic': 'anthropic',
        'docx': 'python-docx',
    }

    # Добавить GUI зависимости только для GUI режима
    if mode == 'gui':
        critical_packages['customtkinter'] = 'customtkinter'

    # Добавить bot зависимости только для bot режима
    if mode == 'bot':
        critical_packages['aiogram'] = 'aiogram'

    missing = []
    for module, package in critical_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print("❌ Отсутствуют критические зависимости:")
        print(f"   {', '.join(missing)}")
        print()
        print("Установите зависимости командой:")
        print(f"   pip install {' '.join(missing)}")
        print()
        if mode == 'bot':
            print("Или установите серверные зависимости:")
            print("   pip install -r requirements-server.txt")
        else:
            print("Или установите все сразу:")
            print("   pip install -r requirements.txt")
        return False

    return True


def show_paths():
    """Показать информацию о путях"""
    from core.config import (
        get_app_data_dir,
        get_working_dir,
        get_input_folder,
        get_output_folder,
        get_env_path,
        get_session_path,
        get_logs_dir
    )
    
    print("\n📁 Пути приложения:")
    print(f"  Конфигурация (.env):  {get_env_path()}")
    print(f"  Данные приложения:    {get_app_data_dir()}")
    print(f"  Рабочая директория:   {get_working_dir()}")
    print(f"  Входные CSV:          {get_input_folder()}")
    print(f"  Выходные DOCX:        {get_output_folder()}")
    print(f"  Логи:                 {get_logs_dir()}")
    print(f"  Сессия Telegram:      {get_session_path()}")


def run_gui():
    """Запуск графического интерфейса"""
    from core.bootstrap import AppBootstrap
    from core.config import is_configured, validate_config
    
    # Инициализация
    bootstrap = AppBootstrap(auto_install_deps=False)
    success, message = bootstrap.initialize()
    
    if not success:
        print(message)
        try:
            import customtkinter as ctk
            from tkinter import messagebox
            
            root = ctk.CTk()
            root.withdraw()
            messagebox.showerror("Ошибка инициализации", message)
            root.destroy()
        except Exception:
            pass
        sys.exit(1)
    
    # Проверка настройки
    if not is_configured():
        print("⚙️ Первый запуск - требуется настройка...")
        from ui.setup import show_setup_window
        
        def on_complete():
            print("✅ Настройка завершена!")
            _launch_main_gui()
        
        show_setup_window(on_complete)
    else:
        is_valid, msg = validate_config()
        if not is_valid:
            print(f"⚠️ Конфигурация невалидна: {msg}")
            from ui.setup import show_setup_window
            show_setup_window(lambda: _launch_main_gui())
        else:
            _launch_main_gui()


def _launch_main_gui():
    """Запуск основного GUI"""
    try:
        from ui.app import run_gui
        run_gui()
    except Exception as e:
        print(f"❌ Ошибка запуска GUI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_console():
    """Запуск консольного режима"""
    from core.bootstrap import AppBootstrap
    
    bootstrap = AppBootstrap(auto_install_deps=False)
    success, message = bootstrap.initialize()
    
    if not success:
        print(message)
        sys.exit(1)
    
    from services.launcher import main_menu
    main_menu()


def run_init_only():
    """Только инициализация без запуска"""
    from core.bootstrap import run_bootstrap
    success = run_bootstrap(auto_install=True)
    sys.exit(0 if success else 1)


def run_bot():
    """Запуск Telegram бота"""
    from core.bootstrap import AppBootstrap

    # Инициализация
    bootstrap = AppBootstrap(auto_install_deps=False)
    success, message = bootstrap.initialize()

    if not success:
        print(message)
        sys.exit(1)

    # Запуск бота
    from bot.main import run
    run()


def print_help():
    """Вывод справки"""
    print("""
Использование: python main.py [опции]

Опции:
  (без опций)    Запуск GUI (по умолчанию)
  --bot, -b      Запуск Telegram бота
  --console, -c  Консольный режим
  --init, -i     Только инициализация (создание папок)
  --paths, -p    Показать пути к папкам
  --version, -v  Показать версию
  --help, -h     Показать эту справку

Примеры:
  python main.py              # Запуск GUI
  python main.py --bot        # Запуск Telegram бота
  python main.py --console    # Консольный режим
  python main.py --init       # Инициализация

Документация: https://github.com/yourrepo/ysell-analyzer
    """)


def main():
    """Главная функция"""
    # 1. Проверка Python
    check_python_version()
    
    # 2. Настройка путей
    setup_paths()
    
    # 3. Вывод заголовка
    print("=" * 50)
    print("  🚀 Ysell Analyzer v0.2.0 (Claude API)")
    print("=" * 50)
    print()
    
    # 4. Обработка аргументов
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ['--help', '-h']:
            print_help()
            sys.exit(0)
        
        if arg in ['--version', '-v']:
            print("Ysell Analyzer v0.2.0")
            sys.exit(0)
        
        if arg in ['--paths', '-p']:
            # Для показа путей не требуются все зависимости
            show_paths()
            sys.exit(0)

        if arg in ['--init', '-i']:
            # Для инициализации не требуются все зависимости
            run_init_only()

        elif arg in ['--bot', '-b']:
            print("🤖 Запуск Telegram бота...")
            if not check_dependencies_quick(mode='bot'):
                sys.exit(1)
            try:
                run_bot()
            except KeyboardInterrupt:
                print("\n\n👋 Бот остановлен")
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

        elif arg in ['--console', '-c']:
            print("📟 Запуск в консольном режиме...")
            if not check_dependencies_quick(mode='gui'):  # Console может использовать GUI для setup
                sys.exit(1)
            try:
                run_console()
            except KeyboardInterrupt:
                print("\n\n👋 Программа завершена")
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                sys.exit(1)

        else:
            print(f"❌ Неизвестный аргумент: {arg}")
            print("Используйте --help для справки")
            sys.exit(1)
    else:
        # GUI режим по умолчанию
        print("🖥️ Запуск в режиме GUI...")
        if not check_dependencies_quick():
            sys.exit(1)
        try:
            run_gui()
        except KeyboardInterrupt:
            print("\n\n👋 Программа завершена")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
