#!/usr/bin/env python3
"""
Простой Telegram бот для Ysell Analyzer
Работает полностью локально, управление через кнопки и команды
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь для импорта services
sys.path.append(str(Path(__file__).parent.parent))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from user_manager import UserManager
from handlers import ExportHandler, AnalysisHandler, SettingsHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(
    MAIN_MENU,
    SETTINGS_MENU,
    EXPORT_MENU,
    ANALYSIS_MENU,
) = range(4)


class YsellAnalyzerBot:
    """Простой Telegram бот для Ysell Analyzer"""

    def __init__(self, token: str):
        """
        Инициализация бота

        Args:
            token: Токен Telegram бота от BotFather
        """
        self.token = token
        self.application = Application.builder().token(token).build()
        self.user_manager = UserManager()

        # Создаем обработчики
        self.export_handler = ExportHandler(self.user_manager)
        self.analysis_handler = AnalysisHandler(self.user_manager)
        self.settings_handler = SettingsHandler(self.user_manager)

        # Регистрация обработчиков
        self._register_handlers()

    def _register_handlers(self):
        """Регистрация всех обработчиков команд"""
        # Главные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("menu", self.show_main_menu))
        self.application.add_handler(CommandHandler("cancel", self.cancel_command))

        # Обработчики кнопок главного меню
        self.application.add_handler(CallbackQueryHandler(self.export_handler.start_export, pattern="^export$"))
        self.application.add_handler(CallbackQueryHandler(self.analysis_handler.start_analysis, pattern="^analysis$"))
        self.application.add_handler(CallbackQueryHandler(self.settings_handler.show_settings, pattern="^settings$"))
        self.application.add_handler(CallbackQueryHandler(self.show_main_menu, pattern="^main_menu$"))

        # Обработчики настроек
        self.application.add_handler(CallbackQueryHandler(
            self.settings_handler.handle_settings_callback,
            pattern="^settings_"
        ))

        # Обработчики экспорта
        self.application.add_handler(CallbackQueryHandler(
            self.export_handler.handle_export_callback,
            pattern="^export_"
        ))

        # Обработчики анализа
        self.application.add_handler(CallbackQueryHandler(
            self.analysis_handler.handle_analysis_callback,
            pattern="^analysis_"
        ))

        # Обработчик текстовых сообщений (для ввода данных)
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_text_input
        ))

        # Обработчик документов (для загрузки CSV)
        self.application.add_handler(MessageHandler(
            filters.Document.ALL,
            self.analysis_handler.handle_document
        ))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user

        welcome_message = f"""
👋 Привет, {user.first_name}!

Добро пожаловать в **Ysell Analyzer** - инструмент для экспорта и анализа Telegram переписок!

🎯 **Что я умею:**
• 📱 Экспортировать историю Telegram чатов в CSV
• 🤖 Анализировать переписки с помощью Claude AI
• 📄 Создавать профессиональные отчеты в DOCX

🔑 **Первый запуск:**
Перейдите в Настройки и укажите ваши API ключи:
1. Telegram API (api.telegram.org/apps)
2. Claude API (console.anthropic.com)

Используйте кнопки ниже для навигации!
"""

        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )
        await self.show_main_menu(update, context)

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать главное меню"""
        keyboard = [
            [
                InlineKeyboardButton("📱 Экспорт чата", callback_data="export"),
                InlineKeyboardButton("🤖 Анализ CSV", callback_data="analysis"),
            ],
            [
                InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = """
🏠 **Главное меню**

Выберите действие:
"""

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 **Справка по использованию**

**Основные команды:**
/start - Начать работу с ботом
/menu - Показать главное меню
/help - Показать эту справку
/cancel - Отменить текущее действие

**Как пользоваться:**

**1. Настройка API ключей:**
• Нажмите "⚙️ Настройки"
• Настройте Telegram API (получите на my.telegram.org/apps)
• Настройте Claude API (получите на console.anthropic.com)

**2. Экспорт чата:**
• Нажмите "📱 Экспорт чата"
• Введите идентификатор чата (@username или ID)
• При необходимости укажите даты
• Дождитесь завершения экспорта
• Скачайте CSV файл

**3. Анализ переписки:**
• Нажмите "🤖 Анализ CSV"
• Загрузите CSV файл с сообщениями
• Дождитесь анализа с Claude AI
• Скачайте DOCX отчет

**Возникли проблемы?**
Напишите /cancel для сброса текущего действия
"""

        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена текущего действия"""
        context.user_data.clear()
        await update.message.reply_text("✅ Действие отменено.")
        await self.show_main_menu(update, context)

    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстового ввода (для настроек, экспорта и т.д.)"""
        user_id = update.effective_user.id
        user_state = context.user_data.get('state')

        if not user_state:
            await update.message.reply_text(
                "Используйте /menu для открытия главного меню"
            )
            return

        # Делегируем обработку соответствующему handler
        if user_state.startswith('settings_'):
            await self.settings_handler.handle_text_input(update, context)
        elif user_state.startswith('export_'):
            await self.export_handler.handle_text_input(update, context)
        elif user_state.startswith('analysis_'):
            await self.analysis_handler.handle_text_input(update, context)

    def run(self):
        """Запуск бота"""
        logger.info("🤖 Запуск Ysell Analyzer Bot...")
        logger.info("✅ Бот готов к работе!")

        # Запускаем бота - python-telegram-bot сам управляет event loop
        try:
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except KeyboardInterrupt:
            logger.info("\n👋 Бот остановлен пользователем")
        except Exception as e:
            logger.error(f"Ошибка при работе бота: {e}")
            raise


def main():
    """Главная функция для запуска бота"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              Ysell Analyzer - Telegram Bot                  ║
║                      Версия 0.3.0                           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

    # Проверяем токен в .env файле
    from dotenv import load_dotenv
    load_dotenv()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    # Если токена нет, запрашиваем у пользователя
    if not bot_token:
        print("\n⚙️  Первая настройка")
        print("=" * 60)
        print("\n📱 Шаг 1: Получите токен бота")
        print("   1. Откройте Telegram и найдите @BotFather")
        print("   2. Отправьте команду /newbot")
        print("   3. Следуйте инструкциям BotFather")
        print("   4. Скопируйте токен (выглядит как: 123456:ABC-DEF...)")
        print("\n" + "=" * 60)

        bot_token = input("\n🔑 Вставьте токен бота: ").strip()

        if not bot_token:
            print("❌ Токен не может быть пустым!")
            return

        # Сохраняем токен в .env
        env_path = Path(__file__).parent / ".env"
        with open(env_path, "w") as f:
            f.write(f"TELEGRAM_BOT_TOKEN={bot_token}\n")

        print("\n✅ Токен сохранен в .env файл")

    print("\n🚀 Запуск бота...")
    print("=" * 60)
    print("\n📱 Найдите вашего бота в Telegram и отправьте /start")
    print("\n⏹️  Для остановки нажмите Ctrl+C")
    print("\n" + "=" * 60 + "\n")

    try:
        # Создание и запуск бота
        bot = YsellAnalyzerBot(bot_token)
        bot.run()
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        print(f"\n❌ Ошибка: {e}")
        print("\nПроверьте правильность токена бота!")

        # Удаляем неправильный токен
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            env_path.unlink()
            print("Токен удален. Запустите программу снова.")


if __name__ == "__main__":
    main()
