"""
Модели базы данных для Telegram Bot
Используется SQLAlchemy + SQLite для хранения пользовательских данных
"""

import os
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

# База для моделей
Base = declarative_base()


# === Модели === #

class User(Base):
    """Модель пользователя Telegram"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    export_tasks = relationship("ExportTask", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class UserSettings(Base):
    """Настройки пользователя (API ключи)"""
    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)

    # Telegram API настройки (зашифрованы)
    telegram_api_id = Column(Text, nullable=True)
    telegram_api_hash = Column(Text, nullable=True)
    telegram_phone = Column(Text, nullable=True)

    # Claude API настройки (зашифрованы)
    claude_api_key = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id})>"


class ExportTask(Base):
    """Задача экспорта Telegram чата"""
    __tablename__ = 'export_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Параметры экспорта
    chat_identifier = Column(String(255), nullable=False)
    date_from = Column(String(50), nullable=True)
    date_to = Column(String(50), nullable=True)

    # Статус задачи
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    progress = Column(Integer, default=0)  # 0-100%
    error = Column(Text, nullable=True)

    # Результат
    output_file = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Связи
    user = relationship("User", back_populates="export_tasks")

    def __repr__(self):
        return f"<ExportTask(id={self.id}, status={self.status}, chat={self.chat_identifier})>"


# === Database Manager === #

class Database:
    """Менеджер базы данных с шифрованием"""

    def __init__(self, db_path: str = None, encryption_key: str = None):
        """
        Инициализация БД

        Args:
            db_path: Путь к файлу БД (по умолчанию ./data/telegram_bot.db)
            encryption_key: Ключ шифрования для API ключей
        """
        if db_path is None:
            db_dir = os.path.join(os.getcwd(), "data")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "telegram_bot.db")

        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Инициализация шифрования
        if encryption_key:
            self.cipher = Fernet(encryption_key.encode())
        else:
            # Генерируем или загружаем ключ
            self.cipher = self._init_encryption()

        logger.info(f"Database initialized at {db_path}")

    def _init_encryption(self) -> Fernet:
        """
        Инициализация шифрования

        Returns:
            Fernet cipher для шифрования/дешифрования
        """
        key_file = os.path.join(os.path.dirname(self.db_path), ".encryption_key")

        if os.path.exists(key_file):
            # Загружаем существующий ключ
            with open(key_file, "rb") as f:
                key = f.read()
        else:
            # Генерируем новый ключ
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Только владелец может читать

        return Fernet(key)

    async def init_db(self):
        """Создание таблиц в БД"""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")

    async def close(self):
        """Закрытие соединения с БД"""
        self.engine.dispose()

    def _encrypt(self, value: str) -> str:
        """Шифрование значения"""
        if not value:
            return None
        return self.cipher.encrypt(value.encode()).decode()

    def _decrypt(self, value: str) -> str:
        """Дешифрование значения"""
        if not value:
            return None
        return self.cipher.decrypt(value.encode()).decode()

    # === User операции === #

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None
    ) -> User:
        """
        Получить или создать пользователя

        Args:
            telegram_id: Telegram ID пользователя
            username: Username
            first_name: Имя
            last_name: Фамилия

        Returns:
            Объект User
        """
        session = self.SessionLocal()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()

            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"Created new user: {telegram_id}")
            else:
                # Обновляем информацию
                if username:
                    user.username = username
                if first_name:
                    user.first_name = first_name
                if last_name:
                    user.last_name = last_name
                user.updated_at = datetime.utcnow()
                session.commit()

            return user
        finally:
            session.close()

    async def get_user(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        session = self.SessionLocal()
        try:
            return session.query(User).filter_by(id=user_id).first()
        finally:
            session.close()

    # === UserSettings операции === #

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """
        Получить настройки пользователя (с дешифровкой)

        Args:
            user_id: ID пользователя

        Returns:
            Объект UserSettings или None
        """
        session = self.SessionLocal()
        try:
            settings = session.query(UserSettings).filter_by(user_id=user_id).first()

            if settings:
                # Дешифруем данные
                if settings.telegram_api_id:
                    settings.telegram_api_id = self._decrypt(settings.telegram_api_id)
                if settings.telegram_api_hash:
                    settings.telegram_api_hash = self._decrypt(settings.telegram_api_hash)
                if settings.telegram_phone:
                    settings.telegram_phone = self._decrypt(settings.telegram_phone)
                if settings.claude_api_key:
                    settings.claude_api_key = self._decrypt(settings.claude_api_key)

            return settings
        finally:
            session.close()

    async def update_user_settings(
        self,
        user_id: int,
        telegram_api_id: str = None,
        telegram_api_hash: str = None,
        telegram_phone: str = None,
        claude_api_key: str = None
    ):
        """
        Обновить настройки пользователя (с шифрованием)

        Args:
            user_id: ID пользователя
            telegram_api_id: Telegram API ID
            telegram_api_hash: Telegram API Hash
            telegram_phone: Номер телефона
            claude_api_key: Claude API ключ
        """
        session = self.SessionLocal()
        try:
            settings = session.query(UserSettings).filter_by(user_id=user_id).first()

            if not settings:
                settings = UserSettings(user_id=user_id)
                session.add(settings)

            # Шифруем и обновляем только переданные значения
            if telegram_api_id is not None:
                settings.telegram_api_id = self._encrypt(telegram_api_id)
            if telegram_api_hash is not None:
                settings.telegram_api_hash = self._encrypt(telegram_api_hash)
            if telegram_phone is not None:
                settings.telegram_phone = self._encrypt(telegram_phone)
            if claude_api_key is not None:
                settings.claude_api_key = self._encrypt(claude_api_key)

            settings.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"Updated settings for user {user_id}")
        finally:
            session.close()

    # === ExportTask операции === #

    async def create_export_task(
        self,
        user_id: int,
        chat_identifier: str,
        date_from: str = None,
        date_to: str = None
    ) -> ExportTask:
        """
        Создать задачу экспорта

        Args:
            user_id: ID пользователя
            chat_identifier: Идентификатор чата
            date_from: Дата начала
            date_to: Дата окончания

        Returns:
            Объект ExportTask
        """
        session = self.SessionLocal()
        try:
            task = ExportTask(
                user_id=user_id,
                chat_identifier=chat_identifier,
                date_from=date_from,
                date_to=date_to,
                status="pending"
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            logger.info(f"Created export task {task.id} for user {user_id}")
            return task
        finally:
            session.close()

    async def get_export_task(self, task_id: int) -> Optional[ExportTask]:
        """Получить задачу экспорта по ID"""
        session = self.SessionLocal()
        try:
            return session.query(ExportTask).filter_by(id=task_id).first()
        finally:
            session.close()

    async def update_task_status(
        self,
        task_id: int,
        status: str,
        progress: int = None,
        error: str = None
    ):
        """
        Обновить статус задачи

        Args:
            task_id: ID задачи
            status: Новый статус
            progress: Прогресс (0-100)
            error: Сообщение об ошибке
        """
        session = self.SessionLocal()
        try:
            task = session.query(ExportTask).filter_by(id=task_id).first()
            if task:
                task.status = status
                if progress is not None:
                    task.progress = progress
                if error is not None:
                    task.error = error
                if status == "completed":
                    task.completed_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()

    async def update_task_output(self, task_id: int, output_file: str):
        """
        Обновить путь к выходному файлу задачи

        Args:
            task_id: ID задачи
            output_file: Путь к файлу
        """
        session = self.SessionLocal()
        try:
            task = session.query(ExportTask).filter_by(id=task_id).first()
            if task:
                task.output_file = output_file
                session.commit()
        finally:
            session.close()

    async def get_user_tasks(self, user_id: int, limit: int = 10) -> list[ExportTask]:
        """
        Получить последние задачи пользователя

        Args:
            user_id: ID пользователя
            limit: Максимальное количество задач

        Returns:
            Список задач
        """
        session = self.SessionLocal()
        try:
            return (
                session.query(ExportTask)
                .filter_by(user_id=user_id)
                .order_by(ExportTask.created_at.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()
