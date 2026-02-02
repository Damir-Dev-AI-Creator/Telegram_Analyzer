# services/launcher.py
"""Консольный лаунчер приложения"""

import os
import asyncio
from pathlib import Path

from core.config import (
    get_input_folder,
    get_output_folder,
    is_configured,
    validate_config
)


async def export_telegram(chat_id: str, start_date=None, end_date=None, limit=10000, code_handler=None):
    """
    DEPRECATED: Этот метод устарел и не поддерживается в multi-user версии бота.

    Используйте Telegram бота для экспорта: python main.py --bot
    Или GUI интерфейс: python main.py --gui

    Старый консольный режим больше не совместим с новой multi-user архитектурой.
    """
    print("❌ Консольный режим экспорта устарел и больше не поддерживается.")
    print("📱 Используйте Telegram бота: python main.py --bot")
    print("🖥️ Или GUI интерфейс: python main.py --gui")
    raise NotImplementedError("Console export is deprecated. Use bot mode: python main.py --bot")


def analyze_csvs():
    """Анализ CSV файлов"""
    from services.analyzer import analyze_csv_folder
    
    input_folder = get_input_folder()
    output_folder = get_output_folder()
    
    input_folder.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    analyze_csv_folder(str(input_folder), str(output_folder))


def main_menu():
    """Консольное меню"""
    print("=== Ysell Analyzer - Консольный режим ===")
    print()
    print("1. Экспорт из Telegram")
    print("2. Анализ CSV -> DOCX")
    print("3. Полный цикл (экспорт + анализ)")
    print("0. Выход")
    print()
    
    choice = input("Выберите действие (0-3): ").strip()
    
    if choice == "0":
        print("👋 До свидания!")
        return
    
    if choice in ["1", "3"]:
        # Проверка конфигурации
        is_valid, message = validate_config()
        if not is_valid:
            print(f"❌ Ошибка конфигурации: {message}")
            return
        
        chat = input("Chat ID/username (например @ysellchat): ").strip()
        if not chat:
            print("❌ Chat ID обязателен")
            return
        
        print()
        print("📅 Формат даты: ДД-ММ-ГГГГ (например 15-12-2024)")
        start_date = input("Дата начала (Enter = с начала): ").strip() or None
        end_date = input("Дата конца (Enter = до сейчас): ").strip() or None
        
        limit_input = input("Лимит сообщений (Enter = 10000): ").strip()
        limit = int(limit_input) if limit_input.isdigit() else 10000
        
        print()
        print(f"🚀 Экспорт: {chat}")
        print(f"   Период: {start_date or 'начало'} → {end_date or 'сейчас'}")
        print(f"   Лимит: {limit}")
        print()
        
        asyncio.run(export_telegram(chat, start_date, end_date, limit))
    
    if choice in ["2", "3"]:
        print()
        print("🔬 Запуск анализа...")
        analyze_csvs()
    
    if choice not in ["0", "1", "2", "3"]:
        print("❌ Неверный выбор")


if __name__ == "__main__":
    main_menu()
