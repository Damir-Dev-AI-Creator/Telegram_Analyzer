# bot/handlers/debug.py
"""Обработчик команды /status для диагностики"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
import logging

from core.db_manager import get_db_manager

logger = logging.getLogger(__name__)

# Создаем router для этого модуля
router = Router()


@router.message(Command("status"))
async def cmd_status(message: Message):
    """
    Обработчик команды /status

    Показывает статус настройки пользователя и помогает диагностировать проблемы
    """
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested status")

    try:
        db = get_db_manager()
        user = await db.get_user(user_id)
        settings = await db.get_user_settings(user_id)

        if not user:
            await message.answer(
                "❌ <b>Вы не настроены</b>\n\n"
                "Используйте /setup для настройки бота."
            )
            return

        # Формируем статус
        status_lines = [
            "📊 <b>Статус настройки</b>\n",
            f"👤 <b>Пользователь:</b> {user.username or 'Не указан'}",
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n",
        ]

        # Telegram API
        if user.is_configured:
            status_lines.append("✅ <b>Telegram API:</b> Настроен")
            if user.api_id:
                status_lines.append(f"   • API_ID: <code>{user.api_id}</code>")
            if user.phone:
                status_lines.append(f"   • Phone: <code>{user.phone}</code>")
            if user.is_authorized:
                status_lines.append(f"   • Авторизация: ✅ Активна")
            else:
                status_lines.append(f"   • Авторизация: ⚠️  Требуется повторная")
        else:
            status_lines.append("❌ <b>Telegram API:</b> Не настроен")
            status_lines.append("   → Запустите /setup для настройки")

        # Claude API
        status_lines.append("")
        if user.claude_api_key:
            key_preview = user.claude_api_key[:10] + "..." + user.claude_api_key[-4:]
            status_lines.append("✅ <b>Claude API:</b> Настроен")
            status_lines.append(f"   • Ключ: <code>{key_preview}</code>")
        else:
            status_lines.append("❌ <b>Claude API:</b> Не настроен")
            status_lines.append("   • Анализ через /analyze недоступен")
            status_lines.append("   → Запустите /setup для настройки")

        # Custom Prompt
        status_lines.append("")
        if settings and settings.custom_prompt:
            prompt_preview = settings.custom_prompt[:50] + "..."
            status_lines.append("🎯 <b>Кастомный промпт:</b> Установлен")
            status_lines.append(f"   • Длина: {len(settings.custom_prompt)} символов")
            status_lines.append(f"   • Превью: {prompt_preview}")
            status_lines.append("   → /setprompt для изменения")
        else:
            status_lines.append("📝 <b>Кастомный промпт:</b> Не установлен")
            status_lines.append("   • Используется дефолтный промпт")
            status_lines.append("   → /setprompt для настройки")

        # Диагностика
        status_lines.append("\n━━━━━━━━━━━━━━━━━━━━━━")
        status_lines.append("\n🔍 <b>Диагностика:</b>")

        issues = []
        if not user.is_configured:
            issues.append("❌ Telegram API не настроен")
        if not user.is_authorized:
            issues.append("⚠️  Требуется повторная авторизация")
        if not user.claude_api_key:
            issues.append("⚠️  Claude API не настроен (анализ недоступен)")

        if issues:
            status_lines.append("\n<b>Обнаружены проблемы:</b>")
            for issue in issues:
                status_lines.append(f"• {issue}")
            status_lines.append("\n<b>Решение:</b>")
            status_lines.append("Запустите /setup для настройки")
        else:
            status_lines.append("\n✅ Все настроено правильно!")
            status_lines.append("\n<b>Доступные команды:</b>")
            status_lines.append("• /export - Экспорт чата")
            status_lines.append("• /analyze - Анализ CSV")
            status_lines.append("• /exportanalyze - Экспорт + анализ")

        status_text = "\n".join(status_lines)
        await message.answer(status_text)

    except Exception as e:
        logger.error(f"Error in /status command: {e}", exc_info=True)
        await message.answer(
            f"❌ <b>Ошибка при получении статуса</b>\n\n"
            f"Ошибка: {str(e)}\n\n"
            f"Попробуйте /setup для повторной настройки."
        )
