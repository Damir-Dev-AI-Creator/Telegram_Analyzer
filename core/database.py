# core/database.py
"""Модели базы данных для multi-user системы"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Базовый класс для моделей
Base = declarative_base()

# Путь к базе данных
DATABASE_DIR = Path(__file__).parent.parent / "data"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "bot.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"


class User(Base):
    """
    Модель пользователя бота

    Каждый пользователь имеет свои API ключи и настройки
    """
    __tablename__ = "users"

    # Основные данные
    user_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)

    # Telegram API ключи
    api_id = Column(Integer, nullable=True)
    api_hash = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    # Claude API ключ (опционально)
    claude_api_key = Column(String(512), nullable=True)

    # Telethon session (зашифрованный StringSession)
    session_string = Column(Text, nullable=True)

    # Статусы
    is_configured = Column(Boolean, default=False)  # Прошел ли onboarding
    is_authorized = Column(Boolean, default=False)  # Авторизован ли в Telegram

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связь с настройками
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username}, configured={self.is_configured})>"


class UserSettings(Base):
    """
    Настройки пользователя

    Фильтры экспорта и другие персональные настройки
    """
    __tablename__ = "user_settings"

    user_id = Column(BigInteger, ForeignKey("users.user_id"), primary_key=True)

    # Фильтры экспорта
    exclude_user_id = Column(Integer, default=0)
    exclude_username = Column(String(255), default="")

    # Лимиты
    default_export_limit = Column(Integer, default=10000)

    # Кастомный промпт для анализа через Claude
    custom_prompt = Column(Text, nullable=True)

    # Связь с пользователем
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, limit={self.default_export_limit})>"


# Глобальные переменные для engine и session maker
_engine = None
_async_session_maker = None


async def init_database():
    """
    Инициализация базы данных

    Создает таблицы если их нет
    """
    global _engine, _async_session_maker

    logger.info(f"Инициализация БД: {DATABASE_PATH}")

    # Создать async engine
    _engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Отключить SQL логи
        future=True
    )

    # Создать session maker
    _async_session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Создать таблицы
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("✅ База данных инициализирована")


def get_session_maker():
    """Получить async session maker"""
    if _async_session_maker is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_database() сначала.")
    return _async_session_maker


async def close_database():
    """Закрыть соединение с БД"""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("✅ Соединение с БД закрыто")
