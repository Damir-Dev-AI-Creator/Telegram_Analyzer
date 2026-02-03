"""
Автоматическая настройка при первом запуске бота
Запускается автоматически если BOT_TOKEN не настроен
"""

import os
import sys
from pathlib import Path


def create_minimal_env(bot_token: str) -> Path:
    """
    Создает минимальный .env файл с BOT_TOKEN

    Args:
        bot_token: Telegram Bot Token

    Returns:
        Path к созданному .env файлу
    """
    # Определить путь к .env
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    env_path = data_dir / ".env"

    # Создать содержимое
    env_content = f"""# Telegram Analyzer Bot - Auto-generated Configuration
# Создано автоматически при первом запуске

# Bot Token (обязательно)
BOT_TOKEN={bot_token}

# ===========================================
# Multi-User Mode
# ===========================================
# Все остальные настройки per-user через /setup:
# - Telegram API credentials (API_ID, API_HASH)
# - Claude API key
# - Session data (encrypted in database)
"""

    env_path.write_text(env_content, encoding='utf-8')
    return env_path


def validate_token_format(token: str) -> tuple[bool, str]:
    """
    Проверка формата Bot Token

    Returns:
        (is_valid, error_message)
    """
    token = token.strip()

    if not token:
        return False, "Токен не может быть пустым"

    if ':' not in token:
        return False, "Неверный формат токена (должен содержать ':')"

    parts = token.split(':')
    if len(parts) != 2:
        return False, "Неверный формат токена"

    if not parts[0].isdigit():
        return False, "Первая часть токена должна быть числом"

    if len(parts[1]) < 20:
        return False, "Вторая часть токена слишком короткая"

    return True, ""


