"""
Обработчик настроек пользователя
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)


class SettingsHandler:
    """Обработчик настроек API ключей"""

    def __init__(self, user_manager):
        self.user_manager = user_manager

    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню настроек"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id

        # Получаем текущие настройки
        settings = self.user_manager.get_settings(user_id)
        has_telegram = self.user_manager.has_telegram_config(user_id)
        has_claude = self.user_manager.has_claude_config(user_id)

        telegram_status = "✅ Настроено" if has_telegram else "⚠️ Не настроено"
        claude_status = "✅ Настроено" if has_claude else "⚠️ Не настроено"

        keyboard = [
            [InlineKeyboardButton(
                f"📱 Telegram API ({telegram_status})",
                callback_data="settings_telegram"
            )],
            [InlineKeyboardButton(
                f"🤖 Claude API ({claude_status})",
                callback_data="settings_claude"
            )],
            [InlineKeyboardButton("🗑️ Очистить настройки", callback_data="settings_clear")],
            [InlineKeyboardButton("« Назад в меню", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = f"""
⚙️ **Настройки**

**Статус конфигурации:**
📱 Telegram API: {telegram_status}
🤖 Claude API: {claude_status}

Выберите что настроить:
"""

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def handle_settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback кнопок настроек"""
        query = update.callback_query
        await query.answer()

        data = query.data

        if data == "settings_telegram":
            await self._setup_telegram(update, context)
        elif data == "settings_claude":
            await self._setup_claude(update, context)
        elif data == "settings_clear":
            await self._clear_settings(update, context)

    async def _setup_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Настройка Telegram API"""
        keyboard = [[InlineKeyboardButton("« Отмена", callback_data="settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = """
📱 **Настройка Telegram API**

**Как получить ключи:**
1. Откройте https://my.telegram.org/apps
2. Войдите с вашим номером телефона
3. Нажмите "Create application"
4. Заполните форму (любые данные)
5. Скопируйте **api_id** и **api_hash**

**Введите данные в формате:**
```
api_id|api_hash|phone
```

**Пример:**
```
1234567|abcdef1234567890abcdef1234567890|+79991234567
```

Отправьте сообщение с вашими данными:
"""

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        # Сохраняем состояние
        context.user_data['state'] = 'settings_telegram_input'

    async def _setup_claude(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Настройка Claude API"""
        keyboard = [[InlineKeyboardButton("« Отмена", callback_data="settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = """
🤖 **Настройка Claude API**

**Как получить ключ:**
1. Откройте https://console.anthropic.com
2. Зарегистрируйтесь или войдите
3. Перейдите в раздел "API Keys"
4. Нажмите "Create Key"
5. Скопируйте ключ (начинается с `sk-ant-...`)

Отправьте ваш Claude API ключ:
"""

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        # Сохраняем состояние
        context.user_data['state'] = 'settings_claude_input'

    async def _clear_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка всех настроек"""
        user_id = update.effective_user.id

        keyboard = [
            [
                InlineKeyboardButton("✅ Да, очистить", callback_data="settings_clear_confirm"),
                InlineKeyboardButton("❌ Отмена", callback_data="settings"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = """
🗑️ **Очистка настроек**

⚠️ Вы уверены что хотите удалить ВСЕ настройки?

Будут удалены:
• Telegram API ключи
• Claude API ключ
• Номер телефона

Это действие нельзя отменить!
"""

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстового ввода настроек"""
        user_id = update.effective_user.id
        state = context.user_data.get('state')
        text = update.message.text.strip()

        if state == 'settings_telegram_input':
            await self._process_telegram_input(update, context, text)
        elif state == 'settings_claude_input':
            await self._process_claude_input(update, context, text)

    async def _process_telegram_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка ввода Telegram API данных"""
        user_id = update.effective_user.id

        try:
            # Парсим данные
            parts = text.split('|')
            if len(parts) != 3:
                await update.message.reply_text(
                    "❌ Неверный формат!\n\n"
                    "Используйте: `api_id|api_hash|phone`\n"
                    "Пример: `1234567|abcdef...|+79991234567`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            api_id, api_hash, phone = [p.strip() for p in parts]

            # Валидация
            if not api_id.isdigit():
                await update.message.reply_text(
                    "❌ API ID должен быть числом!"
                )
                return

            if len(api_hash) != 32:
                await update.message.reply_text(
                    "❌ API Hash должен быть 32 символа!"
                )
                return

            if not phone.startswith('+'):
                await update.message.reply_text(
                    "❌ Номер телефона должен начинаться с +"
                )
                return

            # Сохраняем настройки
            self.user_manager.update_setting(user_id, 'telegram_api_id', api_id)
            self.user_manager.update_setting(user_id, 'telegram_api_hash', api_hash)
            self.user_manager.update_setting(user_id, 'telegram_phone', phone)

            # Очищаем состояние
            context.user_data.pop('state', None)

            keyboard = [[InlineKeyboardButton("« Назад к настройкам", callback_data="settings")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "✅ **Telegram API настроен!**\n\n"
                "Теперь вы можете экспортировать чаты.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            logger.error(f"Error processing Telegram input: {e}")
            await update.message.reply_text(
                f"❌ Ошибка сохранения: {str(e)}\n\n"
                "Попробуйте еще раз."
            )

    async def _process_claude_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка ввода Claude API ключа"""
        user_id = update.effective_user.id

        try:
            api_key = text.strip()

            # Валидация
            if not api_key.startswith('sk-ant-'):
                await update.message.reply_text(
                    "⚠️ Ключ должен начинаться с `sk-ant-`\n\n"
                    "Проверьте правильность ключа.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Сохраняем настройку
            self.user_manager.update_setting(user_id, 'claude_api_key', api_key)

            # Очищаем состояние
            context.user_data.pop('state', None)

            keyboard = [[InlineKeyboardButton("« Назад к настройкам", callback_data="settings")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "✅ **Claude API настроен!**\n\n"
                "Теперь вы можете анализировать переписки.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            logger.error(f"Error processing Claude input: {e}")
            await update.message.reply_text(
                f"❌ Ошибка сохранения: {str(e)}\n\n"
                "Попробуйте еще раз."
            )
