# ui/setup.py
"""Окно первоначальной настройки для создания конфигурации"""

import customtkinter as ctk
from tkinter import messagebox
import webbrowser
from typing import Callable, Optional

from core.config import (
    save_config,
    get_app_data_dir,
    get_working_dir,
    get_env_path
)
from core.utils import (
    ClipboardManager,
    setup_platform_specifics,
    validate_phone,
    validate_api_hash,
    is_macos
)


class SetupWindow:
    """Окно для первоначальной настройки приложения"""
    
    def __init__(self, on_complete_callback: Optional[Callable] = None):
        """
        Args:
            on_complete_callback: Функция, вызываемая после успешной настройки
        """
        self.on_complete = on_complete_callback
        
        # Настройка темы
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        # Создание окна
        self.window = ctk.CTk()
        self.window.title("Первоначальная настройка - Ysell Analyzer")
        self.window.geometry("650x750")
        self.window.resizable(True, True)
        self.window.minsize(550, 600)
        
        # Кросс-платформенные настройки
        setup_platform_specifics(self.window)
        
        # Центрирование окна
        self._center_window()
        
        # Обработка закрытия
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Создание интерфейса
        self._create_widgets()
        
        # Запуск главного цикла
        self.window.mainloop()
    
    def _center_window(self):
        """Центрирование окна на экране"""
        self.window.update_idletasks()
        width = 650
        height = 750
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def _create_widgets(self):
        """Создание виджетов окна"""
        # Заголовок
        self._create_header()
        
        # Основная форма со скроллом
        form_frame = ctk.CTkScrollableFrame(self.window, corner_radius=10)
        form_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Секции настроек
        self._create_telegram_section(form_frame)
        self._create_claude_section(form_frame)
        self._create_optional_section(form_frame)
        self._create_info_section(form_frame)
        
        # Кнопки
        self._create_buttons()
    
    def _create_header(self):
        """Создание заголовка"""
        header_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        header_frame.pack(pady=20, padx=20, fill="x")
        
        ctk.CTkLabel(
            header_frame,
            text="🚀 Добро пожаловать в Ysell Analyzer!",
            font=("Arial", 24, "bold")
        ).pack()
        
        ctk.CTkLabel(
            header_frame,
            text="Для начала работы настройте параметры подключения",
            font=("Arial", 12),
            text_color="gray"
        ).pack(pady=5)
    
    def _create_section_header(self, parent, text: str, link: Optional[str] = None):
        """Создание заголовка секции с опциональной ссылкой"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(20, 10), padx=10)
        
        ctk.CTkLabel(
            frame,
            text=text,
            font=("Arial", 16, "bold"),
            anchor="w"
        ).pack(side="left")
        
        if link:
            link_btn = ctk.CTkButton(
                frame,
                text="🔗 Получить",
                width=100,
                height=25,
                font=("Arial", 11),
                fg_color="#1f6aa5",
                command=lambda: webbrowser.open(link)
            )
            link_btn.pack(side="right")
        
        # Разделитель
        ctk.CTkFrame(parent, height=1, fg_color="gray").pack(fill="x", padx=10)
    
    def _create_field(
        self,
        parent,
        label: str,
        placeholder: str,
        hint: str,
        required: bool = True,
        show: str = ""
    ) -> ctk.CTkEntry:
        """Создание поля ввода"""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", pady=8, padx=10)
        
        # Метка
        label_frame = ctk.CTkFrame(container, fg_color="transparent")
        label_frame.pack(fill="x")
        
        ctk.CTkLabel(
            label_frame,
            text=label,
            font=("Arial", 12, "bold"),
            anchor="w"
        ).pack(side="left")
        
        if required:
            ctk.CTkLabel(
                label_frame,
                text=" *",
                font=("Arial", 12, "bold"),
                text_color="#dc3545"
            ).pack(side="left")
        
        # Поле ввода
        entry = ctk.CTkEntry(
            container,
            placeholder_text=placeholder,
            height=38,
            font=("Arial", 11),
            show=show
        )
        entry.pack(fill="x", pady=(5, 0))
        
        # Привязка горячих клавиш (Cmd/Ctrl + V/C/X/A)
        ClipboardManager.bind_shortcuts(entry, self.window)
        
        # Подсказка
        ctk.CTkLabel(
            container,
            text=hint,
            font=("Arial", 9),
            text_color="gray",
            anchor="w"
        ).pack(fill="x", pady=(3, 0))
        
        return entry
    
    def _create_telegram_section(self, parent):
        """Секция Telegram API"""
        self._create_section_header(
            parent,
            "📱 Telegram API",
            "https://my.telegram.org/apps"
        )

        # Выбор режима
        mode_frame = ctk.CTkFrame(parent, fg_color="transparent")
        mode_frame.pack(fill="x", pady=8, padx=10)

        ctk.CTkLabel(
            mode_frame,
            text="Режим работы:",
            font=("Arial", 12, "bold"),
            anchor="w"
        ).pack(anchor="w")

        self.mode_var = ctk.StringVar(value="mtproto")

        # MTProto режим (полный функционал)
        mtproto_radio = ctk.CTkRadioButton(
            mode_frame,
            text="MTProto API (рекомендуется) - Экспорт истории сообщений",
            variable=self.mode_var,
            value="mtproto",
            command=self._toggle_mode_fields,
            font=("Arial", 11)
        )
        mtproto_radio.pack(anchor="w", pady=3)

        # HTTP Bot API режим (облегченный)
        http_radio = ctk.CTkRadioButton(
            mode_frame,
            text="HTTP Bot API (облегченный) - Только новые сообщения",
            variable=self.mode_var,
            value="http",
            command=self._toggle_mode_fields,
            font=("Arial", 11)
        )
        http_radio.pack(anchor="w", pady=3)

        ctk.CTkLabel(
            mode_frame,
            text="💡 MTProto позволяет экспортировать историю, HTTP Bot API - только новые сообщения",
            font=("Arial", 9),
            text_color="gray",
            anchor="w",
            wraplength=580
        ).pack(anchor="w", pady=(3, 0))

        # Поля MTProto (показываются по умолчанию)
        self.mtproto_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.mtproto_frame.pack(fill="x")

        # Важная информация про User Account для экспорта
        info_box = ctk.CTkFrame(self.mtproto_frame, fg_color="#d9534f", corner_radius=8)
        info_box.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            info_box,
            text="⚠️ Для экспорта истории нужен номер телефона!",
            font=("Arial", 11, "bold"),
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            info_box,
            text="Bot Token НЕ МОЖЕТ экспортировать историю (ограничение Telegram API)",
            font=("Arial", 9),
            text_color="#ffffff",
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(0, 5))

        ctk.CTkLabel(
            info_box,
            text="Заполните: API_ID + API_HASH + Номер телефона",
            font=("Arial", 9, "bold"),
            text_color="#ffffff",
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(0, 10))

        self.api_id_entry = self._create_field(
            self.mtproto_frame,
            "API ID:",
            "12345678",
            "Получите на https://my.telegram.org/apps",
            required=False  # Зависит от режима
        )

        self.api_hash_entry = self._create_field(
            self.mtproto_frame,
            "API Hash:",
            "abcdef1234567890abcdef1234567890",
            "Хеш приложения (32 символа)",
            required=False
        )

        self.phone_entry = self._create_field(
            self.mtproto_frame,
            "Номер телефона:",
            "+1234567890",
            "Обязательно для экспорта истории! Формат: +1234567890",
            required=False
        )

        # Поле для Bot Token (только для HTTP Bot API режима)
        self.bot_token_entry = self._create_field(
            parent,
            "Bot Token (только HTTP Bot API):",
            "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            "От @BotFather. Только для мониторинга НОВЫХ сообщений (история недоступна)",
            required=False
        )

    def _toggle_mode_fields(self):
        """Переключение видимости полей в зависимости от режима"""
        mode = self.mode_var.get()

        if mode == "mtproto":
            # Показать поля MTProto
            self.mtproto_frame.pack(fill="x")
        else:
            # Скрыть поля MTProto
            self.mtproto_frame.pack_forget()
    
    def _create_claude_section(self, parent):
        """Секция Claude API (Anthropic)"""
        self._create_section_header(
            parent,
            "🤖 Claude API (Anthropic)",
            "https://console.anthropic.com/settings/keys"
        )
        
        self.claude_entry = self._create_field(
            parent,
            "API Key:",
            "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxx",
            "Ключ API Claude (начинается с sk-ant-)"
        )
    
    def _create_optional_section(self, parent):
        """Секция опциональных настроек"""
        self._create_section_header(parent, "⚙️ Дополнительно (опционально)")
        
        self.exclude_id_entry = self._create_field(
            parent,
            "Исключить User ID:",
            "1234567890",
            "ID пользователя для исключения из экспорта",
            required=False
        )
        
        self.exclude_name_entry = self._create_field(
            parent,
            "Исключить Username:",
            "Username",
            "Имя пользователя для исключения",
            required=False
        )
    
    def _create_info_section(self, parent):
        """Информационная секция"""
        info_frame = ctk.CTkFrame(parent, corner_radius=10)
        info_frame.pack(fill="x", pady=20, padx=10)
        
        ctk.CTkLabel(
            info_frame,
            text="ℹ️ Информация о хранении данных",
            font=("Arial", 12, "bold")
        ).pack(pady=(10, 5))
        
        info_text = f"""
