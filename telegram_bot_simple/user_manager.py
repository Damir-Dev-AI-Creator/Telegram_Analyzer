"""
Менеджер пользователей и их настроек
Хранит API ключи и настройки в локальной SQLite базе
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


class UserManager:
    """Управление пользователями и их настройками"""

    def __init__(self, db_path: str = None):
        """
        Инициализация менеджера

        Args:
            db_path: Путь к файлу БД (по умолчанию ./data/users.db)
        """
        if db_path is None:
            data_dir = Path(__file__).parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "users.db"

        self.db_path = str(db_path)
        self.cipher = self._init_encryption()
        self._init_db()

    def _init_encryption(self) -> Fernet:
        """Инициализация шифрования для API ключей"""
        key_file = Path(__file__).parent / "data" / ".encryption_key"

        if key_file.exists():
            with open(key_file, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            key_file.parent.mkdir(exist_ok=True)
            with open(key_file, "wb") as f:
                f.write(key)
            # Только владелец может читать
            try:
                os.chmod(key_file, 0o600)
            except:
                pass  # Windows не поддерживает chmod

        return Fernet(key)

    def _init_db(self):
        """Создание таблиц в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица настроек (зашифрованные API ключи)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                telegram_id INTEGER PRIMARY KEY,
                telegram_api_id TEXT,
                telegram_api_hash TEXT,
                telegram_phone TEXT,
                claude_api_key TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"База данных инициализирована: {self.db_path}")

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

    def register_user(self, telegram_id: int, username: str = None,
                     first_name: str = None, last_name: str = None):
        """
        Регистрация или обновление пользователя

        Args:
            telegram_id: Telegram ID пользователя
            username: Username
            first_name: Имя
            last_name: Фамилия
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name
        """, (telegram_id, username, first_name, last_name))

        conn.commit()
        conn.close()
        logger.info(f"Пользователь зарегистрирован: {telegram_id}")

    def get_settings(self, telegram_id: int) -> Dict[str, Optional[str]]:
        """
        Получить настройки пользователя (с дешифровкой)

        Args:
            telegram_id: Telegram ID

        Returns:
            Словарь с настройками
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT telegram_api_id, telegram_api_hash, telegram_phone, claude_api_key
            FROM user_settings
            WHERE telegram_id = ?
        """, (telegram_id,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return {
                'telegram_api_id': None,
                'telegram_api_hash': None,
                'telegram_phone': None,
                'claude_api_key': None,
            }

        # Дешифруем значения
        return {
            'telegram_api_id': self._decrypt(result[0]) if result[0] else None,
            'telegram_api_hash': self._decrypt(result[1]) if result[1] else None,
            'telegram_phone': self._decrypt(result[2]) if result[2] else None,
            'claude_api_key': self._decrypt(result[3]) if result[3] else None,
        }

    def update_setting(self, telegram_id: int, key: str, value: str):
        """
        Обновить одну настройку (с шифрованием)

        Args:
            telegram_id: Telegram ID
            key: Ключ настройки (telegram_api_id, telegram_api_hash, etc.)
            value: Значение
        """
        # Проверяем валидность ключа
        valid_keys = ['telegram_api_id', 'telegram_api_hash', 'telegram_phone', 'claude_api_key']
        if key not in valid_keys:
            raise ValueError(f"Неверный ключ настройки: {key}")

        # Шифруем значение
        encrypted_value = self._encrypt(value) if value else None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Проверяем, существует ли запись
        cursor.execute("""
            SELECT telegram_id FROM user_settings WHERE telegram_id = ?
        """, (telegram_id,))

        if cursor.fetchone():
            # Обновляем существующую запись
            cursor.execute(f"""
                UPDATE user_settings
                SET {key} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (encrypted_value, telegram_id))
        else:
            # Создаем новую запись
            cursor.execute(f"""
                INSERT INTO user_settings (telegram_id, {key})
                VALUES (?, ?)
            """, (telegram_id, encrypted_value))

        conn.commit()
        conn.close()
        logger.info(f"Настройка {key} обновлена для пользователя {telegram_id}")

    def has_telegram_config(self, telegram_id: int) -> bool:
        """Проверка наличия Telegram API настроек"""
        settings = self.get_settings(telegram_id)
        return bool(
            settings.get('telegram_api_id') and
            settings.get('telegram_api_hash') and
            settings.get('telegram_phone')
        )

    def has_claude_config(self, telegram_id: int) -> bool:
        """Проверка наличия Claude API настроек"""
        settings = self.get_settings(telegram_id)
        return bool(settings.get('claude_api_key'))

    def clear_settings(self, telegram_id: int):
        """Очистить все настройки пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM user_settings WHERE telegram_id = ?
        """, (telegram_id,))

        conn.commit()
        conn.close()
        logger.info(f"Настройки очищены для пользователя {telegram_id}")
