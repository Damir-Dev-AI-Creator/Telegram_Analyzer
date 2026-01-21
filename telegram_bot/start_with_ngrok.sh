#!/bin/bash
# Скрипт для запуска с ngrok (требует установленный ngrok)

echo "🚀 Запуск Telegram Bot Mini App с ngrok..."
echo ""

# Проверка ngrok
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok не установлен!"
    echo "📥 Установите: https://ngrok.com/download"
    echo "   или: brew install ngrok"
    exit 1
fi

echo "✅ ngrok найден"
echo ""

# Проверка .env
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте .env файл: cp .env.example .env"
    exit 1
fi

echo "✅ .env найден"
echo ""

# Создание директорий
mkdir -p data
mkdir -p /tmp/telegram_bot_uploads
mkdir -p /tmp/telegram_bot_sessions

echo "📂 Директории созданы"
echo ""

# Функция остановки
cleanup() {
    echo ""
    echo "🛑 Остановка всех компонентов..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "🔧 Запуск компонентов..."
echo ""

# Запуск Backend
echo "1️⃣ Запуск Backend API на порту 8000..."
python3 -m uvicorn backend.api:app --reload --port 8000 &
BACKEND_PID=$!
sleep 3

# Запуск Frontend
echo "2️⃣ Запуск Frontend на порту 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..
sleep 4

# Запуск ngrok для Frontend
echo "3️⃣ Запуск ngrok для Frontend (порт 3000)..."
ngrok http 3000 --log=stdout > /tmp/ngrok_frontend.log &
NGROK_FRONTEND_PID=$!
sleep 3

# Запуск ngrok для Backend
echo "4️⃣ Запуск ngrok для Backend (порт 8000)..."
ngrok http 8000 --log=stdout > /tmp/ngrok_backend.log &
NGROK_BACKEND_PID=$!
sleep 3

echo ""
echo "✅ Все компоненты запущены!"
echo ""
echo "📋 Информация:"
echo ""

# Получаем ngrok URLs
echo "⏳ Получение ngrok URLs..."
sleep 2

# Frontend URL
FRONTEND_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | head -1 | cut -d'"' -f4)
# Backend URL
BACKEND_URL=$(curl -s http://localhost:4041/api/tunnels | grep -o '"public_url":"https://[^"]*' | head -1 | cut -d'"' -f4)

if [ -z "$FRONTEND_URL" ]; then
    echo "⚠️  Не удалось получить Frontend URL автоматически"
    echo "   Откройте http://localhost:4040 для просмотра"
    FRONTEND_URL="http://localhost:4040"
fi

if [ -z "$BACKEND_URL" ]; then
    echo "⚠️  Не удалось получить Backend URL автоматически"
    echo "   Откройте http://localhost:4041 для просмотра"
    BACKEND_URL="http://localhost:4041"
fi

echo ""
echo "🌐 ngrok URLs:"
echo "   Frontend:  $FRONTEND_URL"
echo "   Backend:   $BACKEND_URL"
echo ""
echo "📱 Настройка BotFather:"
echo "   1. Отправьте /newapp в @BotFather"
echo "   2. Используйте Frontend URL: $FRONTEND_URL"
echo ""
echo "⚙️  Обновите .env файл:"
echo "   WEBAPP_URL=$FRONTEND_URL"
echo "   API_URL=$BACKEND_URL"
echo ""
echo "🔄 Создайте frontend/.env:"
echo "   VITE_API_URL=$BACKEND_URL"
echo ""
echo "После обновления .env, перезапустите скрипт!"
echo ""

# Если уже настроено, запускаем бота
if grep -q "ngrok" .env 2>/dev/null; then
    echo "5️⃣ Запуск Telegram Bot..."
    python3 bot.py &
    BOT_PID=$!

    echo ""
    echo "✅ Бот запущен!"
    echo ""
fi

echo "⏹️  Для остановки нажмите Ctrl+C"
echo ""

# Ожидание
wait
