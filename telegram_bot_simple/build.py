"""
Скрипт для компиляции бота в standalone исполняемый файл
Использует PyInstaller
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def build_executable():
    """Собрать исполняемый файл"""

    print("=" * 60)
    print("   Ysell Analyzer Bot - Компиляция в исполняемый файл")
    print("=" * 60)
    print()

    # Проверка PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller не установлен!")
        print("📦 Установите: pip install pyinstaller")
        return False

    # Определяем платформу
    system = platform.system()
    print(f"🖥️  Платформа: {system}")
    print()

    # Параметры сборки
    script_name = "bot_simple.py"
    app_name = "YsellAnalyzer"

    # Базовые параметры
    params = [
        "pyinstaller",
        "--onefile",
        "--name=" + app_name,
        "--clean",
    ]

    # Добавляем services директорию
    services_path = str(Path(__file__).parent.parent / "services")
    params.append(f"--add-data={services_path}{os.pathsep}services")

    # Добавляем иконку если есть
    icon_path = Path(__file__).parent / "icon.ico"
    if icon_path.exists():
        params.append(f"--icon={icon_path}")

    # Скрываем консоль на Windows (опционально)
    # if system == "Windows":
    #     params.append("--noconsole")

    # Добавляем скрипт
    params.append(script_name)

    print("🔧 Параметры сборки:")
    for param in params:
        print(f"   {param}")
    print()

    # Запускаем сборку
    try:
        print("🚀 Начинаю сборку...")
        print("   Это может занять несколько минут...")
        print()

        result = subprocess.run(params, check=True)

        print()
        print("=" * 60)
        print("✅ Сборка завершена успешно!")
        print("=" * 60)
        print()

        # Путь к исполняемому файлу
        if system == "Windows":
            exe_file = f"dist/{app_name}.exe"
        else:
            exe_file = f"dist/{app_name}"

        if os.path.exists(exe_file):
            file_size = os.path.getsize(exe_file) / (1024 * 1024)
            print(f"📦 Файл: {exe_file}")
            print(f"📊 Размер: {file_size:.1f} MB")
            print()
            print("🎉 Готово к распространению!")
            print()
            print("📝 Инструкция для пользователей:")
            print("   1. Скачайте файл")
            print("   2. Запустите")
            print("   3. Введите токен бота при первом запуске")
            print("   4. Бот готов к работе!")

        return True

    except subprocess.CalledProcessError as e:
        print()
        print("❌ Ошибка сборки!")
        print(f"   {e}")
        return False


def clean_build_files():
    """Очистить временные файлы сборки"""
    print()
    print("🧹 Очистка временных файлов...")

    import shutil

    dirs_to_remove = ['build', '__pycache__']
    files_to_remove = ['*.spec']

    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   Удалено: {dir_name}/")

    import glob
    for pattern in files_to_remove:
        for file_path in glob.glob(pattern):
            os.remove(file_path)
            print(f"   Удалено: {file_path}")

    print("✅ Очистка завершена")


def main():
    """Главная функция"""

    # Проверка что запущено из правильной директории
    if not os.path.exists("bot_simple.py"):
        print("❌ Запустите скрипт из директории telegram_bot_simple/")
        return

    # Сборка
    success = build_executable()

    if success:
        # Очистка
        clean_build_files()

        print()
        print("=" * 60)
        print("   Сборка завершена!")
        print("=" * 60)
    else:
        print()
        print("❌ Сборка не удалась. Проверьте ошибки выше.")


if __name__ == "__main__":
    main()
