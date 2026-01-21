"""
FastAPI backend для Telegram Mini App
Обрабатывает все API запросы от React frontend
"""

import os
import sys
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import hashlib
import hmac
import json
from urllib.parse import parse_qsl

# Добавляем родительскую директорию в путь для импорта services
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from services.telegram import TelegramExporter
from services.analyzer import ClaudeAnalyzer

# Импортируем модели базы данных
from telegram_bot.database.models import Database, User, UserSettings, ExportTask

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание приложения
app = FastAPI(
    title="Ysell Analyzer API",
    description="Backend API для Telegram Mini App",
    version="0.3.0"
)

# CORS middleware для разрешения запросов от frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация базы данных
db = Database()

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# === Pydantic модели для API === #

class InitData(BaseModel):
    """Модель для данных инициализации Telegram WebApp"""
    init_data: str = Field(..., description="Строка initData от Telegram WebApp")


class UserSettingsModel(BaseModel):
    """Модель настроек пользователя"""
    telegram_api_id: Optional[str] = None
    telegram_api_hash: Optional[str] = None
    telegram_phone: Optional[str] = None
    claude_api_key: Optional[str] = None


class ExportRequest(BaseModel):
    """Модель запроса на экспорт"""
    chat_identifier: str = Field(..., description="Username или ID чата")
    date_from: Optional[str] = Field(None, description="Дата начала (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="Дата окончания (YYYY-MM-DD)")


class AnalysisRequest(BaseModel):
    """Модель запроса на анализ"""
    csv_file_path: str = Field(..., description="Путь к CSV файлу")
    prompt: Optional[str] = Field(None, description="Пользовательский промпт для анализа")


# === Функции аутентификации === #

def validate_telegram_webapp_data(init_data: str, bot_token: str) -> Optional[Dict[str, Any]]:
    """
    Валидация данных от Telegram WebApp

    Args:
        init_data: Строка initData от Telegram
        bot_token: Токен бота

    Returns:
        Распарсенные данные пользователя или None если невалидно
    """
    try:
        # Парсинг данных
        parsed_data = dict(parse_qsl(init_data))

        # Извлекаем hash
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            return None

        # Создаем data_check_string
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )

        # Вычисляем secret_key
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # Вычисляем hash
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        # Проверяем hash
        if calculated_hash != received_hash:
            logger.warning("Invalid hash in Telegram WebApp data")
            return None

        # Проверяем auth_date (не старше 1 часа)
        auth_date = int(parsed_data.get('auth_date', 0))
        current_time = datetime.now().timestamp()
        if current_time - auth_date > 3600:
            logger.warning("Telegram WebApp data is too old")
            return None

        # Парсим user данные
        user_data = json.loads(parsed_data.get('user', '{}'))

        return user_data

    except Exception as e:
        logger.error(f"Error validating Telegram WebApp data: {e}")
        return None


async def get_current_user(init_data: InitData) -> User:
    """
    Dependency для получения текущего пользователя

    Args:
        init_data: Данные инициализации от Telegram

    Returns:
        Объект пользователя

    Raises:
        HTTPException: Если аутентификация неудачна
    """
    user_data = validate_telegram_webapp_data(init_data.init_data, BOT_TOKEN)

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid authentication data")

    # Получаем или создаем пользователя в БД
    user = await db.get_or_create_user(
        telegram_id=user_data['id'],
        username=user_data.get('username'),
        first_name=user_data.get('first_name'),
        last_name=user_data.get('last_name')
    )

    return user


# === API Endpoints === #

@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "app": "Ysell Analyzer API",
        "version": "0.3.0",
        "status": "running"
    }