• Конфигурация: {get_env_path()}
• Данные: {get_app_data_dir()}
• Рабочие файлы: {get_working_dir()}
        """
        
        ctk.CTkLabel(
            info_frame,
            text=info_text.strip(),
            font=("Arial", 10),
            justify="left",
            anchor="w"
        ).pack(pady=(0, 10), padx=15)
    
    def _create_buttons(self):
        """Создание кнопок"""
        button_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        button_frame.pack(pady=20, padx=20, fill="x")
        
        ctk.CTkButton(
            button_frame,
            text="💾 Сохранить и продолжить",
            command=self._save_config,
            fg_color="#2b8a2b",
            hover_color="#1f6b1f",
            height=50,
            font=("Arial", 15, "bold")
        ).pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        ctk.CTkButton(
            button_frame,
            text="❌ Отмена",
            command=self._on_closing,
            fg_color="#dc3545",
            hover_color="#a02734",
            height=50,
            font=("Arial", 15, "bold")
        ).pack(side="right", expand=True, fill="x", padx=(10, 0))
    
    def _validate(self) -> bool:
        """Валидация полей"""
        errors = []
        mode = self.mode_var.get()

        # Claude API (всегда обязателен)
        claude_key = self.claude_entry.get().strip()
        if not claude_key:
            errors.append("• Claude API Key не может быть пустым")
        elif not claude_key.startswith("sk-ant-"):
            errors.append("• Claude API Key должен начинаться с 'sk-ant-'")

        if mode == "mtproto":
            # MTProto режим: проверка API_ID, API_HASH
            api_id = self.api_id_entry.get().strip()
            if not api_id:
                errors.append("• API ID не может быть пустым в MTProto режиме")
            elif not api_id.isdigit():
                errors.append("• API ID должен быть числом")

            api_hash = self.api_hash_entry.get().strip()
            valid, msg = validate_api_hash(api_hash)
            if not valid:
                errors.append(f"• API Hash: {msg}")

            # Проверка наличия хотя бы одного: PHONE или BOT_TOKEN
            phone = self.phone_entry.get().strip()
            bot_token = self.bot_token_entry.get().strip()

            if not phone and not bot_token:
                errors.append("• Укажите Bot Token для работы с ботом (номер телефона не нужен)\n  Или укажите номер телефона для User Account режима")

            # Если указан телефон, валидируем его
            if phone:
                valid, msg = validate_phone(phone)
                if not valid:
                    errors.append(f"• Телефон: {msg}")

            # Если указан bot_token, валидируем его
            if bot_token:
                if not ":" in bot_token:
                    errors.append("• Bot Token должен содержать ':' (формат: 123456789:ABC...)")

        else:  # HTTP Bot API режим
            # HTTP режим: требуется только BOT_TOKEN
            bot_token = self.bot_token_entry.get().strip()
            if not bot_token:
                errors.append("• Bot Token обязателен в HTTP Bot API режиме")
            elif not ":" in bot_token:
                errors.append("• Bot Token должен содержать ':' (формат: 123456789:ABC...)")

        if errors:
            messagebox.showerror(
                "Ошибка валидации",
                "Исправьте следующие ошибки:\n\n" + "\n".join(errors)
            )
            return False

        return True
    
    def _save_config(self):
        """Сохранение конфигурации"""
        if not self._validate():
            return

        try:
            mode = self.mode_var.get()
            use_mtproto = (mode == "mtproto")

            save_config(
                claude_api_key=self.claude_entry.get().strip(),
                use_mtproto=use_mtproto,
                api_id=self.api_id_entry.get().strip() if use_mtproto else "",
                api_hash=self.api_hash_entry.get().strip() if use_mtproto else "",
                phone=self.phone_entry.get().strip() if use_mtproto else "",
                bot_token=self.bot_token_entry.get().strip(),
                exclude_user_id=self.exclude_id_entry.get().strip() or "0",
                exclude_username=self.exclude_name_entry.get().strip() or ""
            )

            mode_text = "MTProto API (полный функционал)" if use_mtproto else "HTTP Bot API (только новые сообщения)"

            messagebox.showinfo(
                "Успех!",
                f"✅ Конфигурация успешно сохранена!\n\n"
                f"Режим: {mode_text}\n"
                f"Файл: {get_env_path()}\n\n"
                "Приложение готово к работе."
            )

            self.window.destroy()

            if self.on_complete:
                self.on_complete()

        except Exception as e:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось сохранить конфигурацию:\n\n{str(e)}"
            )
    
    def _on_closing(self):
        """Обработка закрытия окна"""
        result = messagebox.askyesno(
            "Выход",
            "Вы уверены?\n\n"
            "Без настройки приложение не будет работать.",
            icon='warning'
        )
        if result:
            self.window.destroy()


def show_setup_window(on_complete: Optional[Callable] = None):
    """Показать окно настройки"""
    SetupWindow(on_complete)


if __name__ == "__main__":
    show_setup_window(lambda: print("✅ Настройка завершена!"))
