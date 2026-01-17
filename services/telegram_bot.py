# telegram_bot.py
"""Модуль для работы с Telegram через HTTP Bot API (облегченный режим)"""

import csv
import asyncio
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict
import os

from telegram import Bot, Update, Chat
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from core.config import BOT_TOKEN, EXCLUDE_USER_ID, EXCLUDE_USERNAME, EXPORT_FOLDER

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def clean_filename(name):
    """Очистка имени чата для использования в названии файла"""
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")


class TelegramBotMonitor:
    """
    Монитор сообщений через HTTP Bot API

    ⚠️ ОГРАНИЧЕНИЯ:
    - НЕ может экспортировать историю (только новые сообщения)
    - Работает только в чатах, где бот добавлен
    - Требует прав администратора в группах/каналах
    """

    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.messages_buffer: Dict[int, List[dict]] = {}  # chat_id -> messages
        self.is_monitoring = False

    async def get_bot_chats(self) -> List[Dict]:
        """
        Получить список чатов, где бот является участником

        ⚠️ HTTP Bot API НЕ предоставляет метод получения списка чатов!
        Нужно отслеживать чаты через обновления или использовать MTProto
        """
        logger.warning("HTTP Bot API не поддерживает получение списка чатов")
        logger.warning("Используйте MTProto режим для этой функции")
        return []

    async def start_monitoring(self, chat_id: int, limit: int = 10000) -> str:
        """
        Запуск мониторинга НОВЫХ сообщений в чате

        Args:
            chat_id: ID чата для мониторинга
            limit: Максимальное количество сообщений для сохранения

        Returns:
            Путь к созданному CSV файлу

        ⚠️ ВАЖНО: Сохраняет только НОВЫЕ сообщения, не историю!
        """
        if not self.bot_token:
            raise ValueError("BOT_TOKEN не настроен")

        bot = Bot(token=self.bot_token)

        # Проверка доступа к чату
        try:
            chat = await bot.get_chat(chat_id)
            logger.info(f"✅ Бот подключен к чату: {chat.title or chat.username or chat_id}")
        except Exception as e:
            raise ValueError(f"Не удалось получить доступ к чату {chat_id}: {e}")

        # Инициализация буфера сообщений
        self.messages_buffer[chat_id] = []
        self.is_monitoring = True

        # Создание application для получения обновлений
        application = Application.builder().token(self.bot_token).build()

        # Обработчик новых сообщений
        async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if update.message and update.message.chat_id == chat_id:
                await self._process_message(update.message, chat_id, limit)

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

        logger.info(f"🤖 Начат мониторинг чата {chat_id}")
        logger.info("⚠️  Сохраняются только НОВЫЕ сообщения (история недоступна в HTTP Bot API)")

        # Запуск polling
        await application.run_polling(allowed_updates=Update.ALL_TYPES)

        # После остановки - сохранение в CSV
        return await self._save_to_csv(chat_id, chat.title or str(chat_id))

    async def _process_message(self, message, chat_id: int, limit: int):
        """Обработка нового сообщения"""
        if not message.text:
            return

        # Исключение по User ID
        if EXCLUDE_USER_ID and EXCLUDE_USER_ID != 0 and message.from_user.id == EXCLUDE_USER_ID:
            return

        sender = "Unknown"
        if message.from_user:
            sender = message.from_user.first_name or ""
            if message.from_user.last_name:
                sender += f" {message.from_user.last_name}"

        # Исключение по Username
        if EXCLUDE_USERNAME and EXCLUDE_USERNAME.strip() and EXCLUDE_USERNAME.lower() in sender.lower():
            return

        clean_text = message.text.replace('\n', ' ').replace('\r', ' ').strip()

        message_data = {
            'Date': message.date.strftime('%d-%m-%Y %H:%M:%S'),
            'From': sender,
            'Text': clean_text
        }

        # Добавление в буфер
        if chat_id not in self.messages_buffer:
            self.messages_buffer[chat_id] = []

        self.messages_buffer[chat_id].append(message_data)

        # Ограничение размера буфера
        if len(self.messages_buffer[chat_id]) > limit:
            self.messages_buffer[chat_id] = self.messages_buffer[chat_id][-limit:]

        logger.info(f"📨 Получено сообщение в чате {chat_id}: {len(self.messages_buffer[chat_id])} всего")

    async def _save_to_csv(self, chat_id: int, chat_title: str) -> str:
        """Сохранение буфера сообщений в CSV"""
        if chat_id not in self.messages_buffer or not self.messages_buffer[chat_id]:
            raise ValueError("Нет сообщений для сохранения")

        messages = self.messages_buffer[chat_id]

        # Формирование имени файла
        timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M')
        output_file = f"{clean_filename(chat_title)}_monitor_{timestamp}.csv"

        # Сохранение в CSV
        os.makedirs(EXPORT_FOLDER, exist_ok=True)
        output_filepath = os.path.join(EXPORT_FOLDER, output_file)

        fieldnames = ['Date', 'From', 'Text']
        with open(output_filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(messages)

        logger.info(f"✅ Мониторинг завершен: {output_filepath}")
        logger.info(f"📊 Сохранено сообщений: {len(messages)}")

        return output_file

    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_monitoring = False
        logger.info("⏹️  Мониторинг остановлен")


async def export_telegram_bot_mode(chat_id: int, limit: int = 10000, duration_seconds: int = 3600) -> str:
    """
    Экспорт сообщений через HTTP Bot API (только новые сообщения)

    Args:
        chat_id: ID чата
        limit: Максимальное количество сообщений
        duration_seconds: Длительность мониторинга в секундах

    Returns:
        Имя созданного CSV файла

    ⚠️ ОГРАНИЧЕНИЯ HTTP Bot API:
    - НЕ может получить историю сообщений
    - Сохраняет только новые сообщения во время работы
    - Требует прав администратора в группах
    """
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не настроен. Откройте настройки и введите токен от @BotFather.")

    monitor = TelegramBotMonitor()

    # Запуск мониторинга с таймаутом
    try:
        async with asyncio.timeout(duration_seconds):
            return await monitor.start_monitoring(chat_id, limit)
    except asyncio.TimeoutError:
        monitor.stop_monitoring()
        # Сохранение собранных сообщений
        bot = Bot(token=BOT_TOKEN)
        chat = await bot.get_chat(chat_id)
        return await monitor._save_to_csv(chat_id, chat.title or str(chat_id))


if __name__ == "__main__":
    # Тестовый запуск
    print("⚠️  HTTP Bot API режим - сохраняет только НОВЫЕ сообщения!")
    print("Для экспорта истории используйте MTProto режим")
