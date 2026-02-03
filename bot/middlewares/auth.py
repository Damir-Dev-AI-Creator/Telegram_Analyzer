# bot/middlewares/auth.py
"""Middleware для проверки доступа к боту"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
import logging

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Проверка доступа к боту - только для владельца"""

    def __init__(self, owner_id: int):
        """
        Args:
            owner_id: Telegram User ID владельца бота
        """
        self.owner_id = owner_id
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Проверка доступа перед обработкой события

        Args:
            handler: Следующий обработчик
            event: Событие (Message, CallbackQuery и т.д.)
            data: Контекст данных

        Returns:
            Результат обработки или None если доступ запрещен
        """
        # Получить user из разных типов событий
        user = None

        if isinstance(event, Message):
            user = event.from_user
        elif hasattr(event, 'from_user'):
            user = event.from_user
        elif hasattr(event, 'message') and hasattr(event.message, 'from_user'):
            user = event.message.from_user

        # Если пользователь не определен - пропустить
        if not user:
            return await handler(event, data)

        # Проверка: только владелец
        if user.id != self.owner_id:
            logger.warning(f"Unauthorized access attempt from user {user.id} (@{user.username})")

            # Отправить сообщение об ошибке
            if isinstance(event, Message):
                await event.answer(
                    "⛔ <b>Доступ запрещен</b>\n\n"
                    "Этот бот предназначен только для владельца.\n"
                    f"Ваш ID: <code>{user.id}</code>"
                )

            return  # Прервать обработку

        # Логировать доступ
        logger.info(f"Authorized access from owner {user.id} (@{user.username})")

        # Продолжить обработку
        return await handler(event, data)
