# telegram_auth_dialog.py
"""Диалоговое окно для авторизации в Telegram"""

import customtkinter as ctk
from tkinter import messagebox
import threading
import asyncio


class TelegramAuthDialog(ctk.CTkToplevel):
    """Диалог для ввода кода авторизации Telegram"""

    def __init__(self, parent, phone_number):
        super().__init__(parent)

        self.phone_number = phone_number
        self.code = None
        self.password = None
        self.waiting_for_input = threading.Event()

        # Настройка окна
        self.title("Авторизация Telegram")
        self.geometry("500x350")
        self.resizable(False, False)

        # Модальное окно
        self.transient(parent)
        self.grab_set()

        # Центрирование
        self.center_window()

        # Создание интерфейса
        self.create_widgets()

        # Запрет закрытия через X
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def center_window(self):
        """Центрирование окна"""
        self.update_idletasks()
        width = 500
        height = 350
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        """Создание виджетов"""

        # Иконка и заголовок
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(pady=20, padx=20, fill="x")

        ctk.CTkLabel(
            header_frame,
            text="🔐 Авторизация в Telegram",
            font=("Arial", 20, "bold")
        ).pack()

        # Информация
        info_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#2b2b2b")
        info_frame.pack(pady=10, padx=20, fill="x")

        info_text = f"""
📱 На номер {self.phone_number} был отправлен код подтверждения.

Проверьте:
• Telegram на телефоне
• Telegram на других устройствах
• SMS сообщения

Введите код ниже:
        """

        ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=("Arial", 12),
            justify="left"
        ).pack(pady=15, padx=15)

        # Поле ввода кода
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            input_frame,
            text="Код подтверждения:",
            font=("Arial", 13, "bold")
        ).pack(anchor="w", pady=(0, 5))

        self.code_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Введите код (например: 12345)",
            height=40,
            font=("Arial", 14),
            justify="center"
        )
        self.code_entry.pack(fill="x")
        self.code_entry.focus()

        # Привязка Enter к отправке
        self.code_entry.bind("<Return>", lambda e: self.submit_code())

        # Добавляем поддержку стандартных сочетаний клавиш
        self.bind_paste_shortcuts(self.code_entry)

        # Поле для пароля (скрыто по умолчанию)
        self.password_frame = ctk.CTkFrame(self, fg_color="transparent")

        ctk.CTkLabel(
            self.password_frame,
            text="Пароль двухфакторной аутентификации:",
            font=("Arial", 13, "bold")
        ).pack(anchor="w", pady=(10, 5))

        self.password_entry = ctk.CTkEntry(
            self.password_frame,
            placeholder_text="Введите пароль 2FA",
            height=40,
            font=("Arial", 14),
            show="●"
        )
        self.password_entry.pack(fill="x")
        self.password_entry.bind("<Return>", lambda e: self.submit_password())

        # Добавляем поддержку стандартных сочетаний клавиш
        self.bind_paste_shortcuts(self.password_entry)

        # Кнопки
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=20, padx=20, fill="x")

        self.submit_btn = ctk.CTkButton(
            button_frame,
            text="✅ Подтвердить",
            command=self.submit_code,
            fg_color="#2b8a2b",
            hover_color="#1f6b1f",
            height=45,
            font=("Arial", 14, "bold")
        )
        self.submit_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        ctk.CTkButton(
            button_frame,
            text="❌ Отмена",
            command=self.on_cancel,
            fg_color="#dc3545",
            hover_color="#a02734",
            height=45,
            font=("Arial", 14, "bold")
        ).pack(side="right", expand=True, fill="x", padx=(5, 0))

        # Ссылка на помощь
        help_label = ctk.CTkLabel(
            self,
            text="❓ Не получили код? Запросите повторно в Telegram",
            font=("Arial", 10),
            text_color="gray"
        )
        help_label.pack(pady=(0, 10))

    def submit_code(self):
        """Отправка кода"""
        code = self.code_entry.get().strip()

        if not code:
            messagebox.showwarning(
                "Предупреждение",
                "Пожалуйста, введите код подтверждения"
            )
            return

        # Проверка формата кода (обычно 5 цифр)
        if not code.isdigit():
            messagebox.showwarning(
                "Предупреждение",
                "Код должен содержать только цифры"
            )
            return

        self.code = code
        self.submit_btn.configure(state="disabled", text="⏳ Проверка...")

        # Сигнализируем, что код введен
        self.waiting_for_input.set()

    def show_password_prompt(self):
        """Показать запрос пароля 2FA"""
        self.after(0, self._show_password_prompt_ui)

    def _show_password_prompt_ui(self):
        """Обновление UI для запроса пароля"""
        # Скрываем поле кода
        self.code_entry.configure(state="disabled")
        self.submit_btn.pack_forget()

        # Показываем поле пароля
        self.password_frame.pack(pady=10, padx=20, fill="x")

        # Обновляем кнопку
        self.submit_btn.configure(
            state="normal",
            text="🔓 Войти",
            command=self.submit_password
        )
        self.submit_btn.pack(side="left", expand=True, fill="x", padx=(0, 5), in_=self.password_frame.master)

        self.password_entry.focus()

    def submit_password(self):
        """Отправка пароля 2FA"""
        password = self.password_entry.get().strip()

        if not password:
            messagebox.showwarning(
                "Предупреждение",
                "Пожалуйста, введите пароль двухфакторной аутентификации"
            )
            return

        self.password = password
        self.submit_btn.configure(state="disabled", text="⏳ Вход...")

        # Сигнализируем, что пароль введен
        self.waiting_for_input.set()

    def on_cancel(self):
        """Отмена авторизации"""
        result = messagebox.askyesno(
            "Отмена авторизации",
            "Вы уверены, что хотите отменить авторизацию?\n\n"
            "Без авторизации экспорт из Telegram невозможен.",
            icon='warning'
        )

        if result:
            self.code = None
            self.password = None
            self.waiting_for_input.set()
            self.destroy()

    def wait_for_input(self):
        """Ожидание ввода пользователя"""
        self.waiting_for_input.clear()
        self.waiting_for_input.wait()
        return self.code, self.password

    def show_error(self, message):
        """Показать ошибку"""
        self.after(0, lambda: self._show_error_ui(message))

    def _show_error_ui(self, message):
        """Обновление UI для показа ошибки"""
        self.submit_btn.configure(state="normal", text="✅ Подтвердить")
        messagebox.showerror("Ошибка авторизации", message)

        # Очищаем поле и фокусируемся на нем
        if self.password_frame.winfo_ismapped():
            self.password_entry.delete(0, "end")
            self.password_entry.focus()
        else:
            self.code_entry.delete(0, "end")
            self.code_entry.focus()

    def close_dialog(self):
        """Закрыть диалог после успешной авторизации"""
        self.after(0, self.destroy)

    def bind_paste_shortcuts(self, entry):
        """Привязка стандартных сочетаний клавиш к полю ввода"""
        # Ctrl+V - вставка
        entry.bind('<Control-v>', lambda e: self.paste_from_clipboard(entry))
        entry.bind('<Control-V>', lambda e: self.paste_from_clipboard(entry))

        # Ctrl+C - копирование
        entry.bind('<Control-c>', lambda e: self.copy_to_clipboard(entry))
        entry.bind('<Control-C>', lambda e: self.copy_to_clipboard(entry))

        # Ctrl+X - вырезание
        entry.bind('<Control-x>', lambda e: self.cut_to_clipboard(entry))
        entry.bind('<Control-X>', lambda e: self.cut_to_clipboard(entry))

        # Ctrl+A - выделить всё
        entry.bind('<Control-a>', lambda e: self.select_all(entry))
        entry.bind('<Control-A>', lambda e: self.select_all(entry))

    def paste_from_clipboard(self, entry):
        """Вставка текста из буфера обмена"""
        try:
            clipboard_text = self.clipboard_get()
            cursor_pos = entry.index("insert")
            entry.insert(cursor_pos, clipboard_text)
            return "break"
        except:
            pass
        return "break"

    def copy_to_clipboard(self, entry):
        """Копирование выделенного текста в буфер обмена"""
        try:
            if entry.selection_present():
                selected_text = entry.selection_get()
                self.clipboard_clear()
                self.clipboard_append(selected_text)
        except:
            pass
        return "break"

    def cut_to_clipboard(self, entry):
        """Вырезание выделенного текста в буфер обмена"""
        try:
            if entry.selection_present():
                selected_text = entry.selection_get()
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                entry.delete("sel.first", "sel.last")
        except:
            pass
        return "break"

    def select_all(self, entry):
        """Выделение всего текста в поле"""
        entry.select_range(0, "end")
        entry.icursor("end")
        return "break"


