# bot/main.py
"""Главный файл Telegram бота"""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Импорт конфигурации
from core.config import BOT_TOKEN, OWNER_ID

# Импорт обработчиков
from bot.handlers import start, export, analyze

# Импорт middleware
from bot.middlewares.auth import AuthMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""

    # Проверка обязательных параметров
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не настроен! Добавьте его в .env файл")
        logger.error("Получить токен: https://t.me/BotFather")
        sys.exit(1)

    if not OWNER_ID or OWNER_ID == 0:
        logger.error("❌ OWNER_ID не настроен! Добавьте его в .env файл")
        logger.error("Узнать свой ID: https://t.me/userinfobot")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("🤖 Telegram Analyzer Bot")
    logger.info("=" * 60)
    logger.info(f"Owner ID: {OWNER_ID}")
    logger.info("=" * 60)

    # Инициализация бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML  # HTML форматирование по умолчанию
        )
    )

    # Инициализация диспетчера
    dp = Dispatcher()

    # Регистрация middleware
    # Важно: AuthMiddleware должен быть первым, чтобы проверять доступ
    dp.message.middleware(AuthMiddleware(owner_id=OWNER_ID))
    dp.callback_query.middleware(AuthMiddleware(owner_id=OWNER_ID))

    logger.info("✅ Middleware зарегистрирован")

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(export.router)
    dp.include_router(analyze.router)

    logger.info("✅ Обработчики зарегистрированы")

    # Удаление вебхуков (если были установлены)
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("=" * 60)
    logger.info("✅ Бот запущен и готов к работе!")
    logger.info("=" * 60)
    logger.info("Доступные команды:")
    logger.info("  /start - Приветствие и главное меню")
    logger.info("  /help  - Подробная справка")
    logger.info("  /export <chat_id> - Экспорт чата")
    logger.info("  /analyze <file> - Анализ через Claude API")
    logger.info("  /exportanalyze <chat_id> - Экспорт + анализ")
    logger.info("=" * 60)
    logger.info("Нажмите Ctrl+C для остановки")
    logger.info("=" * 60)

    # Импорт и инициализация worker
    from services.task_worker import TaskWorker
    worker = TaskWorker()

    try:
        # Запуск бота и worker параллельно
        await asyncio.gather(
            dp.start_polling(bot),
            worker.start()
        )
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    finally:
        logger.info("Закрытие соединений...")
        await worker.stop()
        await bot.session.close()
        logger.info("✅ Бот остановлен")


def run():
    """Точка входа для запуска бота"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
