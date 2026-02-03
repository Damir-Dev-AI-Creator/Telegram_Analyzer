# Dockerfile для Railway, Render и других PaaS платформ
FROM python:3.11-slim

# Установить системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копировать requirements для сервера (без GUI)
COPY requirements-server.txt .

# Обновить pip и установить базовые инструменты
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Установить Python зависимости (только серверные, без GUI)
RUN pip install --no-cache-dir -r requirements-server.txt

# Копировать весь проект
COPY . .

# Создать необходимые директории
RUN mkdir -p data logs data/users

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Порт (хотя бот не использует HTTP, Railway требует)
EXPOSE 8080

# Запуск бота
CMD ["python", "main.py", "--bot"]
