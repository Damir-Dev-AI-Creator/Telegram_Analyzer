# telegram_auth_dialog.py
"""Диалоговое окно для авторизации в Telegram"""

import customtkinter as ctk
from tkinter import messagebox
import threading
import asyncio
import qrcode
from PIL import Image, ImageTk
from io import BytesIO


class AuthMethodDialog(ctk.CTkToplevel):
    """Диалог выбора метода авторизации"""

    def __init__(self, parent):
        super().__init__(parent)

        self.selected_method = None
        self.waiting_for_choice = threading.Event()

        # Настройка окна
        self.title("Выбор метода авторизации")
        self.geometry("550x400")
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
        width = 550
        height = 400
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        """Создание виджетов"""

        # Заголовок
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(pady=20, padx=20, fill="x")

        ctk.CTkLabel(
            header_frame,
            text="🔐 Авторизация в Telegram",
            font=("Arial", 22, "bold")
        ).pack()

        ctk.CTkLabel(
            header_frame,
            text="Выберите удобный для вас способ",
            font=("Arial", 13),
            text_color="gray"
        ).pack(pady=(5, 0))

        # QR-код метод
        qr_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#2b2b2b")
        qr_frame.pack(pady=15, padx=30, fill="x")

        qr_content = ctk.CTkFrame(qr_frame, fg_color="transparent")
        qr_content.pack(pady=15, padx=15, fill="x")

        ctk.CTkLabel(
            qr_content,
            text="📱 QR-код",
            font=("Arial", 16, "bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            qr_content,
            text="• Быстрая авторизация через сканирование\n"
                 "• Удобно если у вас есть другое устройство\n"
                 "• Нужна камера на телефоне",
            font=("Arial", 11),
            justify="left",
            text_color="lightgray"
        ).pack(anchor="w", pady=(5, 10))

        ctk.CTkButton(
            qr_content,
            text="✅ Использовать QR-код",
            command=lambda: self.select_method("qr"),
            fg_color="#2b8a2b",
            hover_color="#1f6b1f",
            height=40,
            font=("Arial", 13, "bold")
        ).pack(fill="x")

        # Код метод
        code_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#2b2b2b")
        code_frame.pack(pady=15, padx=30, fill="x")

        code_content = ctk.CTkFrame(code_frame, fg_color="transparent")
        code_content.pack(pady=15, padx=15, fill="x")

        ctk.CTkLabel(
            code_content,
            text="🔢 Код из Telegram",
            font=("Arial", 16, "bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            code_content,
            text="• Код придет в Telegram или SMS\n"
                 "• Классический способ авторизации\n"
                 "• Нужен доступ к номеру телефона",
            font=("Arial", 11),
            justify="left",
            text_color="lightgray"
        ).pack(anchor="w", pady=(5, 10))

        ctk.CTkButton(
            code_content,
            text="📞 Использовать код",
            command=lambda: self.select_method("code"),
            fg_color="#0088cc",
            hover_color="#006699",
            height=40,
            font=("Arial", 13, "bold")
        ).pack(fill="x")

        # Кнопка отмены
        ctk.CTkButton(
            self,
            text="❌ Отмена",
            command=self.on_cancel,
            fg_color="#dc3545",
            hover_color="#a02734",
            height=40,
            font=("Arial", 12, "bold")
        ).pack(pady=15, padx=30, fill="x")

    def select_method(self, method):
        """Выбор метода авторизации"""
        self.selected_method = method
        self.waiting_for_choice.set()
        self.destroy()

    def on_cancel(self):
        """Отмена выбора"""
        result = messagebox.askyesno(
            "Отмена авторизации",
            "Вы уверены, что хотите отменить авторизацию?\n\n"
            "Без авторизации экспорт из Telegram невозможен.",
            icon='warning'
        )

        if result:
            self.selected_method = None
            self.waiting_for_choice.set()
            self.destroy()

    def wait_for_choice(self):
        """Ожидание выбора пользователя"""
        self.waiting_for_choice.wait()
        return self.selected_method


class TelegramQRAuthDialog(ctk.CTkToplevel):
    """Диалог для авторизации через QR-код"""

    def __init__(self, parent, qr_url):
        super().__init__(parent)

        self.qr_url = qr_url
        self.cancelled = False
        self.qr_image_label = None

        # Настройка окна
        self.title("Авторизация через QR-код")
        self.geometry("500x650")
        self.resizable(False, False)

        # Модальное окно
        self.transient(parent)
        self.grab_set()

        # Центрирование
        self.center_window()

        # Создание интерфейса
        self.create_widgets()

        # Генерация и отображение QR-кода
        self.display_qr_code()

        # Запрет закрытия через X
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def center_window(self):
        """Центрирование окна"""
        self.update_idletasks()
        width = 500
        height = 650
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        """Создание виджетов"""

        # Заголовок
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(pady=20, padx=20, fill="x")

        ctk.CTkLabel(
            header_frame,
            text="📱 QR-код для авторизации",
            font=("Arial", 20, "bold")
        ).pack()

        # Инструкция
        info_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#2b2b2b")
        info_frame.pack(pady=10, padx=20, fill="x")

        info_text = """
Отсканируйте QR-код в Telegram:

1️⃣ Откройте Telegram на телефоне
2️⃣ Перейдите в Настройки → Устройства
3️⃣ Нажмите "Привязать устройство"
4️⃣ Отсканируйте QR-код ниже

⏳ QR-код действителен 5 минут
        """

        ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=("Arial", 12),
            justify="left"
        ).pack(pady=15, padx=15)

        # Контейнер для QR-кода
        qr_container = ctk.CTkFrame(self, corner_radius=10, fg_color="white")
        qr_container.pack(pady=15, padx=50)

        self.qr_image_label = ctk.CTkLabel(
            qr_container,
            text="",
            fg_color="white"
        )
        self.qr_image_label.pack(padx=10, pady=10)

        # Статус
        self.status_label = ctk.CTkLabel(
            self,
            text="⏳ Ожидание сканирования...",
            font=("Arial", 12, "bold"),
            text_color="#ffa500"
        )
        self.status_label.pack(pady=10)

        # Кнопка отмены
        ctk.CTkButton(
            self,
            text="❌ Отмена",
            command=self.on_cancel,
            fg_color="#dc3545",
            hover_color="#a02734",
            height=45,
            font=("Arial", 14, "bold")
        ).pack(pady=20, padx=20, fill="x")

    def display_qr_code(self):
        """Генерация и отображение QR-кода"""
        try:
            # Создать QR-код
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.qr_url)
            qr.make(fit=True)

            # Создать изображение
            qr_image = qr.make_image(fill_color="black", back_color="white")

            # Конвертировать в формат для Tkinter
            qr_image = qr_image.resize((300, 300))
            qr_photo = ImageTk.PhotoImage(qr_image)

            # Отобразить
            self.qr_image_label.configure(image=qr_photo)
            self.qr_image_label.image = qr_photo  # Сохранить ссылку

        except Exception as e:
            self.status_label.configure(
                text=f"❌ Ошибка создания QR-кода: {str(e)}",
                text_color="red"
            )

    def update_status(self, message, color="orange"):
        """Обновить статус"""
        try:
            if self.winfo_exists():
                self.after(0, lambda: self.status_label.configure(text=message, text_color=color))
        except:
            pass

    def on_cancel(self):
        """Отмена авторизации"""
        result = messagebox.askyesno(
            "Отмена авторизации",
            "Вы уверены, что хотите отменить авторизацию?\n\n"
            "Без авторизации экспорт из Telegram невозможен.",
            icon='warning'
        )

        if result:
            self.cancelled = True
            self.destroy()

    def close_dialog(self):
        """Закрыть диалог после успешной авторизации"""
        try:
            if self.winfo_exists():
                self.after(0, self.destroy)
        except:
            pass


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
        try:
            if self.winfo_exists():
                self.after(0, self._show_password_prompt_ui)
        except:
            pass

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
        try:
            if self.winfo_exists():
                self.after(0, lambda: self._show_error_ui(message))
        except:
            pass

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
        try:
            if self.winfo_exists():
                self.after(0, self.destroy)
        except:
            pass

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
        self.qr_dialog = None
        self.auth_method = None

    async def choose_auth_method(self):
        """Выбор метода авторизации (QR или код)"""
        loop = asyncio.get_event_loop()
        method_dialog = None

        def create_method_dialog():
            nonlocal method_dialog
            method_dialog = AuthMethodDialog(self.parent_window)

        # Создаем диалог выбора
        self.parent_window.after(0, create_method_dialog)

        # Ждем, пока диалог будет создан
        while method_dialog is None:
            await asyncio.sleep(0.1)

        # Ждем выбора метода
        self.auth_method = await loop.run_in_executor(
            None,
            method_dialog.wait_for_choice
        )

        if self.auth_method is None:
            raise Exception("Авторизация отменена пользователем")

        return self.auth_method

    async def start_qr_auth(self, client):
        """Запуск QR-авторизации"""
        try:
            # Запустить QR-авторизацию в Telethon
            qr_login = await client.qr_login()
            qr_url = qr_login.url

            # Создать диалог с QR-кодом
            loop = asyncio.get_event_loop()

            def create_qr_dialog():
                self.qr_dialog = TelegramQRAuthDialog(self.parent_window, qr_url)

            self.parent_window.after(0, create_qr_dialog)

            # Ждем, пока диалог будет создан
            while self.qr_dialog is None:
                await asyncio.sleep(0.1)

            # Обновляем статус
            self.qr_dialog.update_status("⏳ Ожидание сканирования...", "orange")

            # Ждем авторизации с таймаутом
            try:
                await asyncio.wait_for(qr_login.wait(), timeout=300)  # 5 минут

                # Успешно авторизовались
                if self.qr_dialog:
                    self.qr_dialog.update_status("✅ Успешно авторизован!", "green")
                    await asyncio.sleep(1)
                    self.qr_dialog.close_dialog()

            except asyncio.TimeoutError:
                if self.qr_dialog:
                    self.qr_dialog.update_status("⏱️ QR-код истек. Попробуйте снова.", "red")
                raise Exception("QR-код истек. Время ожидания 5 минут истекло.")

            # Проверить отмену пользователем
            if self.qr_dialog:
                try:
                    if self.qr_dialog.winfo_exists() and self.qr_dialog.cancelled:
                        raise Exception("Авторизация отменена пользователем")
                except:
                    pass

        except Exception as e:
            if self.qr_dialog:
                self.qr_dialog.update_status(f"❌ Ошибка: {str(e)}", "red")
                await asyncio.sleep(2)
                self.qr_dialog.close_dialog()
            raise

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