# core/utils.py
"""Общие утилиты для приложения"""

import os
import sys
import platform
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Callable


# ============================================================================
# Определение ОС
# ============================================================================

def is_windows() -> bool:
    return platform.system() == "Windows"


def is_macos() -> bool:
    return platform.system() == "Darwin"


def is_linux() -> bool:
    return platform.system() == "Linux"


def get_modifier_key() -> str:
    """Возвращает модификатор для текущей ОС (Cmd на macOS, Ctrl на остальных)"""
    return "Command" if is_macos() else "Control"


# ============================================================================
# Кросс-платформенная работа с буфером обмена и горячие клавиши
# ============================================================================

class ClipboardManager:
    """
    Универсальный менеджер буфера обмена и горячих клавиш для tkinter и customtkinter.

    Поддерживаемые команды:
    - Ctrl+V / Cmd+V — Вставить
    - Ctrl+C / Cmd+C — Копировать
    - Ctrl+X / Cmd+X — Вырезать
    - Ctrl+A / Cmd+A — Выделить всё
    - Ctrl+Z / Cmd+Z — Отменить
    - Ctrl+Y / Cmd+Shift+Z — Повторить
    - Ctrl+Backspace / Opt+Backspace — Удалить слово назад
    - Ctrl+Delete / Opt+Delete — Удалить слово вперёд
    - Home / Cmd+Left — В начало строки
    - End / Cmd+Right — В конец строки
    - Ctrl+Home / Cmd+Up — В начало текста
    - Ctrl+End / Cmd+Down — В конец текста
    - Ctrl+Left / Opt+Left — Слово назад
    - Ctrl+Right / Opt+Right — Слово вперёд
    - Ctrl+Shift+Left / Opt+Shift+Left — Выделить слово назад
    - Ctrl+Shift+Right / Opt+Shift+Right — Выделить слово вперёд
    """

    @staticmethod
    def bind_all_shortcuts(widget, root):
        """
        Привязка ВСЕХ стандартных горячих клавиш к виджету.

        Args:
            widget: CTkEntry, CTkTextbox или другой виджет с поддержкой ввода
            root: Корневое окно (CTk или Tk)
        """
        mod = get_modifier_key()  # Command на macOS, Control на остальных
        alt = "Option" if is_macos() else "Alt"

        # Получаем внутренний tkinter виджет для CTk виджетов
        inner_widget = ClipboardManager._get_inner_widget(widget)
        target = inner_widget if inner_widget else widget

        # === БУФЕР ОБМЕНА ===
        for key in ['v', 'V']:
            target.bind(f'<{mod}-{key}>', lambda e, w=widget, r=root: ClipboardManager.paste(w, r))

        for key in ['c', 'C']:
            target.bind(f'<{mod}-{key}>', lambda e, w=widget, r=root: ClipboardManager.copy(w, r))

        for key in ['x', 'X']:
            target.bind(f'<{mod}-{key}>', lambda e, w=widget, r=root: ClipboardManager.cut(w, r))

        for key in ['a', 'A']:
            target.bind(f'<{mod}-{key}>', lambda e, w=widget: ClipboardManager.select_all(w))

        # === ОТМЕНА / ПОВТОР ===
        for key in ['z', 'Z']:
            target.bind(f'<{mod}-{key}>', lambda e, w=widget: ClipboardManager.undo(w))

        # Redo: Ctrl+Y (Windows/Linux) или Cmd+Shift+Z (macOS)
        if is_macos():
            target.bind(f'<{mod}-Shift-z>', lambda e, w=widget: ClipboardManager.redo(w))
            target.bind(f'<{mod}-Shift-Z>', lambda e, w=widget: ClipboardManager.redo(w))
        else:
            for key in ['y', 'Y']:
                target.bind(f'<{mod}-{key}>', lambda e, w=widget: ClipboardManager.redo(w))

        # === УДАЛЕНИЕ СЛОВ ===
        # Ctrl+Backspace / Option+Backspace — удалить слово назад
        if is_macos():
            target.bind('<Option-BackSpace>', lambda e, w=widget: ClipboardManager.delete_word_back(w))
        else:
            target.bind('<Control-BackSpace>', lambda e, w=widget: ClipboardManager.delete_word_back(w))

        # Ctrl+Delete / Option+Delete — удалить слово вперёд
        if is_macos():
            target.bind('<Option-Delete>', lambda e, w=widget: ClipboardManager.delete_word_forward(w))
        else:
            target.bind('<Control-Delete>', lambda e, w=widget: ClipboardManager.delete_word_forward(w))

        # === НАВИГАЦИЯ ===
        # Home / Cmd+Left — в начало строки
        if is_macos():
            target.bind('<Command-Left>', lambda e, w=widget: ClipboardManager.go_line_start(w))
        target.bind('<Home>', lambda e, w=widget: ClipboardManager.go_line_start(w))

        # End / Cmd+Right — в конец строки
        if is_macos():
            target.bind('<Command-Right>', lambda e, w=widget: ClipboardManager.go_line_end(w))
        target.bind('<End>', lambda e, w=widget: ClipboardManager.go_line_end(w))

        # Ctrl+Home / Cmd+Up — в начало текста
        if is_macos():
            target.bind('<Command-Up>', lambda e, w=widget: ClipboardManager.go_text_start(w))
        else:
            target.bind('<Control-Home>', lambda e, w=widget: ClipboardManager.go_text_start(w))

        # Ctrl+End / Cmd+Down — в конец текста
        if is_macos():
            target.bind('<Command-Down>', lambda e, w=widget: ClipboardManager.go_text_end(w))
        else:
            target.bind('<Control-End>', lambda e, w=widget: ClipboardManager.go_text_end(w))

        # Ctrl+Left / Option+Left — слово назад
        if is_macos():
            target.bind('<Option-Left>', lambda e, w=widget: ClipboardManager.word_back(w))
        else:
            target.bind('<Control-Left>', lambda e, w=widget: ClipboardManager.word_back(w))

        # Ctrl+Right / Option+Right — слово вперёд
        if is_macos():
            target.bind('<Option-Right>', lambda e, w=widget: ClipboardManager.word_forward(w))
        else:
            target.bind('<Control-Right>', lambda e, w=widget: ClipboardManager.word_forward(w))

        # === ВЫДЕЛЕНИЕ С НАВИГАЦИЕЙ ===
        # Shift+Home / Cmd+Shift+Left — выделить до начала строки
        if is_macos():
            target.bind('<Command-Shift-Left>', lambda e, w=widget: ClipboardManager.select_to_line_start(w))
        target.bind('<Shift-Home>', lambda e, w=widget: ClipboardManager.select_to_line_start(w))

        # Shift+End / Cmd+Shift+Right — выделить до конца строки
        if is_macos():
            target.bind('<Command-Shift-Right>', lambda e, w=widget: ClipboardManager.select_to_line_end(w))
        target.bind('<Shift-End>', lambda e, w=widget: ClipboardManager.select_to_line_end(w))

        # Ctrl+Shift+Left / Option+Shift+Left — выделить слово назад
        if is_macos():
            target.bind('<Option-Shift-Left>', lambda e, w=widget: ClipboardManager.select_word_back(w))
        else:
            target.bind('<Control-Shift-Left>', lambda e, w=widget: ClipboardManager.select_word_back(w))

        # Ctrl+Shift+Right / Option+Shift+Right — выделить слово вперёд
        if is_macos():
            target.bind('<Option-Shift-Right>', lambda e, w=widget: ClipboardManager.select_word_forward(w))
        else:
            target.bind('<Control-Shift-Right>', lambda e, w=widget: ClipboardManager.select_word_forward(w))

    @staticmethod
    def bind_shortcuts(widget, root):
        """
        Привязка стандартных горячих клавиш (алиас для bind_all_shortcuts).
        """
        ClipboardManager.bind_all_shortcuts(widget, root)

    @staticmethod
    def _get_inner_widget(widget):
        """Получить внутренний tkinter виджет из CTk виджета"""
        if hasattr(widget, '_entry'):
            return widget._entry
        if hasattr(widget, '_textbox'):
            return widget._textbox
        return None

    @staticmethod
    def _get_entry(widget):
        """Получить Entry виджет"""
        if hasattr(widget, '_entry'):
            return widget._entry
        return widget

    @staticmethod
    def _is_textbox(widget) -> bool:
        """Проверить, является ли виджет текстовым полем (многострочным)"""
        return hasattr(widget, '_textbox') or (hasattr(widget, 'index') and hasattr(widget, 'tag_add'))

    # =========================================================================
    # БУФЕР ОБМЕНА
    # =========================================================================

    @staticmethod
    def paste(widget, root) -> str:
        """Вставка текста из буфера обмена"""
        try:
            clipboard_text = root.clipboard_get()

            if hasattr(widget, '_entry'):
                entry = widget._entry
                try:
                    entry.delete("sel.first", "sel.last")
                except:
                    pass
                entry.insert("insert", clipboard_text)
            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                try:
                    textbox.delete("sel.first", "sel.last")
                except:
                    pass
                textbox.insert("insert", clipboard_text)
            else:
                try:
                    widget.delete("sel.first", "sel.last")
                except:
                    pass
                widget.insert("insert", clipboard_text)

        except Exception as e:
            pass
        return "break"

    @staticmethod
    def copy(widget, root) -> str:
        """Копирование выделенного текста"""
        try:
            selected_text = None

            if hasattr(widget, '_entry'):
                entry = widget._entry
                if entry.selection_present():
                    selected_text = entry.selection_get()
            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                try:
                    selected_text = textbox.get("sel.first", "sel.last")
                except:
                    pass
            else:
                if hasattr(widget, 'selection_present') and widget.selection_present():
                    selected_text = widget.selection_get()

            if selected_text:
                root.clipboard_clear()
                root.clipboard_append(selected_text)

        except Exception:
            pass
        return "break"

    @staticmethod
    def cut(widget, root) -> str:
        """Вырезание выделенного текста"""
        try:
            selected_text = None

            if hasattr(widget, '_entry'):
                entry = widget._entry
                if entry.selection_present():
                    selected_text = entry.selection_get()
                    entry.delete("sel.first", "sel.last")
            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                try:
                    selected_text = textbox.get("sel.first", "sel.last")
                    textbox.delete("sel.first", "sel.last")
                except:
                    pass
            else:
                if hasattr(widget, 'selection_present') and widget.selection_present():
                    selected_text = widget.selection_get()
                    widget.delete("sel.first", "sel.last")

            if selected_text:
                root.clipboard_clear()
                root.clipboard_append(selected_text)

        except Exception:
            pass
        return "break"

    @staticmethod
    def select_all(widget) -> str:
        """Выделение всего текста"""
        try:
            if hasattr(widget, '_entry'):
                entry = widget._entry
                entry.select_range(0, "end")
                entry.icursor("end")
            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                textbox.tag_add("sel", "1.0", "end-1c")
            else:
                if hasattr(widget, 'select_range'):
                    widget.select_range(0, "end")
                    widget.icursor("end")
                elif hasattr(widget, 'tag_add'):
                    widget.tag_add("sel", "1.0", "end-1c")
        except Exception:
            pass
        return "break"

    # =========================================================================
    # ОТМЕНА / ПОВТОР
    # =========================================================================

    @staticmethod
    def undo(widget) -> str:
        """Отмена последнего действия"""
        try:
            inner = ClipboardManager._get_inner_widget(widget)
            target = inner if inner else widget
            target.event_generate("<<Undo>>")
        except Exception:
            pass
        return "break"

    @staticmethod
    def redo(widget) -> str:
        """Повтор отменённого действия"""
        try:
            inner = ClipboardManager._get_inner_widget(widget)
            target = inner if inner else widget
            target.event_generate("<<Redo>>")
        except Exception:
            pass
        return "break"

    # =========================================================================
    # УДАЛЕНИЕ
    # =========================================================================

    @staticmethod
    def delete_word_back(widget) -> str:
        """Удалить слово назад (Ctrl+Backspace)"""
        try:
            if hasattr(widget, '_entry'):
                entry = widget._entry
                pos = entry.index("insert")
                text = entry.get()

                # Находим начало предыдущего слова
                i = pos - 1
                while i > 0 and text[i] == ' ':
                    i -= 1
                while i > 0 and text[i - 1] != ' ':
                    i -= 1

                entry.delete(i, pos)

            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                textbox.delete("insert-1c wordstart", "insert")
        except Exception:
            pass
        return "break"

    @staticmethod
    def delete_word_forward(widget) -> str:
        """Удалить слово вперёд (Ctrl+Delete)"""
        try:
            if hasattr(widget, '_entry'):
                entry = widget._entry
                pos = entry.index("insert")
                text = entry.get()

                # Находим конец следующего слова
                i = pos
                while i < len(text) and text[i] == ' ':
                    i += 1
                while i < len(text) and text[i] != ' ':
                    i += 1

                entry.delete(pos, i)

            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                textbox.delete("insert", "insert wordend")
        except Exception:
            pass
        return "break"

    # =========================================================================
    # НАВИГАЦИЯ
    # =========================================================================

    @staticmethod
    def go_line_start(widget) -> str:
        """Перейти в начало строки (Home)"""
        try:
            if hasattr(widget, '_entry'):
                widget._entry.icursor(0)
            elif hasattr(widget, '_textbox'):
                widget._textbox.mark_set("insert", "insert linestart")
            else:
                widget.icursor(0)
        except Exception:
            pass
        return "break"

    @staticmethod
    def go_line_end(widget) -> str:
        """Перейти в конец строки (End)"""
        try:
            if hasattr(widget, '_entry'):
                widget._entry.icursor("end")
            elif hasattr(widget, '_textbox'):
                widget._textbox.mark_set("insert", "insert lineend")
            else:
                widget.icursor("end")
        except Exception:
            pass
        return "break"

    @staticmethod
    def go_text_start(widget) -> str:
        """Перейти в начало текста (Ctrl+Home)"""
        try:
            if hasattr(widget, '_entry'):
                widget._entry.icursor(0)
            elif hasattr(widget, '_textbox'):
                widget._textbox.mark_set("insert", "1.0")
                widget._textbox.see("1.0")
            else:
                widget.icursor(0)
        except Exception:
            pass
        return "break"

    @staticmethod
    def go_text_end(widget) -> str:
        """Перейти в конец текста (Ctrl+End)"""
        try:
            if hasattr(widget, '_entry'):
                widget._entry.icursor("end")
            elif hasattr(widget, '_textbox'):
                widget._textbox.mark_set("insert", "end-1c")
                widget._textbox.see("end")
            else:
                widget.icursor("end")
        except Exception:
            pass
        return "break"

    @staticmethod
    def word_back(widget) -> str:
        """Перейти на слово назад (Ctrl+Left)"""
        try:
            if hasattr(widget, '_entry'):
                entry = widget._entry
                pos = entry.index("insert")
                text = entry.get()

                i = pos - 1
                while i > 0 and text[i] == ' ':
                    i -= 1
                while i > 0 and text[i - 1] != ' ':
                    i -= 1

                entry.icursor(i)

            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                textbox.mark_set("insert", "insert-1c wordstart")
        except Exception:
            pass
        return "break"

    @staticmethod
    def word_forward(widget) -> str:
        """Перейти на слово вперёд (Ctrl+Right)"""
        try:
            if hasattr(widget, '_entry'):
                entry = widget._entry
                pos = entry.index("insert")
                text = entry.get()

                i = pos
                while i < len(text) and text[i] != ' ':
                    i += 1
                while i < len(text) and text[i] == ' ':
                    i += 1

                entry.icursor(i)

            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                textbox.mark_set("insert", "insert wordend")
        except Exception:
            pass
        return "break"

    # =========================================================================
    # ВЫДЕЛЕНИЕ С НАВИГАЦИЕЙ
    # =========================================================================

    @staticmethod
    def select_to_line_start(widget) -> str:
        """Выделить до начала строки (Shift+Home)"""
        try:
            if hasattr(widget, '_entry'):
                entry = widget._entry
                pos = entry.index("insert")
                entry.select_range(0, pos)
            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                textbox.tag_add("sel", "insert linestart", "insert")
        except Exception:
            pass
        return "break"

    @staticmethod
    def select_to_line_end(widget) -> str:
        """Выделить до конца строки (Shift+End)"""
        try:
            if hasattr(widget, '_entry'):
                entry = widget._entry
                pos = entry.index("insert")
                entry.select_range(pos, "end")
            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                textbox.tag_add("sel", "insert", "insert lineend")
        except Exception:
            pass
        return "break"

    @staticmethod
    def select_word_back(widget) -> str:
        """Выделить слово назад (Ctrl+Shift+Left)"""
        try:
            if hasattr(widget, '_entry'):
                entry = widget._entry
                pos = entry.index("insert")
                text = entry.get()

                i = pos - 1
                while i > 0 and text[i] == ' ':
                    i -= 1
                while i > 0 and text[i - 1] != ' ':
                    i -= 1

                entry.select_range(i, pos)
                entry.icursor(i)

            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                textbox.tag_add("sel", "insert-1c wordstart", "insert")
                textbox.mark_set("insert", "insert-1c wordstart")
        except Exception:
            pass
        return "break"

    @staticmethod
    def select_word_forward(widget) -> str:
        """Выделить слово вперёд (Ctrl+Shift+Right)"""
        try:
            if hasattr(widget, '_entry'):
                entry = widget._entry
                pos = entry.index("insert")
                text = entry.get()

                i = pos
                while i < len(text) and text[i] != ' ':
                    i += 1
                while i < len(text) and text[i] == ' ':
                    i += 1

                entry.select_range(pos, i)
                entry.icursor(i)

            elif hasattr(widget, '_textbox'):
                textbox = widget._textbox
                textbox.tag_add("sel", "insert", "insert wordend")
                textbox.mark_set("insert", "insert wordend")
        except Exception:
            pass
        return "break"


