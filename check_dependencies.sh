#!/bin/bash
# Скрипт проверки зависимостей перед развертыванием

echo "🔍 Проверка зависимостей для развертывания..."
echo "================================================"
echo ""

# Проверка Python версии
echo "1️⃣ Проверка версии Python..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python не найден!"
    exit 1
fi
echo "✅ Python установлен"
echo ""

# Создать временное виртуальное окружение
echo "2️⃣ Создание временного виртуального окружения..."
python3 -m venv /tmp/test_env
source /tmp/test_env/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Не удалось создать виртуальное окружение!"
    exit 1
fi
echo "✅ Виртуальное окружение создано"
echo ""

# Обновить pip
echo "3️⃣ Обновление pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo "✅ pip обновлен"
echo ""

# Тест requirements-server.txt
echo "4️⃣ Тестирование requirements-server.txt..."
pip install --dry-run -r requirements-server.txt > /tmp/test_server.log 2>&1

if [ $? -eq 0 ]; then
    echo "✅ requirements-server.txt - OK"
    SERVER_OK=1
else
    echo "⚠️  requirements-server.txt - есть проблемы"
    echo "   Смотрите /tmp/test_server.log для деталей"
    SERVER_OK=0
fi
echo ""

# Тест requirements-minimal.txt
echo "5️⃣ Тестирование requirements-minimal.txt..."
pip install --dry-run -r requirements-minimal.txt > /tmp/test_minimal.log 2>&1

if [ $? -eq 0 ]; then
    echo "✅ requirements-minimal.txt - OK"
    MINIMAL_OK=1
else
    echo "⚠️  requirements-minimal.txt - есть проблемы"
    echo "   Смотрите /tmp/test_minimal.log для деталей"
    MINIMAL_OK=0
fi
echo ""

# Очистка
deactivate
rm -rf /tmp/test_env

# Итоги
echo "================================================"
echo "📊 Результаты проверки:"
echo ""

if [ $SERVER_OK -eq 1 ]; then
    echo "✅ requirements-server.txt готов к деплою"
    echo "   Используйте Dockerfile (основной)"
elif [ $MINIMAL_OK -eq 1 ]; then
    echo "⚠️  Используйте requirements-minimal.txt"
    echo "   Измените Dockerfile или используйте Dockerfile.minimal"
else
    echo "❌ Обе версии requirements имеют проблемы"
    echo "   Проверьте логи в /tmp/test_*.log"
    exit 1
fi

echo ""
echo "🚀 Готово к развертыванию!"
