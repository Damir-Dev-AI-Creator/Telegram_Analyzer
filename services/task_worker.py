# services/task_worker.py
"""Task Worker для обработки задач экспорта и анализа в фоновом режиме"""

import asyncio
import logging
import os
from typing import Optional
from aiogram import Bot
from aiogram.types import FSInputFile

from core.queue import task_queue, Task, TaskType, TaskStatus
from core.config import BOT_TOKEN
from core.db_manager import get_db_manager
from services.telegram import export_telegram_csv
from services.analyzer import analyze_csv_with_claude, save_to_docx

logger = logging.getLogger(__name__)


class TaskWorker:
    """
    Worker для обработки задач в фоновом режиме

    Обрабатывает задачи типа:
    - EXPORT: экспорт чата в CSV
    - ANALYZE: анализ CSV через Claude API
    - EXPORT_ANALYZE: экспорт + анализ
    """

    def __init__(self):
        """Инициализация worker"""
        self.bot: Optional[Bot] = None
        self.running = False

    async def start(self):
        """Запустить worker"""
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN не настроен, worker не может запуститься")
            return

        self.bot = Bot(token=BOT_TOKEN)
        self.running = True

        logger.info("=" * 60)
        logger.info("🔧 Task Worker запущен")
        logger.info("=" * 60)

        while self.running:
            try:
                # Получить задачу из очереди (блокирующий вызов)
                task = await task_queue.get_task()

                logger.info(f"⚙️ Обработка задачи #{task.task_id} типа {task.task_type.value}")

                # Обработать задачу в зависимости от типа
                if task.task_type == TaskType.EXPORT:
                    await self._process_export(task)
                elif task.task_type == TaskType.ANALYZE:
                    await self._process_analyze(task)
                elif task.task_type == TaskType.EXPORT_ANALYZE:
                    await self._process_export_analyze(task)

                # Пометить задачу как обработанную
                task_queue.task_done()

            except asyncio.CancelledError:
                logger.info("Worker остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в worker: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def stop(self):
        """Остановить worker"""
        self.running = False
        if self.bot:
            await self.bot.session.close()
        logger.info("✅ Worker остановлен")

    async def _process_export(self, task: Task):
        """
        Обработать задачу экспорта

        Args:
            task: Задача с данными {chat_id, start_date, end_date, limit}
        """
        user_id = task.user_id
        chat_id = task.data.get('chat_id')
        start_date = task.data.get('start_date')
        end_date = task.data.get('end_date')
        limit = task.data.get('limit', 10000)

        try:
            # Уведомление о начале
            await self.bot.send_message(
                user_id,
                f"⏳ <b>Экспорт начался</b>\n\n"
                f"🆔 Задача: #{task.task_id}\n"
                f"📱 Чат: <code>{chat_id}</code>\n"
                f"📊 Лимит: {limit:,} сообщений"
            )

            # Выполнить экспорт (per-user)
            logger.info(f"Starting export for task #{task.task_id}, user {user_id}")
            file_path = await export_telegram_csv(
                user_id=user_id,
                chat=chat_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )

            # file_path теперь полный путь к файлу
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            filename = os.path.basename(file_path)
            document = FSInputFile(file_path)
            await self.bot.send_document(
                user_id,
                document=document,
                caption=(
                    f"✅ <b>Экспорт завершен!</b>\n\n"
                    f"🆔 Задача: #{task.task_id}\n"
                    f"📱 Чат: <code>{chat_id}</code>\n"
                    f"📄 Файл: <code>{filename}</code>"
                )
            )

            await task_queue.mark_completed(task.task_id)
            logger.info(f"✅ Task #{task.task_id} completed successfully")

        except Exception as e:
            logger.error(f"❌ Ошибка при экспорте задачи #{task.task_id}: {e}", exc_info=True)

            await self.bot.send_message(
                user_id,
                f"❌ <b>Ошибка экспорта</b>\n\n"
                f"🆔 Задача: #{task.task_id}\n"
                f"📱 Чат: <code>{chat_id}</code>\n\n"
                f"Ошибка: {str(e)}"
            )

            await task_queue.mark_failed(task.task_id)

    async def _process_analyze(self, task: Task):
        """
        Обработать задачу анализа

        Args:
            task: Задача с данными {file_path, filename}
        """
        user_id = task.user_id
        file_path = task.data.get('file_path')
        filename = task.data.get('filename', 'unknown.csv')

        try:
            # Получить пользователя и его Claude API ключ
            db = get_db_manager()
            user = await db.get_user(user_id)

            if not user:
                raise ValueError(f"User {user_id} not found")

            if not user.claude_api_key:
                raise ValueError(
                    f"Claude API key not configured for user {user_id}. "
                    f"Please configure it using /settings command."
                )

            # Уведомление о начале
            await self.bot.send_message(
                user_id,
                f"🤖 <b>Анализ начался</b>\n\n"
                f"🆔 Задача: #{task.task_id}\n"
                f"📄 Файл: <code>{filename}</code>\n\n"
                f"⏳ Отправляю данные в Claude API..."
            )

            # Выполнить анализ через Claude API с per-user ключом
            logger.info(f"Starting analysis for task #{task.task_id}, user {user_id}")

            # Запустить анализ в отдельном потоке (т.к. analyze_csv_with_claude синхронный)
            loop = asyncio.get_event_loop()
            analysis_text = await loop.run_in_executor(
                None,
                analyze_csv_with_claude,
                file_path,
                user.claude_api_key  # Per-user Claude API key
            )

            # Создать DOCX файл в per-user папке
            base_filename = os.path.basename(filename)
            output_filename = base_filename.replace('.csv', '_analysis.docx')

            # Per-user папка для анализов
            user_output_folder = os.path.join("data", "users", str(user_id), "analysis")
            os.makedirs(user_output_folder, exist_ok=True)
            output_path = os.path.join(user_output_folder, output_filename)

            await loop.run_in_executor(
                None,
                save_to_docx,
                analysis_text,
                output_path,
                base_filename
            )

            # Отправить DOCX файл
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Файл анализа не найден: {output_path}")

            document = FSInputFile(output_path)
            await self.bot.send_document(
                user_id,
                document=document,
                caption=(
                    f"✅ <b>Анализ завершен!</b>\n\n"
                    f"🆔 Задача: #{task.task_id}\n"
                    f"📄 Файл: <code>{filename}</code>\n"
                    f"🤖 Модель: Claude Sonnet 4\n"
                    f"📊 Результат: <code>{output_filename}</code>"
                )
            )

            await task_queue.mark_completed(task.task_id)
            logger.info(f"✅ Задача #{task.task_id} (анализ) завершена успешно")

        except Exception as e:
            logger.error(f"❌ Ошибка при анализе задачи #{task.task_id}: {e}", exc_info=True)

            await self.bot.send_message(
                user_id,
                f"❌ <b>Ошибка анализа</b>\n\n"
                f"🆔 Задача: #{task.task_id}\n"
                f"📄 Файл: <code>{filename}</code>\n\n"
                f"Ошибка: {str(e)}"
            )

            await task_queue.mark_failed(task.task_id)

    async def _process_export_analyze(self, task: Task):
        """
        Обработать комбинированную задачу экспорт + анализ

        Args:
            task: Задача с данными {chat_id, start_date, end_date, limit}
        """
        user_id = task.user_id
        chat_id = task.data.get('chat_id')
        start_date = task.data.get('start_date')
        end_date = task.data.get('end_date')
        limit = task.data.get('limit', 10000)

        try:
            # Получить пользователя и проверить Claude API ключ
            db = get_db_manager()
            user = await db.get_user(user_id)

            if not user:
                raise ValueError(f"User {user_id} not found")

            if not user.claude_api_key:
                raise ValueError(
                    f"Claude API key not configured for user {user_id}. "
                    f"Please configure it using /settings command."
                )

            # Шаг 1: Экспорт
            await self.bot.send_message(
                user_id,
                f"📊 <b>Экспорт + Анализ</b>\n\n"
                f"🆔 Задача: #{task.task_id}\n"
                f"📱 Чат: <code>{chat_id}</code>\n\n"
                f"⏳ Шаг 1/2: Экспорт чата..."
            )

            logger.info(f"Step 1/2: Export for task #{task.task_id}, user {user_id}")
            file_path = await export_telegram_csv(
                user_id=user_id,
                chat=chat_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )

            # file_path теперь полный путь к файлу
            filename = os.path.basename(file_path)

            # Отправить CSV
            document = FSInputFile(file_path)
            await self.bot.send_document(
                user_id,
                document=document,
                caption=f"✅ Экспорт завершен: <code>{filename}</code>"
            )

            # Шаг 2: Анализ
            await self.bot.send_message(
                user_id,
                f"🤖 <b>Шаг 2/2: Анализ через Claude API...</b>\n\n"
                f"⏳ Это может занять некоторое время."
            )

            logger.info(f"Step 2/2: Analysis for task #{task.task_id}, user {user_id}")

            loop = asyncio.get_event_loop()
            analysis_text = await loop.run_in_executor(
                None,
                analyze_csv_with_claude,
                file_path,
                user.claude_api_key  # Per-user Claude API key
            )

            # Создать DOCX в per-user папке
            output_filename = filename.replace('.csv', '_analysis.docx')
            user_output_folder = os.path.join("data", "users", str(user_id), "analysis")
            os.makedirs(user_output_folder, exist_ok=True)
            output_path = os.path.join(user_output_folder, output_filename)

            await loop.run_in_executor(
                None,
                save_to_docx,
                analysis_text,
                output_path,
                filename
            )

            # Отправить DOCX
            if os.path.exists(output_path):
                document = FSInputFile(output_path)
                await self.bot.send_document(
                    user_id,
                    document=document,
                    caption=(
                        f"✅ <b>Анализ завершен!</b>\n\n"
                        f"🆔 Задача: #{task.task_id}\n"
                        f"📱 Чат: <code>{chat_id}</code>\n"
                        f"📊 CSV: <code>{filename}</code>\n"
                        f"📄 Анализ: <code>{output_filename}</code>"
                    )
                )

            await task_queue.mark_completed(task.task_id)
            logger.info(f"✅ Task #{task.task_id} (export+analyze) completed successfully")

        except Exception as e:
            logger.error(f"❌ Ошибка при экспорт+анализ задачи #{task.task_id}: {e}", exc_info=True)

            await self.bot.send_message(
                user_id,
                f"❌ <b>Ошибка</b>\n\n"
                f"🆔 Задача: #{task.task_id}\n"
                f"📱 Чат: <code>{chat_id}</code>\n\n"
                f"Ошибка: {str(e)}"
            )

            await task_queue.mark_failed(task.task_id)