# ============================================================================
# Настройка для разных ОС
# ============================================================================

def setup_platform_specifics(root):
    """Применение платформо-специфичных настроек"""
    if is_windows():
        _setup_windows(root)
    elif is_macos():
        _setup_macos(root)
    elif is_linux():
        _setup_linux(root)


def _setup_windows(root):
    """Настройки для Windows"""
    import ctypes

    # Поддержка High DPI
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # Правильная иконка в taskbar
    try:
        myappid = 'ysell.analyzer.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass


def _setup_macos(root):
    """Настройки для macOS"""
    # Масштабирование для Retina
    try:
        root.tk.call('tk', 'scaling', 2.0)
    except Exception:
        pass

    # Стандартные команды macOS
    try:
        root.bind('<Command-q>', lambda e: root.quit())
        root.bind('<Command-w>', lambda e: root.withdraw())
    except Exception:
        pass


def _setup_linux(root):
    """Настройки для Linux"""
    # Принудительно использовать X11 для Wayland
    if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        os.environ['GDK_BACKEND'] = 'x11'


# ============================================================================
# Логирование
# ============================================================================

def setup_logging(log_dir: Path, name: str = "ysell_analyzer") -> logging.Logger:
    """
    Настройка логирования с выводом в файл и консоль.

    Args:
        log_dir: Директория для логов
        name: Имя логгера

    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый обработчик
    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# ============================================================================
# Проверка зависимостей
# ============================================================================

def check_dependencies() -> tuple[bool, List[str]]:
    """
    Проверка установленных зависимостей.

    Returns:
        (все_установлены, список_отсутствующих)
    """
    required = {
        'telethon': 'telethon>=1.34.0',
        'pandas': 'pandas>=2.0.0',
        'customtkinter': 'customtkinter>=5.2.0',
        'anthropic': 'anthropic>=0.40.0',
        'docx': 'python-docx>=1.1.0',
        'PIL': 'Pillow>=10.0.0',
        'dotenv': 'python-dotenv>=1.0.0',
    }

    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    return len(missing) == 0, missing


def check_python_version(min_version: tuple = (3, 9)) -> bool:
    """Проверка минимальной версии Python"""
    return sys.version_info >= min_version


# ============================================================================
# Валидация данных
# ============================================================================

def validate_date(date_str: str, format_str: str = '%d-%m-%Y') -> tuple[bool, Optional[datetime]]:
    """
    Валидация строки даты.

    Args:
        date_str: Строка с датой
        format_str: Формат даты

    Returns:
        (валидна, объект_datetime или None)
    """
    if not date_str or not date_str.strip():
        return True, None  # Пустая дата допустима

    try:
        parsed = datetime.strptime(date_str.strip(), format_str)
        return True, parsed
    except ValueError:
        return False, None


def validate_phone(phone: str) -> tuple[bool, str]:
    """
    Валидация номера телефона.

    Args:
        phone: Номер телефона

    Returns:
        (валиден, сообщение_об_ошибке)
    """
    phone = phone.strip()

    if not phone:
        return False, "Номер телефона не может быть пустым"

    if not phone.startswith('+'):
        return False, "Номер должен начинаться с +"

    # Убираем + для проверки цифр
    digits = phone[1:].replace(' ', '').replace('-', '')
    if not digits.isdigit():
        return False, "Номер должен содержать только цифры"

    if len(digits) < 10 or len(digits) > 15:
        return False, "Неверная длина номера телефона"

    return True, ""


def validate_api_hash(api_hash: str) -> tuple[bool, str]:
    """Валидация API Hash"""
    api_hash = api_hash.strip()

    if not api_hash:
        return False, "API Hash не может быть пустым"

    if len(api_hash) != 32:
        return False, "API Hash должен содержать 32 символа"

    return True, ""


# ============================================================================
# Файловые операции
# ============================================================================

def safe_remove_file(path: Path) -> bool:
    """
    Безопасное удаление файла с проверками.

    Args:
        path: Путь к файлу

    Returns:
        True если файл удален успешно
    """
    try:
        if path.exists() and path.is_file():
            path.unlink()
            return True
        return False
    except Exception:
        return False


def get_csv_files(folder: Path) -> List[Path]:
    """Получение списка CSV файлов в папке"""
    if not folder.exists():
        return []
    return list(folder.glob("*.csv"))


def clean_filename(name: str) -> str:
    """Очистка имени файла от недопустимых символов"""
    import re
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")


# ============================================================================
# Форматирование
# ============================================================================

def format_file_size(size_bytes: int) -> str:
    """Форматирование размера файла"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """Форматирование длительности"""
    if seconds < 60:
        return f"{int(seconds)} сек"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes} мин {secs} сек"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours} ч {minutes} мин"