@app.post("/auth/validate")
async def validate_auth(init_data: InitData):
    """
    Валидация аутентификации пользователя

    Returns:
        Информация о пользователе
    """
    user = await get_current_user(init_data)

    return {
        "success": True,
        "user": {
            "id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
    }


@app.post("/settings/get")
async def get_settings(init_data: InitData):
    """
    Получение настроек пользователя

    Returns:
        Настройки пользователя (API ключи зашифрованы)
    """
    user = await get_current_user(init_data)
    settings = await db.get_user_settings(user.id)

    return {
        "success": True,
        "settings": {
            "telegram_api_id": settings.telegram_api_id if settings else None,
            "telegram_api_hash": "••••••" if settings and settings.telegram_api_hash else None,
            "telegram_phone": settings.telegram_phone if settings else None,
            "claude_api_key": "••••••" if settings and settings.claude_api_key else None,
            "has_telegram_config": bool(settings and settings.telegram_api_id),
            "has_claude_config": bool(settings and settings.claude_api_key)
        }
    }


@app.post("/settings/update")
async def update_settings(init_data: InitData, settings: UserSettingsModel):
    """
    Обновление настроек пользователя

    Args:
        settings: Новые настройки

    Returns:
        Результат обновления
    """
    user = await get_current_user(init_data)

    # Обновляем настройки в БД
    await db.update_user_settings(
        user_id=user.id,
        telegram_api_id=settings.telegram_api_id,
        telegram_api_hash=settings.telegram_api_hash,
        telegram_phone=settings.telegram_phone,
        claude_api_key=settings.claude_api_key
    )

    return {
        "success": True,
        "message": "Настройки успешно обновлены"
    }


@app.post("/export/start")
async def start_export(
    init_data: InitData,
    export_request: ExportRequest,
    background_tasks: BackgroundTasks
):
    """
    Запуск экспорта Telegram чата

    Args:
        export_request: Параметры экспорта

    Returns:
        ID задачи экспорта
    """
    user = await get_current_user(init_data)
    settings = await db.get_user_settings(user.id)

    # Проверка настроек
    if not settings or not settings.telegram_api_id:
        raise HTTPException(
            status_code=400,
            detail="Настройте Telegram API ключи в разделе 'Настройки'"
        )

    # Создаем задачу экспорта
    task = await db.create_export_task(
        user_id=user.id,
        chat_identifier=export_request.chat_identifier,
        date_from=export_request.date_from,
        date_to=export_request.date_to
    )

    # Запускаем экспорт в фоне
    background_tasks.add_task(
        run_export_task,
        task_id=task.id,
        user_id=user.id,
        settings=settings,
        export_request=export_request
    )

    return {
        "success": True,
        "task_id": task.id,
        "message": "Экспорт запущен"
    }


@app.get("/export/status/{task_id}")
async def get_export_status(task_id: int, init_data: InitData):
    """
    Получение статуса задачи экспорта

    Args:
        task_id: ID задачи

    Returns:
        Статус задачи
    """
    user = await get_current_user(init_data)
    task = await db.get_export_task(task_id)

    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    return {
        "success": True,
        "task": {
            "id": task.id,
            "status": task.status,
            "progress": task.progress,
            "error": task.error,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
    }


@app.get("/export/download/{task_id}")
async def download_export(task_id: int, init_data: InitData):
    """
    Скачивание результата экспорта

    Args:
        task_id: ID задачи

    Returns:
        CSV файл
    """
    user = await get_current_user(init_data)
    task = await db.get_export_task(task_id)

    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Экспорт еще не завершен")

    if not task.output_file or not os.path.exists(task.output_file):
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(
        path=task.output_file,
        filename=os.path.basename(task.output_file),
        media_type='text/csv'
    )


@app.post("/analyze/start")
async def start_analysis(
    init_data: InitData,
    csv_file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Запуск анализа CSV файла с Claude AI

    Args:
        csv_file: Загруженный CSV файл

    Returns:
        Результат анализа
    """
    user = await get_current_user(init_data)
    settings = await db.get_user_settings(user.id)

    # Проверка настроек
    if not settings or not settings.claude_api_key:
        raise HTTPException(
            status_code=400,
            detail="Настройте Claude API ключ в разделе 'Настройки'"
        )

    # Сохраняем загруженный файл
    upload_dir = f"/tmp/telegram_bot_uploads/{user.id}"
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, csv_file.filename)
    with open(file_path, "wb") as f:
        content = await csv_file.read()
        f.write(content)

    # Запускаем анализ
    try:
        analyzer = ClaudeAnalyzer(api_key=settings.claude_api_key)
        result_path = await run_analysis(analyzer, file_path)

        return {
            "success": True,
            "message": "Анализ завершен",
            "output_file": result_path
        }
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/download/{filename}")
async def download_analysis(filename: str, init_data: InitData):
    """
    Скачивание результата анализа (DOCX)

    Args:
        filename: Имя файла

    Returns:
        DOCX файл
    """
    user = await get_current_user(init_data)

    # Проверяем путь к файлу
    file_path = f"/tmp/telegram_bot_uploads/{user.id}/{filename}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


# === Вспомогательные функции === #

async def run_export_task(
    task_id: int,
    user_id: int,
    settings: UserSettings,
    export_request: ExportRequest
):
    """
    Выполнение задачи экспорта в фоновом режиме

    Args:
        task_id: ID задачи
        user_id: ID пользователя
        settings: Настройки пользователя
        export_request: Параметры экспорта
    """
    try:
        # Обновляем статус
        await db.update_task_status(task_id, "in_progress", 10)

        # Создаем директорию для сессий пользователя
        session_dir = f"/tmp/telegram_bot_sessions/{user_id}"
        os.makedirs(session_dir, exist_ok=True)

        # Создаем экспортер
        exporter = TelegramExporter(
            api_id=int(settings.telegram_api_id),
            api_hash=settings.telegram_api_hash,
            phone=settings.telegram_phone,
            session_file=os.path.join(session_dir, "session")
        )

        # Парсим даты
        date_from = datetime.strptime(export_request.date_from, "%Y-%m-%d") if export_request.date_from else None
        date_to = datetime.strptime(export_request.date_to, "%Y-%m-%d") if export_request.date_to else None

        # Запускаем экспорт
        await db.update_task_status(task_id, "in_progress", 50)

        output_file = await exporter.export_chat(
            chat_identifier=export_request.chat_identifier,
            output_file=f"/tmp/telegram_bot_uploads/{user_id}/export_{task_id}.csv",
            date_from=date_from,
            date_to=date_to
        )

        # Обновляем статус на завершено
        await db.update_task_status(task_id, "completed", 100)
        await db.update_task_output(task_id, output_file)

    except Exception as e:
        logger.error(f"Export task {task_id} failed: {e}")
        await db.update_task_status(task_id, "failed", 0, str(e))


async def run_analysis(analyzer: ClaudeAnalyzer, csv_file_path: str) -> str:
    """
    Выполнение анализа CSV файла

    Args:
        analyzer: Инстанс ClaudeAnalyzer
        csv_file_path: Путь к CSV файлу

    Returns:
        Путь к сгенерированному DOCX файлу
    """
    # Запускаем анализ
    output_file = csv_file_path.replace('.csv', '_analysis.docx')

    # Вызываем метод анализа (предполагается, что он асинхронный)
    result = await analyzer.analyze_and_generate_report(
        csv_file=csv_file_path,
        output_file=output_file
    )

    return output_file


# === Lifecycle events === #

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Starting Ysell Analyzer API...")
    await db.init_db()
    logger.info("API ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    logger.info("Shutting down Ysell Analyzer API...")
    await db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
