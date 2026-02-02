# ui/app.py
"""Главное окно приложения с поддержкой множественного экспорта"""

import customtkinter as ctk
from tkinter import messagebox, END
import asyncio
import threading
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import os

from core.config import (
    validate_config,
    reload_config,
    get_input_folder,
    get_output_folder,
    get_base_dir,
    get_data_dir,
    is_configured,
    EXPORT_FOLDER
)
from core.utils import (
    ClipboardManager,
    setup_platform_specifics,
    validate_date,
    get_csv_files,
    is_macos
)


class YsellAnalyzerApp:
    """Главное окно приложения"""

    VERSION = "0.3.0"

    def __init__(self):
        # Настройка темы
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Создание окна
        self.root = ctk.CTk()
        self.root.title(f"Ysell Analyzer v{self.VERSION}")
        self.root.geometry("850x750")
        self.root.minsize(750, 650)

        # Список чатов для экспорта
        self.chat_list: List[dict] = []

        # Кросс-платформенные настройки
        setup_platform_specifics(self.root)

        # Проверка конфигурации
        self._check_initial_config()

        # Создание интерфейса
        self._create_ui()

        # Запуск
        self.root.mainloop()

    def _check_initial_config(self):
        """Проверка конфигурации при старте"""
        if not is_configured():
            messagebox.showwarning(
                "Настройка",
                "Приложение не настроено!\n\n"
                "Откройте вкладку '⚙️ Настройки' для конфигурации."
            )

    def _create_ui(self):
        """Создание интерфейса"""
        # Вкладки
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(pady=15, padx=20, fill="both", expand=True)

        # Вкладка экспорта Telegram
        self.tab_export = self.tabview.add("📱 Telegram")
        self._create_export_tab()

        # Вкладка анализа
        self.tab_analyze = self.tabview.add("📊 Анализ")
        self._create_analyze_tab()

        # Вкладка настроек
        self.tab_settings = self.tabview.add("⚙️ Настройки")
        self._create_settings_tab()

        # Статус-бар
        self._create_status_bar()

    # =========================================================================
    # ВКЛАДКА ЭКСПОРТА (с множественными чатами)
    # =========================================================================

    def _create_export_tab(self):
        """Вкладка экспорта из Telegram с поддержкой нескольких чатов"""
        # Основной контейнер
        main_frame = ctk.CTkFrame(self.tab_export, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Заголовок
        ctk.CTkLabel(
            main_frame,
            text="Экспорт сообщений из Telegram",
            font=("Arial", 18, "bold")
        ).pack(pady=(0, 15))

        # === Блок добавления чата ===
        add_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        add_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            add_frame,
            text="➕ Добавить чат для экспорта",
            font=("Arial", 13, "bold")
        ).pack(pady=(15, 10))

        # Chat ID
        chat_input_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        chat_input_frame.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(chat_input_frame, text="Ссылка на чат", width=140).pack(side="left")
        self.chat_entry = ctk.CTkEntry(
            chat_input_frame,
            placeholder_text="https://t.me/...",
            height=35
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=10)
        ClipboardManager.bind_shortcuts(self.chat_entry, self.root)

        # Даты в одну строку
        dates_input_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        dates_input_frame.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(dates_input_frame, text="Период:", width=140).pack(side="left")

        self.start_date_entry = ctk.CTkEntry(
            dates_input_frame,
            placeholder_text="01-12-2025",
            width=120,
            height=35
        )
        self.start_date_entry.pack(side="left", padx=(10, 5))
        ClipboardManager.bind_shortcuts(self.start_date_entry, self.root)

        ctk.CTkLabel(dates_input_frame, text="—").pack(side="left", padx=5)

        self.end_date_entry = ctk.CTkEntry(
            dates_input_frame,
            placeholder_text="31-12-2025",
            width=120,
            height=35
        )
        self.end_date_entry.pack(side="left", padx=(5, 10))
        ClipboardManager.bind_shortcuts(self.end_date_entry, self.root)

        ctk.CTkLabel(
            dates_input_frame,
            text="(ДД-ММ-ГГГГ, пусто = всё)",
            text_color="gray",
            font=("Arial", 10)
        ).pack(side="left", padx=10)

        # Лимит
        limit_input_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        limit_input_frame.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(limit_input_frame, text="Лимит сообщений:", width=140).pack(side="left")
        self.limit_entry = ctk.CTkEntry(
            limit_input_frame,
            placeholder_text="10000",
            width=120,
            height=35
        )
        self.limit_entry.insert(0, "10000")
        self.limit_entry.pack(side="left", padx=10)
        ClipboardManager.bind_shortcuts(self.limit_entry, self.root)

        # Кнопка добавления
        ctk.CTkButton(
            add_frame,
            text="➕ Добавить в очередь",
            command=self._add_chat_to_queue,
            fg_color="#28a745",
            hover_color="#218838",
            height=40,
            font=("Arial", 13, "bold")
        ).pack(pady=15, padx=15, fill="x")

        # === Очередь чатов ===
        queue_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        queue_frame.pack(fill="both", expand=True, pady=(0, 15))

        queue_header = ctk.CTkFrame(queue_frame, fg_color="transparent")
        queue_header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            queue_header,
            text="📋 Очередь экспорта",
            font=("Arial", 13, "bold")
        ).pack(side="left")

        self.queue_count_label = ctk.CTkLabel(
            queue_header,
            text="(0 чатов)",
            font=("Arial", 11),
            text_color="gray"
        )
        self.queue_count_label.pack(side="left", padx=10)

        # Кнопка очистки очереди
        ctk.CTkButton(
            queue_header,
            text="🗑️ Очистить",
            command=self._clear_queue,
            fg_color="#dc3545",
            hover_color="#c82333",
            width=100,
            height=30,
            font=("Arial", 11)
        ).pack(side="right")

        # Список чатов (Textbox для отображения)
        self.queue_textbox = ctk.CTkTextbox(
            queue_frame,
            height=150,
            font=("Consolas", 11),
            state="disabled"
        )
        self.queue_textbox.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        # === Кнопки действий ===
        actions_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        actions_frame.pack(fill="x")

        self.export_btn = ctk.CTkButton(
            actions_frame,
            text="🚀 Экспортировать все",
            command=self._start_batch_export,
            fg_color="#1f6aa5",
            hover_color="#1a5a8a",
            height=50,
            font=("Arial", 15, "bold")
        )
        self.export_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.export_analyze_btn = ctk.CTkButton(
            actions_frame,
            text="🚀📊 Экспорт + Анализ",
            command=self._start_export_and_analyze,
            fg_color="#6f42c1",
            hover_color="#5a32a3",
            height=50,
            font=("Arial", 15, "bold")
        )
        self.export_analyze_btn.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Прогресс
        self.export_progress_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.export_progress_label = ctk.CTkLabel(
            self.export_progress_frame,
            text="",
            font=("Arial", 11)
        )
        self.export_progress_label.pack(pady=(10, 5))

        self.export_progress = ctk.CTkProgressBar(self.export_progress_frame)
        self.export_progress.set(0)

    def _add_chat_to_queue(self):
        """Добавить чат в очередь экспорта"""
        chat_id = self.chat_entry.get().strip()

        if not chat_id:
            messagebox.showwarning("Ошибка", "Введите ссылку!")
            return

        # Валидация дат
        start_date = self.start_date_entry.get().strip()
        end_date = self.end_date_entry.get().strip()

        if start_date:
            valid, _ = validate_date(start_date)
            if not valid:
                messagebox.showerror("Ошибка", f"Неверный формат даты начала: {start_date}\nИспользуйте ДД-ММ-ГГГГ")
                return

        if end_date:
            valid, _ = validate_date(end_date)
            if not valid:
                messagebox.showerror("Ошибка", f"Неверный формат даты конца: {end_date}\nИспользуйте ДД-ММ-ГГГГ")
                return

        # Лимит
        try:
            limit = int(self.limit_entry.get().strip() or "10000")
        except ValueError:
            messagebox.showerror("Ошибка", "Лимит должен быть числом!")
            return

        # Проверка на дубликат
        for item in self.chat_list:
            if item['chat_id'] == chat_id:
                messagebox.showinfo("Информация", f"Чат {chat_id} уже в очереди")
                return

        # Добавляем в очередь
        self.chat_list.append({
            'chat_id': chat_id,
            'start_date': start_date or None,
            'end_date': end_date or None,
            'limit': limit
        })

        # Очищаем поле чата (даты оставляем)
        self.chat_entry.delete(0, END)

        # Обновляем отображение
        self._update_queue_display()

        self._set_status(f"✅ Чат {chat_id} добавлен в очередь")

    def _clear_queue(self):
        """Очистить очередь"""
        if self.chat_list:
            if messagebox.askyesno("Подтверждение", "Очистить всю очередь?"):
                self.chat_list.clear()
                self._update_queue_display()
                self._set_status("🗑️ Очередь очищена")

    def _update_queue_display(self):
        """Обновить отображение очереди"""
        self.queue_textbox.configure(state="normal")
        self.queue_textbox.delete("1.0", END)

        if not self.chat_list:
            self.queue_textbox.insert("1.0", "Очередь пуста. Добавьте чаты для экспорта.")
        else:
            for i, item in enumerate(self.chat_list, 1):
                period = ""
                if item['start_date'] or item['end_date']:
                    start = item['start_date'] or "начало"
                    end = item['end_date'] or "сейчас"
                    period = f" | {start} — {end}"

                line = f"{i}. {item['chat_id']}{period} | лимит: {item['limit']}\n"
                self.queue_textbox.insert(END, line)

        self.queue_textbox.configure(state="disabled")
        self.queue_count_label.configure(text=f"({len(self.chat_list)} чатов)")

    def _start_batch_export(self):
        """Запуск пакетного экспорта"""
        if not self.chat_list:
            messagebox.showwarning("Ошибка", "Добавьте хотя бы один чат в очередь!")
            return

        # Проверка конфигурации
        is_valid, msg = validate_config()
        if not is_valid:
            messagebox.showerror("Ошибка конфигурации", msg)
            return

        # Блокируем кнопки
        self._set_export_buttons_state(False)

        # Показываем прогресс
        self.export_progress_frame.pack(fill="x", pady=(15, 0))
        self.export_progress.set(0)

        # Запускаем в отдельном потоке
        thread = threading.Thread(
            target=self._run_batch_export,
            args=(False,),  # analyze_after=False
            daemon=True
        )
        thread.start()

    def _start_export_and_analyze(self):
        """Экспорт + анализ всех файлов"""
        if not self.chat_list:
            messagebox.showwarning("Ошибка", "Добавьте хотя бы один чат в очередь!")
            return

        # Проверка конфигурации
        is_valid, msg = validate_config()
        if not is_valid:
            messagebox.showerror("Ошибка конфигурации", msg)
            return

        # Блокируем кнопки
        self._set_export_buttons_state(False)

        # Показываем прогресс
        self.export_progress_frame.pack(fill="x", pady=(15, 0))
        self.export_progress.set(0)

        # Запускаем в отдельном потоке
        thread = threading.Thread(
            target=self._run_batch_export,
            args=(True,),  # analyze_after=True
            daemon=True
        )
        thread.start()

    def _run_batch_export(self, analyze_after: bool):
        """Выполнение пакетного экспорта (в отдельном потоке)"""
        from services.telegram import export_telegram_csv
        from ui.auth_dialog import TelegramCodeHandler

        total = len(self.chat_list)
        exported_files = []
        errors = []

        # Создаём обработчик авторизации один раз
        code_handler = TelegramCodeHandler(self.root)

        for i, item in enumerate(self.chat_list):
            chat_id = item['chat_id']

            # Обновляем прогресс
            progress = i / total
            self.root.after(0, lambda p=progress, c=chat_id, idx=i: self._update_export_progress(p,
                                                                                                 f"[{idx + 1}/{total}] Экспорт: {c}"))

            try:
                # Use legacy export function for GUI mode
                from services.telegram import export_telegram_csv_legacy

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                result = loop.run_until_complete(
                    export_telegram_csv_legacy(
                        chat=chat_id,
                        start_date=item['start_date'],
                        end_date=item['end_date'],
                        limit=item['limit'],
                        code_handler=code_handler
                    )
                )
                loop.close()

                if result:
                    exported_files.append(result)
                    self.root.after(0, lambda c=chat_id: self._set_status(f"✅ Экспортирован: {c}"))

            except Exception as e:
                errors.append(f"{chat_id}: {str(e)}")
                self.root.after(0, lambda c=chat_id, err=str(e): self._set_status(f"❌ Ошибка {c}: {err}"))

        # Экспорт завершён
        self.root.after(0, lambda: self._update_export_progress(1.0, "Экспорт завершён"))

        # Анализ если нужен
        if analyze_after and exported_files:
            self.root.after(0, lambda: self._update_export_progress(0, "Запуск анализа..."))
            self._run_analysis_after_export()
        else:
            # Показываем результат
            self.root.after(0, lambda: self._show_export_result(exported_files, errors))
            self.root.after(0, lambda: self._set_export_buttons_state(True))
            self.root.after(0, lambda: self.export_progress_frame.pack_forget())

    def _run_analysis_after_export(self):
        """Запуск анализа после экспорта"""
        from services.analyzer import analyze_csv_folder, API_DELAY_SECONDS

        def progress_callback(current, total, filename, status):
            """Колбэк для обновления прогресса"""
            progress = current / total

            if status == "analyzing":
                text = f"[{current}/{total}] 🤖 Анализ: {filename}"
            elif status == "waiting":
                text = f"[{current}/{total}] ⏳ Пауза {API_DELAY_SECONDS} сек..."
            else:
                text = f"[{current}/{total}] {filename}"

            self.root.after(0, lambda p=progress: self.export_progress.set(p))
            self.root.after(0, lambda t=text: self.export_progress_label.configure(text=t))

        try:
            self.root.after(0, lambda: self._update_export_progress(0, "🤖 Запуск анализа CSV файлов..."))

            result = analyze_csv_folder(progress_callback=progress_callback)

            self.root.after(0, lambda: self._update_export_progress(1.0, "✅ Анализ завершён"))
            self.root.after(0, lambda r=result: self._show_analysis_result(r))

        except Exception as e:
            self.root.after(0, lambda err=str(e): messagebox.showerror("Ошибка анализа", err))

        finally:
            self.root.after(0, lambda: self._set_export_buttons_state(True))
            self.root.after(0, lambda: self.export_progress_frame.pack_forget())

    def _update_export_progress(self, value: float, text: str):
        """Обновление прогресса экспорта"""
        self.export_progress.set(value)
        self.export_progress_label.configure(text=text)

    def _show_export_result(self, exported: List[str], errors: List[str]):
        """Показать результат экспорта"""
        msg = f"✅ Экспортировано файлов: {len(exported)}"
        if errors:
            msg += f"\n❌ Ошибок: {len(errors)}"
            for err in errors[:5]:  # Показываем первые 5 ошибок
                msg += f"\n  • {err}"
            if len(errors) > 5:
                msg += f"\n  ... и ещё {len(errors) - 5}"

        messagebox.showinfo("Результат экспорта", msg)

        # Очищаем очередь после успешного экспорта
        if exported:
            self.chat_list.clear()
            self._update_queue_display()

    def _set_export_buttons_state(self, enabled: bool):
        """Включить/выключить кнопки экспорта"""
        state = "normal" if enabled else "disabled"
        self.export_btn.configure(state=state)
        self.export_analyze_btn.configure(state=state)

    # =========================================================================
    # ВКЛАДКА АНАЛИЗА
    # =========================================================================

    def _create_analyze_tab(self):
        """Вкладка анализа CSV файлов"""
        main_frame = ctk.CTkFrame(self.tab_analyze, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Заголовок
        ctk.CTkLabel(
            main_frame,
            text="Анализ CSV файлов через Claude API",
            font=("Arial", 18, "bold")
        ).pack(pady=(0, 20))

        # Информация о папках
        info_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        info_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            info_frame,
            text="📁 Расположение файлов",
            font=("Arial", 13, "bold")
        ).pack(pady=(15, 10))

        paths_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        paths_frame.pack(fill="x", padx=15, pady=(0, 15))

        # Входная папка
        input_path_frame = ctk.CTkFrame(paths_frame, fg_color="transparent")
        input_path_frame.pack(fill="x", pady=3)

        ctk.CTkLabel(input_path_frame, text="Входные CSV:", width=120, anchor="w").pack(side="left")
        self.input_path_label = ctk.CTkLabel(
            input_path_frame,
            text=str(get_input_folder()),
            font=("Consolas", 10),
            text_color="gray"
        )
        self.input_path_label.pack(side="left", fill="x", expand=True)

        # Выходная папка
        output_path_frame = ctk.CTkFrame(paths_frame, fg_color="transparent")
        output_path_frame.pack(fill="x", pady=3)

        ctk.CTkLabel(output_path_frame, text="Выходные DOCX:", width=120, anchor="w").pack(side="left")
        self.output_path_label = ctk.CTkLabel(
            output_path_frame,
            text=str(get_output_folder()),
            font=("Consolas", 10),
            text_color="gray"
        )
        self.output_path_label.pack(side="left", fill="x", expand=True)

        # Кнопка открытия папки
        ctk.CTkButton(
            info_frame,
            text="📂 Открыть папку приложения",
            command=self._open_app_folder,
            fg_color="#6c757d",
            hover_color="#5a6268",
            height=35
        ).pack(pady=(0, 15), padx=15, fill="x")

        # Счётчик файлов
        files_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        files_frame.pack(fill="x", pady=(0, 20))

        files_header = ctk.CTkFrame(files_frame, fg_color="transparent")
        files_header.pack(fill="x", padx=15, pady=15)

        ctk.CTkLabel(
            files_header,
            text="📊 CSV файлы для анализа:",
            font=("Arial", 13, "bold")
        ).pack(side="left")

        self.csv_count_label = ctk.CTkLabel(
            files_header,
            text="0",
            font=("Arial", 20, "bold"),
            text_color="#1f6aa5"
        )
        self.csv_count_label.pack(side="left", padx=15)

        ctk.CTkButton(
            files_header,
            text="🔄 Обновить",
            command=self._refresh_csv_count,
            width=100,
            height=30
        ).pack(side="right")

        # Список файлов
        self.csv_listbox = ctk.CTkTextbox(
            files_frame,
            height=120,
            font=("Consolas", 10),
            state="disabled"
        )
        self.csv_listbox.pack(fill="x", padx=15, pady=(0, 15))

        # Обновляем счётчик
        self._refresh_csv_count()

        # Кнопка анализа
        self.analyze_btn = ctk.CTkButton(
            main_frame,
            text="🤖 Запустить анализ всех CSV",
            command=self._start_analysis,
            fg_color="#28a745",
            hover_color="#218838",
            height=50,
            font=("Arial", 15, "bold")
        )
        self.analyze_btn.pack(fill="x", pady=(10, 0))

        # Прогресс анализа
        self.analyze_progress_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.analyze_progress_label = ctk.CTkLabel(
            self.analyze_progress_frame,
            text="",
            font=("Arial", 11)
        )
        self.analyze_progress_label.pack(pady=(15, 5))

        self.analyze_progress = ctk.CTkProgressBar(self.analyze_progress_frame)
        self.analyze_progress.set(0)

    def _refresh_csv_count(self):
        """Обновить счётчик CSV файлов"""
        csv_files = get_csv_files(get_input_folder())
        self.csv_count_label.configure(text=str(len(csv_files)))

        # Обновляем список
        self.csv_listbox.configure(state="normal")
        self.csv_listbox.delete("1.0", END)

        if csv_files:
            for f in csv_files:
                self.csv_listbox.insert(END, f"• {f}\n")
        else:
            self.csv_listbox.insert("1.0", "Нет CSV файлов для анализа")

        self.csv_listbox.configure(state="disabled")

    def _open_app_folder(self):
        """Открыть папку приложения"""
        import subprocess
        import platform

        folder = get_base_dir()

        try:
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")

    def _start_analysis(self):
        """Запуск анализа CSV файлов"""
        csv_files = get_csv_files(get_input_folder())

        if not csv_files:
            messagebox.showwarning(
                "Нет файлов",
                f"В папке {get_input_folder()} нет CSV файлов для анализа."
            )
            return

        # Подтверждение
        if not messagebox.askyesno(
                "Подтверждение",
                f"Будет проанализировано файлов: {len(csv_files)}\n\n"
                "После анализа CSV файлы будут удалены.\n"
                "Продолжить?"
        ):
            return

        # Блокируем кнопку
        self.analyze_btn.configure(state="disabled")

        # Показываем прогресс
        self.analyze_progress_frame.pack(fill="x", pady=(15, 0))
        self.analyze_progress.set(0)
        self.analyze_progress_label.configure(text="Запуск анализа...")

        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self._run_analysis, daemon=True)
        thread.start()

    def _run_analysis(self):
        """Выполнение анализа (в отдельном потоке)"""
        from services.analyzer import analyze_csv_folder, API_DELAY_SECONDS

        def progress_callback(current, total, filename, status):
            """Колбэк для обновления прогресса"""
            progress = current / total

            if status == "analyzing":
                text = f"[{current}/{total}] 🤖 Анализ: {filename}"
            elif status == "waiting":
                text = f"[{current}/{total}] ⏳ Пауза {API_DELAY_SECONDS} сек..."
            else:
                text = f"[{current}/{total}] {filename}"

            self.root.after(0, lambda p=progress: self.analyze_progress.set(p))
            self.root.after(0, lambda t=text: self.analyze_progress_label.configure(text=t))

        try:
            self.root.after(0, lambda: self.analyze_progress.set(0))
            self.root.after(0, lambda: self.analyze_progress_label.configure(text="Запуск анализа..."))

            result = analyze_csv_folder(progress_callback=progress_callback)

            self.root.after(0, lambda: self.analyze_progress.set(1.0))
            self.root.after(0, lambda: self.analyze_progress_label.configure(text="✅ Анализ завершён"))
            self.root.after(0, lambda r=result: self._show_analysis_result(r))

        except Exception as e:
            self.root.after(0, lambda err=str(e): messagebox.showerror("Ошибка", f"Ошибка анализа:\n{err}"))

        finally:
            self.root.after(0, lambda: self.analyze_btn.configure(state="normal"))
            self.root.after(0, lambda: self.analyze_progress_frame.pack_forget())
            self.root.after(0, self._refresh_csv_count)

    def _show_analysis_result(self, result: dict):
        """Показать результат анализа"""
        msg = f"✅ Успешно обработано: {result.get('success', 0)}\n"
        msg += f"❌ Ошибок: {result.get('errors', 0)}"

        if result.get('details'):
            msg += "\n\nДетали:"
            for detail in result['details'][:5]:
                msg += f"\n• {detail}"

        msg += f"\n\n📁 Результаты в папке:\n{get_output_folder()}"

        messagebox.showinfo("Анализ завершён", msg)

    # =========================================================================
    # ВКЛАДКА НАСТРОЕК
    # =========================================================================

    def _create_settings_tab(self):
        """Вкладка настроек"""
        main_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Заголовок
        ctk.CTkLabel(
            main_frame,
            text="Настройки приложения",
            font=("Arial", 18, "bold")
        ).pack(pady=(0, 20))

        # Статус конфигурации
        status_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        status_frame.pack(fill="x", pady=(0, 20))

        is_valid, msg = validate_config()
        status_color = "#28a745" if is_valid else "#dc3545"
        status_text = "✅ Приложение настроено" if is_valid else f"❌ {msg}"

        self.config_status_label = ctk.CTkLabel(
            status_frame,
            text=status_text,
            font=("Arial", 13, "bold"),
            text_color=status_color
        )
        self.config_status_label.pack(pady=15)

        # Информация о путях
        paths_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        paths_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            paths_frame,
            text="📁 Расположение данных",
            font=("Arial", 13, "bold")
        ).pack(pady=(15, 10))

        paths_info = ctk.CTkFrame(paths_frame, fg_color="transparent")
        paths_info.pack(fill="x", padx=15, pady=(0, 15))

        paths = [
            ("Базовая папка:", get_base_dir()),
            ("Конфигурация:", get_data_dir() / ".env"),
            ("Входные CSV:", get_input_folder()),
            ("Выходные DOCX:", get_output_folder()),
        ]

        for label, path in paths:
            row = ctk.CTkFrame(paths_info, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, width=130, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(path), font=("Consolas", 9), text_color="gray").pack(side="left")

        # Кнопки
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            buttons_frame,
            text="⚙️ Изменить настройки",
            command=self._open_settings,
            fg_color="#1f6aa5",
            height=45,
            font=("Arial", 13, "bold")
        ).pack(fill="x", pady=5)

        ctk.CTkButton(
            buttons_frame,
            text="📂 Открыть папку приложения",
            command=self._open_app_folder,
            fg_color="#6c757d",
            hover_color="#5a6268",
            height=40
        ).pack(fill="x", pady=5)

        ctk.CTkButton(
            buttons_frame,
            text="🔄 Перезагрузить конфигурацию",
            command=self._reload_config,
            fg_color="#ffc107",
            hover_color="#e0a800",
            text_color="black",
            height=40
        ).pack(fill="x", pady=5)

    def _open_settings(self):
        """Открыть окно настроек"""
        from ui.setup import show_setup_window
        show_setup_window(self._on_settings_saved)

    def _on_settings_saved(self):
        """Колбэк после сохранения настроек"""
        reload_config()
        self._update_config_status()
        self._set_status("✅ Настройки сохранены")

    def _reload_config(self):
        """Перезагрузить конфигурацию"""
        reload_config()
        self._update_config_status()
        self._set_status("🔄 Конфигурация перезагружена")

    def _update_config_status(self):
        """Обновить статус конфигурации"""
        is_valid, msg = validate_config()
        status_color = "#28a745" if is_valid else "#dc3545"
        status_text = "✅ Приложение настроено" if is_valid else f"❌ {msg}"
        self.config_status_label.configure(text=status_text, text_color=status_color)

    # =========================================================================
    # СТАТУС-БАР
    # =========================================================================

    def _create_status_bar(self):
        """Создание статус-бара"""
        self.status_bar = ctk.CTkFrame(self.root, height=30, corner_radius=0)
        self.status_bar.pack(fill="x", side="bottom")

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Готов к работе",
            font=("Arial", 10),
            text_color="gray"
        )
        self.status_label.pack(side="left", padx=15, pady=5)

        # Версия справа
        ctk.CTkLabel(
            self.status_bar,
            text=f"v{self.VERSION}",
            font=("Arial", 10),
            text_color="gray"
        ).pack(side="right", padx=15, pady=5)

    def _set_status(self, text: str):
        """Установить текст статуса"""
        self.status_label.configure(text=text)


def run_gui():
    """Запуск GUI приложения"""
    app = YsellAnalyzerApp()


if __name__ == "__main__":
    run_gui()