class TelegramCodeHandler:
    """Обработчик для получения кода от пользователя через GUI"""

    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.dialog = None

    async def get_code(self, phone_number):
        """Получить код подтверждения от пользователя"""
        # Создаем диалог в главном потоке
        loop = asyncio.get_event_loop()

        def create_dialog():
            self.dialog = TelegramAuthDialog(self.parent_window, phone_number)

        # Создаем диалог
        self.parent_window.after(0, create_dialog)

        # Ждем, пока диалог будет создан
        while self.dialog is None:
            await asyncio.sleep(0.1)

        # Ждем ввода кода в отдельном потоке
        code, password = await loop.run_in_executor(
            None,
            self.dialog.wait_for_input
        )

        if code is None:
            raise Exception("Авторизация отменена пользователем")

        return code

    async def get_password(self):
        """Получить пароль двухфакторной аутентификации"""
        if self.dialog is None:
            raise Exception("Диалог авторизации не инициализирован")

        # Показываем запрос пароля
        self.dialog.show_password_prompt()

        # Сбрасываем событие для нового ввода
        self.dialog.waiting_for_input.clear()

        # Ждем ввода пароля
        loop = asyncio.get_event_loop()
        code, password = await loop.run_in_executor(
            None,
            self.dialog.wait_for_input
        )

        if password is None:
            raise Exception("Авторизация отменена пользователем")

        return password

    def show_error(self, message):
        """Показать ошибку"""
        if self.dialog:
            self.dialog.show_error(message)

    def close(self):
        """Закрыть диалог"""
        if self.dialog:
            self.dialog.close_dialog()
            self.dialog = None