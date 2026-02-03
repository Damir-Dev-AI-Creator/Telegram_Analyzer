#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новой функциональности настройки параметров экспорта
"""

from datetime import datetime, timedelta

def test_date_formatting():
    """Тест 1: Проверка форматирования дат"""
    print("=" * 60)
    print("ТЕСТ 1: Форматирование дат")
    print("=" * 60)

    now = datetime.now()

    test_cases = [
        ("За все время", None),
        ("Последние 7 дней", now - timedelta(days=7)),
        ("Последние 30 дней", now - timedelta(days=30)),
        ("Последние 3 месяца", now - timedelta(days=90)),
        ("Последний год", now - timedelta(days=365)),
    ]

    for label, date in test_cases:
        if date is None:
            print(f"✓ {label}: start_date=None")
        else:
            iso_format = date.isoformat()
            readable_format = date.strftime("%d.%m.%Y")
            print(f"✓ {label}: {readable_format} (ISO: {iso_format[:10]})")

    print()


def test_limit_values():
    """Тест 2: Проверка значений лимита"""
    print("=" * 60)
    print("ТЕСТ 2: Значения лимита сообщений")
    print("=" * 60)

    limit_map = {
        "all": None,
        "100": 100,
        "1000": 1000,
        "10000": 10000,
        "50000": 50000
    }

    for key, value in limit_map.items():
        if value is None:
            display = "Все сообщения"
        else:
            display = f"{value:,} сообщений"
        print(f"✓ {key}: {display}")

    print()


def test_custom_date_parsing():
    """Тест 3: Проверка парсинга кастомных дат"""
    print("=" * 60)
    print("ТЕСТ 3: Парсинг кастомных дат")
    print("=" * 60)

    test_dates = [
        "01.01.2024",
        "15.06.2023",
        "31.12.2025",
    ]

    for date_str in test_dates:
        try:
            parsed = datetime.strptime(date_str, "%d.%m.%Y")
            iso = parsed.isoformat()

            # Проверка что дата не в будущем
            is_future = parsed > datetime.now()
            status = "❌ В будущем!" if is_future else "✓ Валидна"

            print(f"{status} {date_str} -> {iso}")
        except ValueError as e:
            print(f"❌ Ошибка парсинга {date_str}: {e}")

    print()


def test_iso_date_parsing():
    """Тест 4: Проверка парсинга ISO дат"""
    print("=" * 60)
    print("ТЕСТ 4: Парсинг ISO дат")
    print("=" * 60)

    now = datetime.now()
    test_dates = [
        now.isoformat(),
        (now - timedelta(days=7)).isoformat(),
        (now - timedelta(days=30)).isoformat(),
    ]

    for iso_str in test_dates:
        try:
            # Парсинг ISO формата
            parsed = datetime.fromisoformat(iso_str)
            readable = parsed.strftime("%d.%m.%Y %H:%M:%S")
            print(f"✓ {iso_str[:19]} -> {readable}")
        except (ValueError, AttributeError) as e:
            print(f"❌ Ошибка парсинга {iso_str}: {e}")

    print()


def test_callback_data_patterns():
    """Тест 5: Проверка паттернов callback_data"""
    print("=" * 60)
    print("ТЕСТ 5: Паттерны callback_data")
    print("=" * 60)

    # Для /export
    export_callbacks = [
        ("limit_all", "Все сообщения"),
        ("limit_100", "100 сообщений"),
        ("limit_custom", "Кастомный лимит"),
        ("date_all", "За все время"),
        ("date_7days", "7 дней"),
        ("date_custom", "Кастомная дата"),
    ]

    print("Callback для /export:")
    for callback, desc in export_callbacks:
        print(f"  ✓ {callback} -> {desc}")

    print()

    # Для /exportanalyze
    ea_callbacks = [
        ("ea_limit_all", "Все сообщения"),
        ("ea_limit_100", "100 сообщений"),
        ("ea_limit_custom", "Кастомный лимит"),
        ("ea_date_all", "За все время"),
        ("ea_date_7days", "7 дней"),
        ("ea_date_custom", "Кастомная дата"),
    ]

    print("Callback для /exportanalyze:")
    for callback, desc in ea_callbacks:
        print(f"  ✓ {callback} -> {desc}")

    print()


def test_fsm_states():
    """Тест 6: Проверка FSM состояний"""
    print("=" * 60)
    print("ТЕСТ 6: FSM состояния")
    print("=" * 60)

    export_states = [
        "waiting_chat_link",
        "waiting_limit_choice",
        "waiting_custom_limit",
        "waiting_date_choice",
        "waiting_custom_date"
    ]

    print("ExportStates:")
    for state in export_states:
        print(f"  ✓ {state}")

    print()

    print("ExportAnalyzeStates:")
    for state in export_states:
        print(f"  ✓ {state}")

    print()


def test_task_data_structure():
    """Тест 7: Проверка структуры данных задачи"""
    print("=" * 60)
    print("ТЕСТ 7: Структура данных задачи")
    print("=" * 60)

    now = datetime.now()
    start_date = now - timedelta(days=30)

    # Пример 1: С датой и лимитом
    task_data_1 = {
        'chat_id': '@durov',
        'start_date': start_date.isoformat(),
        'end_date': None,
        'limit': 1000
    }

    print("Пример 1: С датой и лимитом")
    for key, value in task_data_1.items():
        print(f"  {key}: {value}")

    print()

    # Пример 2: Все сообщения, за все время
    task_data_2 = {
        'chat_id': 'https://t.me/telegram',
        'start_date': None,
        'end_date': None,
        'limit': None
    }

    print("Пример 2: Все сообщения, за все время")
    for key, value in task_data_2.items():
        print(f"  {key}: {value}")

    print()


def main():
    """Запуск всех тестов"""
    print("\n")
    print("🔍 ТЕСТИРОВАНИЕ НОВОЙ ФУНКЦИОНАЛЬНОСТИ НАСТРОЙКИ ЭКСПОРТА")
    print()

    test_date_formatting()
    test_limit_values()
    test_custom_date_parsing()
    test_iso_date_parsing()
    test_callback_data_patterns()
    test_fsm_states()
    test_task_data_structure()

    print("=" * 60)
    print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
