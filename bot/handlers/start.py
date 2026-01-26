# bot/handlers/start.py
"""Обработчики базовых команд: /start, /help"""

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
import logging

logger = logging.getLogger(__name__)

# Создаем router для этого модуля
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Обработчик команды /start
    Приветствие и краткое описание возможностей
    """
    logger.info(f"User {message.from_user.id} started the bot")

    await message.answer(
        "🎯 <b>Telegram Analyzer Bot</b>\n\n"
        "Привет! Я помогу экспортировать ваши Telegram чаты в CSV формат.\n\n"
        "<b>📊 Возможности:</b>\n"
        "• Экспорт истории сообщений из любого чата\n"
        "• Поддержка каналов, групп и личных чатов\n"
        "• Фильтрация по датам и пользователям\n"
        "• Быстрый экспорт через MTProto API\n\n"
        "<b>🚀 Быстрый старт:</b>\n"
        "1. Отправьте /export и укажите Chat ID\n"
        "2. Дождитесь завершения экспорта\n"
        "3. Получите CSV файл\n\n"
        "<b>📖 Команды:</b>\n"
        "/export - Экспорт чата\n"
        "/help - Подробная справка\n\n"
        "Используйте /help для подробных инструкций."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Обработчик команды /help
    Подробная справка по использованию
    """
    logger.info(f"User {message.from_user.id} requested help")

    help_text = """
<b>📖 Подробная справка</b>

<b>🎯 Как экспортировать чат:</b>

1️⃣ <b>Отправьте команду:</b>
<code>/export CHAT_ID</code>

Где CHAT_ID может быть:
• Числовой ID: <code>-1001234567890</code>
• Username: <code>@channelname</code>
• Ссылка: <code>https://t.me/channelname</code>

<b>Примеры:</b>
<code>/export -1001234567890</code>
<code>/export @durov</code>
<code>/export https://t.me/telegram</code>

━━━━━━━━━━━━━━━━━━━━━━

<b>📋 Как найти Chat ID:</b>

<b>Метод 1:</b> Через @userinfobot
1. Найдите @userinfobot в Telegram
2. Перешлите сообщение из нужного чата боту
3. Скопируйте Chat ID из ответа

<b>Метод 2:</b> Через веб-версию
1. Откройте https://web.telegram.org
2. Откройте нужный канал
3. Посмотрите URL: <code>https://web.telegram.org/k/#-1001234567890</code>
4. Скопируйте числовой ID

<b>Метод 3:</b> Для публичных каналов
Можно использовать @username или ссылку t.me

━━━━━━━━━━━━━━━━━━━━━━

<b>⚙️ Требования:</b>

✅ Вы должны быть участником чата/канала
✅ Для приватных каналов нужен Chat ID
✅ Бот работает через ваш User Account

━━━━━━━━━━━━━━━━━━━━━━

<b>📊 Формат экспорта:</b>

CSV файл со столбцами:
• Date - дата и время сообщения
• From - автор сообщения
• Text - текст сообщения

━━━━━━━━━━━━━━━━━━━━━━

<b>❓ Проблемы:</b>

<b>Ошибка "Chat not found":</b>
→ Проверьте правильность Chat ID
→ Убедитесь, что вы участник чата

<b>Экспорт не запускается:</b>
→ Проверьте настройки API_ID, API_HASH, PHONE
→ Убедитесь, что userbot авторизован

━━━━━━━━━━━━━━━━━━━━━━

<b>💬 Команды:</b>

/start - Главное меню
/export - Экспорт чата
/help - Эта справка

━━━━━━━━━━━━━━━━━━━━━━

Готовы начать? Используйте /export
"""

    await message.answer(help_text)
