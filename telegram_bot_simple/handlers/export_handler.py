"""
Обработчик экспорта Telegram чатов
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# Добавляем путь к services
sys.path.append(str(Path(__file__).parent.parent.parent))
from services.telegram import TelegramExporter

logger = logging.getLogger(__name__)


class ExportHandler:
    """Обработчик экспорта чатов"""

    def __init__(self, user_manager):
        self.user_manager = user_manager

    async def start_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс экспорта"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id

        # Проверка настроек
        if not self.user_manager.has_telegram_config(user_id):
            keyboard = [[InlineKeyboardButton("⚙️ Настроить", callback_data="settings")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "⚠️ **Telegram API не настроен**\n\n"
                "Сначала настройте Telegram API ключи в разделе Настройки.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        keyboard = [[InlineKeyboardButton("« Отмена", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = """
📱 **Экспорт Telegram чата**

**Как использовать:**
Отправьте идентификатор чата в одном из форматов:

1️⃣ **Только chat_id:**
   `@channel_name` или `-1001234567890`

2️⃣ **С датами (опционально):**
   `@channel_name|2024-01-01|2024-12-31`
   `-1001234567890|2024-06-01|2024-06-30`

**Форматы дат:** YYYY-MM-DD

**Примеры:**
• `@durov` - весь чат
• `@durov|2024-01-01|2024-01-31` - только январь 2024
• `-1001234567890` - приватный чат (весь)

Отправьте идентификатор чата:
"""

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        # Сохраняем состояние
        context.user_data['state'] = 'export_chat_input'

    async def handle_export_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback кнопок экспорта"""
        # Пока не используется, но может понадобиться для дополнительных кнопок
        pass

    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода данных для экспорта"""
        user_id = update.effective_user.id
        state = context.user_data.get('state')

        if state == 'export_chat_input':
            await self._process_export_input(update, context)

    async def _process_export_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода данных для экспорта"""
        user_id = update.effective_user.id
        text = update.message.text.strip()

        try:
            # Парсим ввод
            parts = text.split('|')
            chat_id = parts[0].strip()
            date_from = parts[1].strip() if len(parts) > 1 else None
            date_to = parts[2].strip() if len(parts) > 2 else None

            # Валидация дат
            date_from_obj = None
            date_to_obj = None

            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
                except ValueError:
                    await update.message.reply_text(
                        "❌ Неверный формат даты начала!\n"
                        "Используйте: YYYY-MM-DD (например: 2024-01-01)"
                    )
                    return

            if date_to:
                try:
                    date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
                except ValueError:
                    await update.message.reply_text(
                        "❌ Неверный формат даты окончания!\n"
                        "Используйте: YYYY-MM-DD (например: 2024-12-31)"
                    )
                    return

            # Очищаем состояние
            context.user_data.pop('state', None)

            # Отправляем сообщение о начале экспорта
            status_message = await update.message.reply_text(
                "⏳ **Начинаю экспорт...**\n\n"
                f"Чат: `{chat_id}`\n"
                f"Даты: {date_from or 'все'} - {date_to or 'все'}\n\n"
                "Это может занять несколько минут...",
                parse_mode=ParseMode.MARKDOWN
            )

            # Запускаем экспорт
            await self._run_export(
                update,
                context,
                status_message,
                chat_id,
                date_from_obj,
                date_to_obj
            )

        except Exception as e:
            logger.error(f"Error processing export input: {e}")
            await update.message.reply_text(
                f"❌ Ошибка: {str(e)}\n\n"
                "Проверьте формат ввода и попробуйте снова."
            )

    async def _run_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                         status_message, chat_id: str, date_from, date_to):
        """Выполнение экспорта"""
        user_id = update.effective_user.id

        try:
            # Получаем настройки
            settings = self.user_manager.get_settings(user_id)

            # Создаем директорию для сессий пользователя
            session_dir = Path(__file__).parent.parent / "data" / "sessions" / str(user_id)
            session_dir.mkdir(parents=True, exist_ok=True)

            # Создаем директорию для экспортов
            export_dir = Path(__file__).parent.parent / "data" / "exports" / str(user_id)
            export_dir.mkdir(parents=True, exist_ok=True)

            # Обновляем статус
            await status_message.edit_text(
                "⚙️ **Подключение к Telegram...**\n\n"
                f"Чат: `{chat_id}`\n"
                f"Даты: {date_from or 'все'} - {date_to or 'все'}",
                parse_mode=ParseMode.MARKDOWN
            )

            # Создаем экспортер
            exporter = TelegramExporter(
                api_id=int(settings['telegram_api_id']),
                api_hash=settings['telegram_api_hash'],
                phone=settings['telegram_phone'],
                session_file=str(session_dir / "session")
            )

            # Запускаем экспорт
            await status_message.edit_text(
                "📥 **Экспортирую сообщения...**\n\n"
                f"Чат: `{chat_id}`\n\n"
                "⏳ Пожалуйста, подождите...",
                parse_mode=ParseMode.MARKDOWN
            )

            # Генерируем имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = export_dir / f"export_{chat_id.replace('@', '')}_{timestamp}.csv"

            # Выполняем экспорт
            result_file = await exporter.export_chat(
                chat_identifier=chat_id,
                output_file=str(output_file),
                date_from=date_from,
                date_to=date_to
            )

            # Проверяем результат
            if not os.path.exists(result_file):
                raise Exception("Файл экспорта не был создан")

            # Получаем статистику
            import csv
            with open(result_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Пропускаем заголовок
                message_count = sum(1 for _ in reader)

            file_size = os.path.getsize(result_file)
            file_size_mb = file_size / (1024 * 1024)

            # Отправляем файл пользователю
            await status_message.edit_text(
                "📤 **Отправляю файл...**",
                parse_mode=ParseMode.MARKDOWN
            )

            with open(result_file, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(result_file),
                    caption=f"✅ **Экспорт завершен!**\n\n"
                            f"📊 Статистика:\n"
                            f"• Сообщений: {message_count:,}\n"
                            f"• Размер: {file_size_mb:.2f} MB\n"
                            f"• Чат: `{chat_id}`",
                    parse_mode=ParseMode.MARKDOWN
                )

            # Удаляем статусное сообщение
            await status_message.delete()

            # Показываем меню
            keyboard = [[InlineKeyboardButton("« Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "🎉 Экспорт успешно завершен!\n\n"
                "Используйте этот CSV файл для анализа с Claude AI.",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Export error: {e}")

            error_message = str(e)
            if "Could not find the input entity" in error_message:
                error_message = "Чат не найден. Проверьте идентификатор."
            elif "AUTH_KEY_UNREGISTERED" in error_message:
                error_message = "Ошибка авторизации. Проверьте настройки Telegram API."
            elif "PHONE_NUMBER_INVALID" in error_message:
                error_message = "Неверный номер телефона. Проверьте настройки."

            await status_message.edit_text(
                f"❌ **Ошибка экспорта**\n\n"
                f"Причина: {error_message}\n\n"
                "Попробуйте:\n"
                "1. Проверить идентификатор чата\n"
                "2. Убедиться что у вас есть доступ к чату\n"
                "3. Проверить настройки Telegram API",
                parse_mode=ParseMode.MARKDOWN
            )