def run_gui_setup() -> str | None:
    """
    Запустить GUI setup через tkinter

    Returns:
        Bot Token или None если отменено
    """
    try:
        import tkinter as tk
        from tkinter import messagebox, ttk
    except ImportError:
        # tkinter недоступен, вернем None
        return None

    result = {"token": None}

    def on_save():
        token = token_entry.get().strip()
        is_valid, error = validate_token_format(token)

        if not is_valid:
            messagebox.showerror("Ошибка", error)
            return

        result["token"] = token
        root.quit()
        root.destroy()

    def on_cancel():
        root.quit()
        root.destroy()

    def on_help():
        help_text = """Как получить Bot Token:

1. Откройте Telegram
2. Найдите @BotFather
3. Отправьте /newbot
4. Следуйте инструкциям
5. Скопируйте токен

Формат токена:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"""
        messagebox.showinfo("Справка", help_text)

    # Создать окно
    root = tk.Tk()
    root.title("Telegram Analyzer Bot - Первая настройка")
    root.geometry("600x400")
    root.resizable(False, False)

    # Центрировать окно
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (600 // 2)
    y = (root.winfo_screenheight() // 2) - (400 // 2)
    root.geometry(f"600x400+{x}+{y}")

    # Стиль
    style = ttk.Style()
    style.theme_use('clam')

    # Главный frame
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Заголовок
    title_label = tk.Label(
        main_frame,
        text="🤖 Добро пожаловать в Telegram Analyzer Bot!",
        font=("Arial", 16, "bold"),
        fg="#0088cc"
    )
    title_label.pack(pady=(0, 10))

    # Описание
    desc_text = """Для запуска бота необходим Bot Token от @BotFather.

После первой настройки каждый пользователь сможет
настроить свои credentials через команду /setup в боте."""

    desc_label = tk.Label(
        main_frame,
        text=desc_text,
        font=("Arial", 10),
        justify=tk.LEFT,
        wraplength=550
    )
    desc_label.pack(pady=(0, 20))

    # Разделитель
    separator1 = ttk.Separator(main_frame, orient='horizontal')
    separator1.pack(fill='x', pady=10)

    # Инструкция
    instruction_label = tk.Label(
        main_frame,
        text="Введите Bot Token:",
        font=("Arial", 11, "bold")
    )
    instruction_label.pack(anchor=tk.W, pady=(10, 5))

    # Поле ввода токена
    token_entry = ttk.Entry(main_frame, width=60, font=("Courier", 10))
    token_entry.pack(pady=(0, 5))
    token_entry.focus()

    # Пример
    example_label = tk.Label(
        main_frame,
        text="Пример: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        font=("Arial", 8),
        fg="gray"
    )
    example_label.pack(anchor=tk.W, pady=(0, 20))

    # Разделитель
    separator2 = ttk.Separator(main_frame, orient='horizontal')
    separator2.pack(fill='x', pady=10)

    # Кнопки
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=(10, 0))

    help_button = ttk.Button(
        button_frame,
        text="❓ Как получить токен?",
        command=on_help
    )
    help_button.pack(side=tk.LEFT, padx=5)

    cancel_button = ttk.Button(
        button_frame,
        text="Отмена",
        command=on_cancel
    )
    cancel_button.pack(side=tk.LEFT, padx=5)

    save_button = ttk.Button(
        button_frame,
        text="✅ Сохранить и запустить",
        command=on_save
    )
    save_button.pack(side=tk.LEFT, padx=5)

    # Bind Enter
    token_entry.bind('<Return>', lambda e: on_save())

    # Запустить
    root.mainloop()

    return result["token"]


def run_console_setup() -> str | None:
    """
    Запустить консольный setup (если GUI недоступен)

    Returns:
        Bot Token или None если отменено
    """
    print()
    print("=" * 70)
    print("🤖 Telegram Analyzer Bot - Первая настройка")
    print("=" * 70)
    print()
    print("Для запуска бота необходим Bot Token от @BotFather.")
    print()
    print("📋 Как получить Bot Token:")
    print("1. Откройте Telegram")
    print("2. Найдите @BotFather (https://t.me/BotFather)")
    print("3. Отправьте команду /newbot")
    print("4. Следуйте инструкциям для создания бота")
    print("5. Скопируйте токен (формат: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz)")
    print()
    print("=" * 70)
    print()

    while True:
        try:
            token = input("Введите Bot Token (или 'exit' для выхода): ").strip()

            if token.lower() in ('exit', 'quit', 'q'):
                print("\n❌ Настройка отменена")
                return None

            is_valid, error = validate_token_format(token)
            if not is_valid:
                print(f"\n❌ Ошибка: {error}")
                print("Попробуйте еще раз.\n")
                continue

            return token

        except KeyboardInterrupt:
            print("\n\n❌ Настройка прервана пользователем")
            return None
        except EOFError:
            print("\n\n❌ Настройка прервана")
            return None


def run_first_time_setup() -> bool:
    """
    Запустить настройку первого запуска

    Returns:
        True если настройка завершена успешно, False если отменена
    """
    print("\n⚠️  BOT_TOKEN не настроен. Запуск первоначальной настройки...\n")

    # Попробовать GUI сначала
    token = run_gui_setup()

    # Если GUI не сработал, использовать консоль
    if token is None:
        print("ℹ️  GUI недоступен, используется консольный режим\n")
        token = run_console_setup()

    if token is None:
        return False

    # Создать .env файл
    try:
        env_path = create_minimal_env(token)
        print()
        print("=" * 70)
        print("✅ Настройка завершена успешно!")
        print("=" * 70)
        print(f"📁 Создан файл: {env_path}")
        print()
        print("🚀 Запуск бота...")
        print("=" * 70)
        print()
        return True
    except Exception as e:
        print(f"\n❌ Ошибка при создании .env: {e}")
        return False


def check_bot_token_configured() -> bool:
    """
    Проверить, настроен ли BOT_TOKEN

    Returns:
        True если настроен, False если нужна первоначальная настройка
    """
    # Проверить переменную окружения
    token = os.getenv("BOT_TOKEN", "").strip()
    if token:
        return True

    # Проверить .env файлы
    env_paths = [
        Path("data/.env"),
        Path(".env")
    ]

    for env_path in env_paths:
        if env_path.exists():
            content = env_path.read_text(encoding='utf-8')
            for line in content.split('\n'):
                if line.startswith('BOT_TOKEN='):
                    value = line.split('=', 1)[1].strip()
                    if value and 'your_bot_token' not in value.lower():
                        return True

    return False


if __name__ == "__main__":
    # Тест
    if not check_bot_token_configured():
        success = run_first_time_setup()
        sys.exit(0 if success else 1)
    else:
        print("✅ BOT_TOKEN уже настроен")
