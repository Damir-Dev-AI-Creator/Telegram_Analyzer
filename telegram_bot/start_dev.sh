#!/bin/bash
# Скрипт для запуска всех компонентов в режиме разработки

echo "🚀 Запуск Telegram Bot Mini App в режиме разработки..."
echo ""

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте .env файл на основе .env.example"
    echo "   cp .env.example .env"
    exit 1
fi

# Проверка Python зависимостей
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "❌ Python зависимости не установлены!"
    echo "📦 Установите их: pip install -r requirements.txt"
    exit 1
fi

# Проверка Node.js зависимостей
if [ ! -d "frontend/node_modules" ]; then
    echo "❌ Frontend зависимости не установлены!"
    echo "📦 Установите их: cd frontend && npm install"
    exit 1
fi

echo "✅ Все проверки пройдены!"
echo ""

# Создание директорий
mkdir -p data
mkdir -p /tmp/telegram_bot_uploads
mkdir -p /tmp/telegram_bot_sessions

echo "📂 Директории созданы"
echo ""

# Функция для остановки всех процессов при выходе
cleanup() {
    echo ""
    echo "🛑 Остановка всех компонентов..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "🔧 Запуск компонентов..."
echo ""

# Запуск Backend API
echo "1️⃣ Запуск Backend API на порту 8000..."
python3 -m uvicorn backend.api:app --reload --port 8000 &
BACKEND_PID=$!
sleep 2

# Запуск Frontend
echo "2️⃣ Запуск Frontend на порту 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..
sleep 3

# Запуск Telegram Bot
echo "3️⃣ Запуск Telegram Bot..."
python3 bot.py &
BOT_PID=$!
sleep 2

echo ""
echo "✅ Все компоненты запущены!"
echo ""
echo "📋 Информация:"
echo "   Backend API:   http://localhost:8000"
echo "   Frontend:      http://localhost:3000"
echo "   API Docs:      http://localhost:8000/docs"
echo ""
echo "🤖 Найдите вашего бота в Telegram и отправьте /start"
echo ""
echo "⏹️  Для остановки нажмите Ctrl+C"
echo ""

# Ожидание
wait
