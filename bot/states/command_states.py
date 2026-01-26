# bot/states/command_states.py
"""Состояния FSM для команд бота"""

from aiogram.fsm.state import State, StatesGroup


class ExportStates(StatesGroup):
    """Состояния для команды /export"""
    waiting_chat_link = State()  # Ожидание ссылки/ID чата
    waiting_limit_choice = State()  # Ожидание выбора лимита сообщений
    waiting_custom_limit = State()  # Ожидание ввода кастомного лимита
    waiting_date_choice = State()  # Ожидание выбора периода дат
    waiting_custom_date = State()  # Ожидание ввода кастомной даты


class AnalyzeStates(StatesGroup):
    """Состояния для команды /analyze"""
    waiting_file_or_name = State()  # Ожидание файла или имени файла


class ExportAnalyzeStates(StatesGroup):
    """Состояния для команды /exportanalyze"""
    waiting_chat_link = State()  # Ожидание ссылки/ID чата
    waiting_limit_choice = State()  # Ожидание выбора лимита сообщений
    waiting_custom_limit = State()  # Ожидание ввода кастомного лимита
    waiting_date_choice = State()  # Ожидание выбора периода дат
    waiting_custom_date = State()  # Ожидание ввода кастомной даты


class PromptStates(StatesGroup):
    """Состояния для команды /setprompt"""
    waiting_prompt_text = State()  # Ожидание текста промпта
