# core/db_manager.py
"""Менеджер для работы с базой данных"""

from typing import Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from core.database import User, UserSettings, get_session_maker
from cryptography.fernet import Fernet
import os

logger = logging.getLogger(__name__)

# Ключ шифрования для session_string (в продакшене хранить в .env!)
# Для простоты генерируем один раз и сохраняем в файл
ENCRYPTION_KEY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", ".encryption_key")


def _get_or_create_encryption_key() -> bytes:
    """Получить или создать ключ шифрования"""
    if os.path.exists(ENCRYPTION_KEY_FILE):
        with open(ENCRYPTION_KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(ENCRYPTION_KEY_FILE), exist_ok=True)
        with open(ENCRYPTION_KEY_FILE, "wb") as f:
            f.write(key)
        # Установка безопасных прав доступа (только владелец может читать/писать)
        os.chmod(ENCRYPTION_KEY_FILE, 0o600)
        return key


ENCRYPTION_KEY = _get_or_create_encryption_key()
cipher = Fernet(ENCRYPTION_KEY)


def encrypt_session(session_string: str) -> str:
    """Зашифровать session string"""
    if not session_string:
        return ""
    return cipher.encrypt(session_string.encode()).decode()


def decrypt_session(encrypted: str) -> str:
    """Расшифровать session string"""
    if not encrypted:
        return ""
    return cipher.decrypt(encrypted.encode()).decode()


class DatabaseManager:
    """
    Менеджер для работы с базой данных

    Предоставляет методы для CRUD операций с пользователями
    """

    def __init__(self):
        self.session_maker = get_session_maker()

    async def get_user(self, user_id: int) -> Optional[User]:
        """
        Получить пользователя по ID

        Args:
            user_id: Telegram User ID

        Returns:
            User или None если не найден
        """
        async with self.session_maker() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """
        Создать нового пользователя

        Args:
            user_id: Telegram User ID
            username: Username (опционально)
            first_name: Имя (опционально)
            last_name: Фамилия (опционально)

        Returns:
            Созданный User
        """
        async with self.session_maker() as session:
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                created_at=datetime.utcnow(),
                last_active=datetime.utcnow()
            )

            session.add(user)

            # Создать настройки по умолчанию
            settings = UserSettings(user_id=user_id)
            session.add(settings)

            await session.commit()
            await session.refresh(user)

            logger.info(f"✅ Создан пользователь: {user_id} (@{username})")
            return user

    async def update_user(self, user_id: int, **kwargs) -> bool:
        """
        Обновить данные пользователя

        Args:
            user_id: Telegram User ID
            **kwargs: Поля для обновления

        Returns:
            True если обновлено, False если пользователь не найден
        """
        # Обработка session_string - шифрование
        if "session_string" in kwargs and kwargs["session_string"]:
            kwargs["session_string"] = encrypt_session(kwargs["session_string"])

        async with self.session_maker() as session:
            result = await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(**kwargs)
            )
            await session.commit()

            if result.rowcount > 0:
                logger.info(f"✅ Обновлен пользователь: {user_id}")
                return True
            return False

    async def get_user_session(self, user_id: int) -> Optional[str]:
        """
        Получить session string пользователя (расшифрованный)

        Args:
            user_id: Telegram User ID

        Returns:
            Расшифрованный session string или None
        """
        user = await self.get_user(user_id)
        if user and user.session_string:
            return decrypt_session(user.session_string)
        return None

    async def save_user_session(self, user_id: int, session_string: str):
        """
        Сохранить session string (зашифрованный)

        Args:
            user_id: Telegram User ID
            session_string: StringSession от Telethon
        """
        # update_user сам зашифрует session_string, не нужно делать это здесь
        await self.update_user(user_id, session_string=session_string, is_authorized=True)
        logger.info(f"✅ Сохранена сессия для пользователя: {user_id}")

    async def is_user_configured(self, user_id: int) -> bool:
        """
        Проверить настроен ли пользователь

        Args:
            user_id: Telegram User ID

        Returns:
            True если пользователь прошел onboarding
        """
        user = await self.get_user(user_id)
        return user is not None and user.is_configured

    async def is_user_authorized(self, user_id: int) -> bool:
        """
        Проверить авторизован ли пользователь в Telegram

        Args:
            user_id: Telegram User ID

        Returns:
            True если авторизован
        """
        user = await self.get_user(user_id)
        return user is not None and user.is_authorized

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """
        Получить настройки пользователя

        Args:
            user_id: Telegram User ID

        Returns:
            UserSettings или None
        """
        async with self.session_maker() as session:
            result = await session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def update_user_settings(self, user_id: int, **kwargs) -> bool:
        """
        Обновить настройки пользователя

        Args:
            user_id: Telegram User ID
            **kwargs: Поля для обновления

        Returns:
            True если обновлено
        """
        async with self.session_maker() as session:
            result = await session.execute(
                update(UserSettings)
                .where(UserSettings.user_id == user_id)
                .values(**kwargs)
            )
            await session.commit()

            return result.rowcount > 0

    async def delete_user(self, user_id: int) -> bool:
        """
        Удалить пользователя и все его данные

        Args:
            user_id: Telegram User ID

        Returns:
            True если удален
        """
        async with self.session_maker() as session:
            result = await session.execute(
                delete(User).where(User.user_id == user_id)
            )
            await session.commit()

            if result.rowcount > 0:
                logger.info(f"🗑️ Удален пользователь: {user_id}")
                return True
            return False

    async def update_last_active(self, user_id: int):
        """
        Обновить время последней активности

        Args:
            user_id: Telegram User ID
        """
        await self.update_user(user_id, last_active=datetime.utcnow())

    async def get_all_users_count(self) -> int:
        """
        Получить количество всех пользователей

        Returns:
            Количество пользователей
        """
        async with self.session_maker() as session:
            result = await session.execute(select(User))
            return len(result.all())


# Глобальный экземпляр менеджера (создается после init_database)
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Получить глобальный экземпляр DatabaseManager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
