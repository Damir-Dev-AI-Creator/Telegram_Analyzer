#!/usr/bin/env python3
"""
Telegram Bot для Ysell Analyzer с Mini App UI
Позволяет пользователям экспортировать и анализировать Telegram чаты через веб-интерфейс
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class YsellAnalyzerBot:
    """Главный класс Telegram бота"""

    def __init__(self, token: str, webapp_url: str):
        """
        Инициализация бота

        Args:
            token: Токен Telegram бота
            webapp_url: URL веб-приложения Mini App
        """
        self.token = token
        self.webapp_url = webapp_url
        self.application = Application.builder().token(token).build()

        # Регистрация обработчиков
        self._register_handlers()

    def _register_handlers(self):
        """Регистрация всех обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("app", self.open_webapp))
        self.application.add_handler(CommandHandler("about", self.about_command))

        # Обработчик callback кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_handler))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user

        # Создаем клавиатуру с кнопкой открытия Mini App
        keyboard = [
            [InlineKeyboardButton(
                "🚀 Открыть Ysell Analyzer",
                web_app=WebAppInfo(url=self.webapp_url)
            )],
            [InlineKeyboardButton("ℹ️ О приложении", callback_data="about")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_message = f"""
👋 Привет, {user.first_name}!

Добро пожаловать в **Ysell Analyzer** - инструмент для экспорта и анализа Telegram переписок с помощью Claude AI.

🎯 **Возможности:**
• 📱 Экспорт полной истории чатов
• 🤖 Анализ с помощью Claude AI
• 📄 Генерация профессиональных отчетов
• 🔒 Безопасное хранение ваших настроек

🔑 **Приватность:**
Ваши API ключи (Telegram и Claude) хранятся только у вас!

Нажмите кнопку ниже, чтобы начать:
"""

        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def open_webapp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Открытие Mini App"""
        keyboard = [
            [InlineKeyboardButton(
                "🚀 Открыть приложение",
                web_app=WebAppInfo(url=self.webapp_url)
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Нажмите кнопку ниже для открытия Ysell Analyzer:",
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 **Руководство по использованию**

**Команды бота:**
/start - Главное меню
/app - Открыть приложение
/help - Это сообщение
/about - О приложении

**Как начать работу:**

1️⃣ **Получите API ключи Telegram:**
   • Перейдите на https://my.telegram.org/apps
   • Создайте приложение
   • Скопируйте API_ID и API_HASH

2️⃣ **Получите Claude API ключ:**
   • Зарегистрируйтесь на https://console.anthropic.com
   • Создайте API ключ
   • Скопируйте его

3️⃣ **Настройте приложение:**
   • Откройте Ysell Analyzer через кнопку
   • Перейдите в раздел "Настройки"
   • Введите свои API ключи
   • Сохраните настройки

4️⃣ **Используйте приложение:**
   • **Экспорт**: Укажите username чата и даты
   • **Анализ**: Загрузите CSV и получите отчет

🔒 **Безопасность:**
Все ключи хранятся в зашифрованном виде и доступны только вам!

❓ Возникли вопросы? Напишите команду /about
"""

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /about"""
        about_text = """
ℹ️ **О приложении Ysell Analyzer**

**Версия:** 0.3.0
**Технологии:**
• Python + Telethon (Telegram API)
• Anthropic Claude AI
• FastAPI + React (Mini App)

**Основные возможности:**

📱 **Экспорт сообщений:**
   • Полная история чата (неограниченно)
   • Фильтрация по датам
   • Экспорт в CSV формат
   • Поддержка User Account режима

🤖 **AI Анализ:**
   • Claude Opus 4.5 / Sonnet 4
   • Умный анализ переписок
   • Генерация DOCX отчетов
   • Поддержка больших файлов (3000+ строк)

🔒 **Приватность:**
   • Локальное хранение ключей
   • Шифрование данных
   • Нет доступа к вашим чатам
   • Открытый исходный код

🌐 **Платформы:**
   • Telegram Bot (Mini App)
   • Desktop (Windows, macOS, Linux)

📧 **Поддержка:**
GitHub: https://github.com/Damir-Dev-AI-Creator/Telegram_Analyzer

Лицензия: MIT License
"""

        await update.message.reply_text(about_text, parse_mode='Markdown')

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на inline кнопки"""
        query = update.callback_query
        await query.answer()

        if query.data == "about":
            await self.about_command(update, context)
        elif query.data == "help":
            await self.help_command(update, context)

    def run(self):
        """Запуск бота"""
        logger.info("Запуск Telegram бота...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Главная функция для запуска бота"""
    # Загрузка переменных окружения
    from dotenv import load_dotenv
    load_dotenv()

    # Получение конфигурации
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    webapp_url = os.getenv("WEBAPP_URL", "http://localhost:3000")

    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен в .env файле!")

    # Создание и запуск бота
    bot = YsellAnalyzerBot(bot_token, webapp_url)
    bot.run()


if __name__ == "__main__":
    main()
