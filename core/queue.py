# core/queue.py
"""Task Queue для асинхронной обработки задач экспорта и анализа"""

import asyncio
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Типы задач"""
    EXPORT = "export"
    ANALYZE = "analyze"
    EXPORT_ANALYZE = "export_analyze"


class TaskStatus(Enum):
    """Статусы задач"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Структура задачи"""
    task_id: int
    task_type: TaskType
    user_id: int
    data: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING


class TaskQueue:
    """
    Очередь задач на основе asyncio.Queue

    Поддерживает задачи экспорта, анализа и комбинированные
    """

    def __init__(self, maxsize: int = 100):
        """
        Args:
            maxsize: Максимальный размер очереди
        """
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._task_counter: int = 0
        self._tasks: Dict[int, Task] = {}
        self._lock = asyncio.Lock()

    async def add_task(
        self,
        task_type: TaskType,
        user_id: int,
        data: Dict[str, Any]
    ) -> int:
        """
        Добавить задачу в очередь

        Args:
            task_type: Тип задачи (export, analyze, export_analyze)
            user_id: ID пользователя Telegram
            data: Данные задачи (chat_id, file_path и т.д.)

        Returns:
            task_id: ID созданной задачи
        """
        async with self._lock:
            self._task_counter += 1
            task_id = self._task_counter

            task = Task(
                task_id=task_id,
                task_type=task_type,
                user_id=user_id,
                data=data,
                status=TaskStatus.PENDING
            )

            self._tasks[task_id] = task
            await self._queue.put(task)

            logger.info(
                f"✅ Задача #{task_id} добавлена в очередь. "
                f"Тип: {task_type.value}, User: {user_id}"
            )

            return task_id

    async def get_task(self) -> Task:
        """
        Получить следующую задачу из очереди (блокирующий вызов)

        Returns:
            Task: Следующая задача для обработки
        """
        task = await self._queue.get()

        async with self._lock:
            if task.task_id in self._tasks:
                self._tasks[task.task_id].status = TaskStatus.PROCESSING

        logger.info(f"📋 Задача #{task.task_id} получена из очереди")
        return task

    async def mark_completed(self, task_id: int):
        """Отметить задачу как завершенную"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.COMPLETED
                logger.info(f"✅ Задача #{task_id} завершена")

    async def mark_failed(self, task_id: int):
        """Отметить задачу как провалившуюся"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.FAILED
                logger.error(f"❌ Задача #{task_id} провалена")

    def get_task_status(self, task_id: int) -> TaskStatus:
        """
        Получить статус задачи

        Args:
            task_id: ID задачи

        Returns:
            TaskStatus или None если задача не найдена
        """
        task = self._tasks.get(task_id)
        return task.status if task else None

    def get_user_tasks(self, user_id: int) -> list:
        """
        Получить все задачи пользователя

        Args:
            user_id: ID пользователя

        Returns:
            List[Task]: Список задач пользователя
        """
        return [
            task for task in self._tasks.values()
            if task.user_id == user_id
        ]

    def get_queue_size(self) -> int:
        """Получить текущий размер очереди"""
        return self._queue.qsize()

    def task_done(self):
        """Пометить задачу как обработанную (для Queue.join())"""
        self._queue.task_done()

    async def wait_empty(self):
        """Дождаться пока очередь опустеет"""
        await self._queue.join()


# Глобальный экземпляр очереди
task_queue = TaskQueue(maxsize=100)
