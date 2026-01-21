@echo off
REM Скрипт для запуска всех компонентов в режиме разработки (Windows)

echo 🚀 Запуск Telegram Bot Mini App в режиме разработки...
echo.

REM Проверка наличия .env файла
if not exist .env (
    echo ❌ Файл .env не найден!
    echo 📝 Создайте .env файл на основе .env.example
    echo    copy .env.example .env
    pause
    exit /b 1
)

echo ✅ Файл .env найден
echo.

REM Создание директорий
if not exist data mkdir data
if not exist C:\temp\telegram_bot_uploads mkdir C:\temp\telegram_bot_uploads
if not exist C:\temp\telegram_bot_sessions mkdir C:\temp\telegram_bot_sessions

echo 📂 Директории созданы
echo.

echo 🔧 Запуск компонентов...
echo.

REM Запуск Backend API
echo 1️⃣ Запуск Backend API на порту 8000...
start "Backend API" cmd /k python -m uvicorn backend.api:app --reload --port 8000
timeout /t 3 /nobreak > nul

REM Запуск Frontend
echo 2️⃣ Запуск Frontend на порту 3000...
cd frontend
start "Frontend" cmd /k npm run dev
cd ..
timeout /t 4 /nobreak > nul

REM Запуск Telegram Bot
echo 3️⃣ Запуск Telegram Bot...
start "Telegram Bot" cmd /k python bot.py
timeout /t 2 /nobreak > nul

echo.
echo ✅ Все компоненты запущены в отдельных окнах!
echo.
echo 📋 Информация:
echo    Backend API:   http://localhost:8000
echo    Frontend:      http://localhost:3000
echo    API Docs:      http://localhost:8000/docs
echo.
echo 🤖 Найдите вашего бота в Telegram и отправьте /start
echo.
echo ⏹️  Закройте окна для остановки компонентов
echo.

pause
