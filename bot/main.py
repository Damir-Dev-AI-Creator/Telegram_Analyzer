# bot/main.py
"""Главный файл Telegram бота"""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Импорт конфигурации
from core.config import BOT_TOKEN, reload_config
from core.first_run_setup import check_bot_token_configured, run_first_time_setup

# Импорт обработчиков
from bot.handlers import start, export, analyze, setup, prompt, debug

# Импорт инициализации БД
from core.database import init_database, close_database

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

    # Проверка первого запуска и настройка
    if not check_bot_token_configured():
        print("\n" + "=" * 60)
        print("⚠️  Первый запуск - необходима настройка")
        print("=" * 60)
        print()

        success = run_first_time_setup()
        if not success:
            print("\n❌ Настройка отменена или не удалась")
            print("Запустите бота снова для повторной настройки")
            sys.exit(1)

        # Перезагрузить конфигурацию после настройки
        reload_config()

        # Импортировать обновленный BOT_TOKEN
        from core.config import BOT_TOKEN as UPDATED_TOKEN
        global BOT_TOKEN
        BOT_TOKEN = UPDATED_TOKEN

        print("\n✅ Настройка завершена успешно!")
        print("=" * 60)
        print()

    # Проверка обязательных параметров
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не настроен! Добавьте его в .env файл")
        logger.error("Получить токен: https://t.me/BotFather")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("🤖 Telegram Analyzer Bot (Multi-User)")
    logger.info("=" * 60)

    # Инициализация базы данных
    logger.info("📦 Инициализация базы данных...")
    try:
        await init_database()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}", exc_info=True)
        sys.exit(1)

    logger.info("=" * 60)

    # Инициализация бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML  # HTML форматирование по умолчанию
        )
    )

    # Инициализация диспетчера с FSM storage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    logger.info("✅ FSM storage настроен")

    # Регистрация роутеров
    # ВАЖНО: setup должен быть первым для обработки /setup и /cancel
    dp.include_router(setup.router)
    dp.include_router(start.router)
    dp.include_router(export.router)
    dp.include_router(analyze.router)
    dp.include_router(prompt.router)
    dp.include_router(debug.router)

    logger.info("✅ Обработчики зарегистрированы")

    # Удаление вебхуков (если были установлены)
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("=" * 60)
    logger.info("✅ Бот запущен и готов к работе!")
    logger.info("=" * 60)
    logger.info("Режим: Multi-User (любой пользователь может настроить)")
    logger.info("")
    logger.info("Доступные команды:")
    logger.info("  /start  - Приветствие и главное меню")
    logger.info("  /setup  - Настройка Telegram API и Claude API")
    logger.info("  /status - Диагностика настроек и проблем")
    logger.info("  /help   - Подробная справка")
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
        await close_database()
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
