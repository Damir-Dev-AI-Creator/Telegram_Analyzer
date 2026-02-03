# 🏗️ АРХИТЕКТУРА СИСТЕМЫ REAL-TIME МОНИТОРИНГА И АНАЛИЗА TELEGRAM

## 📋 СОДЕРЖАНИЕ
1. [Концепция и требования](#концепция-и-требования)
2. [Варианты реализации](#варианты-реализации)
3. [Выбранная архитектура](#выбранная-архитектура)
4. [Технический стек](#технический-стек)
5. [Детальный дизайн компонентов](#детальный-дизайн-компонентов)
6. [База данных и схема](#база-данных-и-схема)
7. [Анонимизация данных](#анонимизация-данных)
8. [План развертывания на Debian VPS](#план-развертывания)
9. [Масштабирование и оптимизация](#масштабирование)
10. [Безопасность](#безопасность)
11. [Мониторинг и observability](#мониторинг)

---

## 📝 КОНЦЕПЦИЯ И ТРЕБОВАНИЯ

### Текущее состояние (v1.0 - Batch Processing)
- ✅ Ручной экспорт сообщений из Telegram в CSV
- ✅ Пакетный анализ CSV файлов через Claude API
- ✅ Генерация DOCX отчетов
- ❌ Нет real-time мониторинга
- ❌ Нет базы данных
- ❌ Нет автоматизации

### Целевое состояние (v2.0 - Real-Time System)

#### Основные требования
1. **Real-time мониторинг** - автоматическое отслеживание новых сообщений
2. **Централизованное хранилище** - PostgreSQL база данных
3. **Анонимизация** - автоматическое удаление/хэширование личных данных
4. **Userbot** - обычный аккаунт Telegram (не бот), добавленный во все чаты
5. **Ассистент-бот** - AI помощник для техподдержки на основе истории
6. **VPS развертывание** - работа 24/7 на Debian сервере
7. **Масштабируемость** - поддержка множества чатов одновременно

#### Дополнительные требования
- Восстановление после сбоев (crash recovery)
- Логирование и алерты
- API для интеграций
- Web dashboard для мониторинга
- Экспорт данных для аналитики

---

## 🔀 ВАРИАНТЫ РЕАЛИЗАЦИИ

### Вариант 1: UserBot + WebSocket + Real-time Processing

**Архитектура:**
```
Telegram Chats → UserBot (Telethon) → WebSocket → Real-time Processor → PostgreSQL
                                                           ↓
                                                    Claude API
                                                           ↓
                                                   AI Assistant Bot
```

**Плюсы:**
- ✅ Настоящий real-time (миллисекунды задержки)
- ✅ Мгновенные ответы ассистента
- ✅ Простая архитектура

**Минусы:**
- ❌ Высокие затраты на Claude API (каждое сообщение)
- ❌ Нет батчинга для оптимизации
- ❌ Сложно обрабатывать пики нагрузки

**Стоимость:** ~$500-1000/месяц при 1000 сообщений/день

---

### Вариант 2: UserBot + Message Queue + Batch Processing

**Архитектура:**
```
Telegram Chats → UserBot → RabbitMQ/Redis → Batch Processor (каждые 5 мин) → PostgreSQL
                                                      ↓
                                               Claude API (batch)
                                                      ↓
                                              AI Assistant Bot
```

**Плюсы:**
- ✅ Оптимизация затрат (батчинг запросов)
- ✅ Устойчивость к пикам (очередь сглаживает)
- ✅ Можно обрабатывать офлайн

**Минусы:**
- ❌ Задержка обработки (5-15 минут)
- ❌ Более сложная архитектура
- ❌ Нужен дополнительный компонент (очередь)

**Стоимость:** ~$100-300/месяц при 1000 сообщений/день

---

### Вариант 3: Гибридный подход (Рекомендуемый)

**Архитектура:**
```
Telegram Chats → UserBot (Telethon)
                     ↓
         ┌───────────┴──────────────┐
         ↓                          ↓
    Fast Lane                  Slow Lane
    (priority)                  (batch)
         ↓                          ↓
    Immediate                 Message Queue
    Processing                  (Redis)
         ↓                          ↓
    Claude API                Batch Processor
         ↓                      (5-15 min)
         ↓                          ↓
         └──────────┬───────────────┘
                    ↓
              PostgreSQL
                    ↓
           AI Assistant Bot
```

**Логика разделения:**
- **Fast Lane**: Срочные сообщения от VIP клиентов, содержащие триггерные слова ("urgent", "bug", "не работает")
- **Slow Lane**: Обычные сообщения, вопросы, общение

**Плюсы:**
- ✅ Баланс между скоростью и стоимостью
- ✅ Гибкость в обработке
- ✅ Оптимизация затрат
- ✅ Приоритизация важных сообщений

**Минусы:**
- ❌ Самая сложная архитектура
- ❌ Требует тонкой настройки правил

**Стоимость:** ~$150-400/месяц при 1000 сообщений/день

---

## ✅ ВЫБРАННАЯ АРХИТЕКТУРА: Вариант 3 (Гибридный)

### Обоснование выбора
1. **Оптимальное соотношение цена/скорость** - срочные сообщения обрабатываются мгновенно, остальные батчами
2. **Масштабируемость** - можно легко добавлять воркеры для обработки
3. **Гибкость** - правила приоритизации настраиваются без изменения кода
4. **Fault tolerance** - очередь обеспечивает надежность

---

## 🛠️ ТЕХНИЧЕСКИЙ СТЕК

### Backend
- **Python 3.12+** - основной язык
- **Telethon** - UserBot для Telegram
- **PostgreSQL 16** - основная БД
- **Redis 7** - очередь сообщений + кэш
- **FastAPI** - REST API + WebSocket
- **SQLAlchemy 2.0** - ORM
- **Alembic** - миграции БД
- **Celery** - распределенная обработка задач

### AI & Analytics
- **Claude API (Anthropic)** - анализ и ответы
- **LangChain** - управление промптами и контекстом
- **Sentence Transformers** - векторизация для семантического поиска
- **pgvector** - векторный поиск в PostgreSQL

### Мониторинг
- **Prometheus** - метрики
- **Grafana** - дашборды
- **Loki** - логи
- **AlertManager** - алерты

### DevOps
- **Docker & Docker Compose** - контейнеризация
- **Nginx** - reverse proxy
- **Systemd** - управление сервисами
- **Let's Encrypt** - SSL сертификаты

---

## 🔧 ДЕТАЛЬНЫЙ ДИЗАЙН КОМПОНЕНТОВ

### 1. UserBot Service (Telegram Listener)

```python
# services/userbot_monitor.py
"""
Real-time мониторинг Telegram чатов через UserBot.
Обрабатывает входящие сообщения и направляет в Fast/Slow Lane.
"""

from telethon import TelegramClient, events
from typing import Optional
import asyncio

class TelegramUserBot:
    """UserBot для мониторинга чатов"""

    def __init__(self, api_id, api_hash, phone, session_path):
        self.client = TelegramClient(session_path, api_id, api_hash)
        self.monitored_chats = []

    async def start(self):
        """Запуск мониторинга"""
        await self.client.start(phone=self.phone)

        # Регистрация обработчиков
        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            await self.process_message(event)

    async def process_message(self, event):
        """Обработка нового сообщения"""
        message_data = {
            'chat_id': event.chat_id,
            'message_id': event.id,
            'user_id': event.sender_id,
            'text': event.text,
            'timestamp': event.date,
            'reply_to': event.reply_to_msg_id
        }

        # Анонимизация
        message_data = anonymize_message(message_data)

        # Определение приоритета
        priority = determine_priority(message_data)

        if priority == 'HIGH':
            await fast_lane_processor.process(message_data)
        else:
            await queue_manager.enqueue(message_data)

    async def monitor_chats(self, chat_ids: list):
        """Добавить чаты для мониторинга"""
        self.monitored_chats = chat_ids
```

### 2. Priority Detector (Классификатор приоритетов)

```python
# services/priority_detector.py
"""
Определение приоритета сообщений на основе:
- Ключевых слов (urgent, bug, error, не работает)
- Отправителя (VIP клиенты)
- Контекста (ответ на важное сообщение)
- Времени (ночные сообщения = высокий приоритет)
"""

from typing import Literal
from datetime import datetime

Priority = Literal['HIGH', 'MEDIUM', 'LOW']

class PriorityDetector:
    """Классификатор приоритетов"""

    URGENT_KEYWORDS = [
        'urgent', 'срочно', 'bug', 'баг', 'error', 'ошибка',
        'не работает', 'сломалось', 'critical', 'критично'
    ]

    VIP_USERS = [...]  # ID VIP пользователей

    def determine_priority(self, message: dict) -> Priority:
        """Определить приоритет сообщения"""
        score = 0

        # Проверка ключевых слов
        text_lower = message['text'].lower()
        if any(keyword in text_lower for keyword in self.URGENT_KEYWORDS):
            score += 50

        # VIP пользователь
        if message['user_id'] in self.VIP_USERS:
            score += 30

        # Ночное время (22:00 - 08:00)
        hour = message['timestamp'].hour
        if hour < 8 or hour >= 22:
            score += 20

        # Ответ на важное сообщение
        if message['reply_to'] and self.is_important_thread(message['reply_to']):
            score += 25

        # Классификация
        if score >= 50:
            return 'HIGH'
        elif score >= 25:
            return 'MEDIUM'
        else:
            return 'LOW'
```

### 3. Message Queue Manager

```python
# services/queue_manager.py
"""
Управление очередью сообщений в Redis.
Батчинг для оптимизации API запросов.
"""

import redis
from typing import List
import json

class MessageQueue:
    """Очередь сообщений"""

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.BATCH_SIZE = 50
        self.BATCH_TIMEOUT = 300  # 5 минут

    async def enqueue(self, message: dict):
        """Добавить сообщение в очередь"""
        queue_key = f"messages:{message['chat_id']}"
        self.redis.rpush(queue_key, json.dumps(message))

    async def dequeue_batch(self, chat_id: int) -> List[dict]:
        """Получить батч сообщений"""
        queue_key = f"messages:{chat_id}"
        messages = []

        for _ in range(self.BATCH_SIZE):
            msg = self.redis.lpop(queue_key)
            if not msg:
                break
            messages.append(json.loads(msg))

        return messages

    async def get_pending_count(self, chat_id: int) -> int:
        """Количество необработанных сообщений"""
        return self.redis.llen(f"messages:{chat_id}")
```

### 4. Batch Processor (Обработчик батчей)

```python
# services/batch_processor.py
"""
Периодическая обработка батчей сообщений.
Celery task, запускается каждые 5-15 минут.
"""

from celery import Celery
from typing import List

app = Celery('telegram_analyzer')

@app.task
async def process_message_batch(chat_id: int):
    """Обработать батч сообщений для чата"""

    # Получить батч из очереди
    messages = await queue_manager.dequeue_batch(chat_id)

    if not messages:
        return

    # Анализ батча через Claude API
    analysis = await analyze_batch_with_claude(messages)

    # Сохранение в БД
    await db.save_messages(messages)
    await db.save_analysis(chat_id, analysis)

    # Проверка на необходимость ответа ассистента
    if analysis.requires_response:
        await assistant_bot.send_response(
            chat_id,
            analysis.suggested_response
        )

async def analyze_batch_with_claude(messages: List[dict]) -> dict:
    """Анализ батча сообщений через Claude"""

    # Формирование контекста
    context = format_messages_for_claude(messages)

    prompt = f"""
    Проанализируй следующий батч сообщений из техподдержки:

    {context}

    Определи:
    1. Основные темы и проблемы
    2. Требуется ли срочный ответ
    3. Предложи ответ если нужен
    4. Sentiment analysis
    """

    response = await claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    return parse_claude_response(response)
```

### 5. Database Models

```python
# models/database.py
"""
Модели базы данных PostgreSQL.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

Base = declarative_base()

class Chat(Base):
    """Чаты Telegram"""
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, index=True)
    title = Column(String(255))
    chat_type = Column(String(50))  # group, supergroup, channel
    is_monitored = Column(Boolean, default=True)
    created_at = Column(DateTime)

class Message(Base):
    """Сообщения (анонимизированные)"""
    __tablename__ = 'messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(Integer, ForeignKey('chats.id'))
    telegram_message_id = Column(Integer)

    # Анонимизированные данные
    user_hash = Column(String(64))  # SHA256 хэш user_id
    text_content = Column(Text)  # Очищен от личных данных

    timestamp = Column(DateTime, index=True)
    is_support = Column(Boolean, default=False)  # Сообщение от тех поддержки

    # Метаданные
    priority = Column(String(20))  # HIGH, MEDIUM, LOW
    processed = Column(Boolean, default=False)

class Analysis(Base):
    """Результаты анализа"""
    __tablename__ = 'analysis'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(Integer, ForeignKey('chats.id'))
    batch_id = Column(String(50))  # ID батча сообщений

    # Результаты
    summary = Column(Text)
    topics = Column(JSONB)  # JSON массив тем
    sentiment = Column(String(20))  # positive, negative, neutral
    requires_response = Column(Boolean)
    suggested_response = Column(Text, nullable=True)

    analyzed_at = Column(DateTime)
    claude_model = Column(String(50))

class AssistantResponse(Base):
    """Ответы AI ассистента"""
    __tablename__ = 'assistant_responses'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(Integer, ForeignKey('chats.id'))
    analysis_id = Column(UUID(as_uuid=True), ForeignKey('analysis.id'))

    response_text = Column(Text)
    sent_at = Column(DateTime)
    was_helpful = Column(Boolean, nullable=True)  # Feedback
```

---

## 🔒 АНОНИМИЗАЦИЯ ДАННЫХ

### Стратегия анонимизации

```python
# services/anonymizer.py
"""
Автоматическая анонимизация личных данных.
"""

import hashlib
import re
from typing import Dict

class DataAnonymizer:
    """Анонимизатор персональных данных"""

    # Паттерны для обнаружения
    PHONE_PATTERN = r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    NAME_PATTERN = r'\b[A-ZА-Я][a-zа-я]+ [A-ZА-Я][a-zа-я]+\b'

    def anonymize_message(self, message: Dict) -> Dict:
        """Анонимизировать сообщение"""

        # Хэширование user_id
        message['user_hash'] = self.hash_user_id(message['user_id'])
        del message['user_id']  # Удаляем оригинальный ID

        # Очистка текста
        text = message['text']
        text = self.remove_phones(text)
        text = self.remove_emails(text)
        text = self.mask_names(text)
        message['text'] = text

        return message

    def hash_user_id(self, user_id: int) -> str:
        """Хэширование user_id (необратимо)"""
        return hashlib.sha256(str(user_id).encode()).hexdigest()

    def remove_phones(self, text: str) -> str:
        """Удаление номеров телефонов"""
        return re.sub(self.PHONE_PATTERN, '[PHONE]', text)

    def remove_emails(self, text: str) -> str:
        """Удаление email адресов"""
        return re.sub(self.EMAIL_PATTERN, '[EMAIL]', text)

    def mask_names(self, text: str) -> str:
        """Маскирование имен"""
        return re.sub(self.NAME_PATTERN, '[NAME]', text)
```

### Уровни анонимизации

| Уровень | Данные | Обработка |
|---------|--------|-----------|
| **1. Полное удаление** | User ID, Phone, Email | Удаляются навсегда |
| **2. Хэширование** | User ID → Hash | SHA256, необратимо |
| **3. Маскирование** | Имена → [NAME] | Заменяются токеном |
| **4. Сохранение** | Текст сообщения (без PII) | Хранится в БД |

---

## 🚀 ПЛАН РАЗВЕРТЫВАНИЯ НA DEBIAN VPS

### Спецификация сервера

**Минимальные требования:**
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 50GB SSD
- **Network**: 100 Mbps
- **OS**: Debian 12 (Bookworm)

**Рекомендуемые (для production):**
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 100GB NVMe SSD
- **Network**: 1 Gbps
- **OS**: Debian 12 (Bookworm)

### Пошаговое развертывание

```bash
# ============================================================================
# ШАГ 1: Подготовка сервера
# ============================================================================

# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y \
    python3.12 python3.12-venv python3-pip \
    postgresql-16 postgresql-contrib \
    redis-server \
    nginx \
    git curl wget \
    supervisor \
    certbot python3-certbot-nginx

# ============================================================================
# ШАГ 2: Настройка PostgreSQL
# ============================================================================

# Создание базы данных
sudo -u postgres psql <<EOF
CREATE DATABASE telegram_analyzer;
CREATE USER analyzer_user WITH PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE telegram_analyzer TO analyzer_user;

-- Установка pgvector для векторного поиска
CREATE EXTENSION vector;
EOF

# Настройка PostgreSQL для оптимизации
sudo nano /etc/postgresql/16/main/postgresql.conf
# Изменить:
# shared_buffers = 2GB
# effective_cache_size = 6GB
# maintenance_work_mem = 512MB
# checkpoint_completion_target = 0.9

sudo systemctl restart postgresql

# ============================================================================
# ШАГ 3: Настройка Redis
# ============================================================================

# Конфигурация Redis
sudo nano /etc/redis/redis.conf
# Изменить:
# maxmemory 1gb
# maxmemory-policy allkeys-lru

sudo systemctl restart redis-server

# ============================================================================
# ШАГ 4: Развертывание приложения
# ============================================================================

# Клонирование репозитория
cd /opt
sudo git clone https://github.com/yourrepo/telegram_analyzer.git
cd telegram_analyzer

# Создание виртуального окружения
python3.12 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
pip install -r requirements-prod.txt  # Production зависимости

# Создание .env файла
cat > .env <<EOF
# Telegram API
API_ID=your_api_id
API_HASH=your_api_hash
PHONE=+1234567890

# Claude API
CLAUDE_API_KEY=sk-ant-api03-...
CLAUDE_MODEL=claude-sonnet-4-20250514

# Database
DATABASE_URL=postgresql://analyzer_user:strong_password_here@localhost/telegram_analyzer

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=generate_random_secret_here
JWT_SECRET=generate_jwt_secret_here

# Monitoring
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
EOF

# Запуск миграций БД
alembic upgrade head

# ============================================================================
# ШАГ 5: Настройка Systemd сервисов
# ============================================================================

# UserBot Service
sudo cat > /etc/systemd/system/telegram-userbot.service <<EOF
[Unit]
Description=Telegram UserBot Monitor
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/telegram_analyzer
Environment="PATH=/opt/telegram_analyzer/venv/bin"
ExecStart=/opt/telegram_analyzer/venv/bin/python -m services.userbot_monitor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Batch Processor (Celery Worker)
sudo cat > /etc/systemd/system/telegram-worker.service <<EOF
[Unit]
Description=Telegram Message Batch Processor
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/telegram_analyzer
Environment="PATH=/opt/telegram_analyzer/venv/bin"
ExecStart=/opt/telegram_analyzer/venv/bin/celery -A services.batch_processor worker --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Celery Beat (Scheduler)
sudo cat > /etc/systemd/system/telegram-beat.service <<EOF
[Unit]
Description=Telegram Batch Scheduler
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/telegram_analyzer
Environment="PATH=/opt/telegram_analyzer/venv/bin"
ExecStart=/opt/telegram_analyzer/venv/bin/celery -A services.batch_processor beat --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# FastAPI Server
sudo cat > /etc/systemd/system/telegram-api.service <<EOF
[Unit]
Description=Telegram Analyzer API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/telegram_analyzer
Environment="PATH=/opt/telegram_analyzer/venv/bin"
ExecStart=/opt/telegram_analyzer/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Включение и запуск сервисов
sudo systemctl daemon-reload
sudo systemctl enable telegram-userbot telegram-worker telegram-beat telegram-api
sudo systemctl start telegram-userbot telegram-worker telegram-beat telegram-api

# ============================================================================
# ШАГ 6: Настройка Nginx
# ============================================================================

sudo cat > /etc/nginx/sites-available/telegram-analyzer <<'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/telegram-analyzer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Получение SSL сертификата
sudo certbot --nginx -d your-domain.com

# ============================================================================
# ШАГ 7: Настройка мониторинга
# ============================================================================

# Установка Prometheus
cd /tmp
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
sudo mv prometheus-2.45.0.linux-amd64 /opt/prometheus

# Конфигурация Prometheus
sudo cat > /opt/prometheus/prometheus.yml <<EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'telegram-analyzer'
    static_configs:
      - targets: ['localhost:8000']
EOF

# Systemd service для Prometheus
sudo cat > /etc/systemd/system/prometheus.service <<EOF
[Unit]
Description=Prometheus
After=network.target

[Service]
Type=simple
ExecStart=/opt/prometheus/prometheus --config.file=/opt/prometheus/prometheus.yml
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable prometheus
sudo systemctl start prometheus

# ============================================================================
# ШАГ 8: Логирование
# ============================================================================

# Настройка ротации логов
sudo cat > /etc/logrotate.d/telegram-analyzer <<EOF
/opt/telegram_analyzer/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload telegram-userbot telegram-worker telegram-api
    endscript
}
EOF

# ============================================================================
# ШАГ 9: Backup setup
# ============================================================================

# Скрипт бэкапа БД
sudo cat > /opt/telegram_analyzer/scripts/backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/telegram_analyzer"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
pg_dump -U analyzer_user telegram_analyzer | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup Redis
redis-cli --rdb $BACKUP_DIR/redis_$DATE.rdb

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -type f -mtime +30 -delete
EOF

chmod +x /opt/telegram_analyzer/scripts/backup.sh

# Добавление в cron (каждый день в 3:00 AM)
echo "0 3 * * * /opt/telegram_analyzer/scripts/backup.sh" | sudo crontab -

# ============================================================================
# ШАГ 10: Проверка развертывания
# ============================================================================

# Проверка статуса сервисов
sudo systemctl status telegram-userbot telegram-worker telegram-beat telegram-api

# Проверка логов
sudo journalctl -u telegram-userbot -f

# Проверка подключения к БД
sudo -u postgres psql -d telegram_analyzer -c "SELECT version();"

# Проверка Redis
redis-cli ping

# Проверка API
curl http://localhost:8000/health

echo "Развертывание завершено!"
```

---

## 📈 МАСШТАБИРОВАНИЕ И ОПТИМИЗАЦИЯ

### Horizontal Scaling

```yaml
# docker-compose.yml для кластера
version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: telegram_analyzer
      POSTGRES_USER: analyzer_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    deploy:
      replicas: 1

  redis:
    image: redis:7-alpine
    deploy:
      replicas: 1

  userbot:
    build: .
    command: python -m services.userbot_monitor
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 1  # Только один UserBot instance

  worker:
    build: .
    command: celery -A services.batch_processor worker
    depends_on:
      - redis
      - postgres
    deploy:
      replicas: 3  # Несколько воркеров для параллельной обработки

  api:
    build: .
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 2  # Load balancing
```

### Оптимизации производительности

1. **Database Indexing**
```sql
-- Индексы для быстрого поиска
CREATE INDEX idx_messages_chat_timestamp ON messages(chat_id, timestamp DESC);
CREATE INDEX idx_messages_user_hash ON messages(user_hash);
CREATE INDEX idx_messages_priority ON messages(priority) WHERE processed = false;
CREATE INDEX idx_analysis_chat ON analysis(chat_id, analyzed_at DESC);
```

2. **Redis Caching**
```python
# Кэширование частых запросов
@cached(ttl=300)  # 5 минут
async def get_chat_statistics(chat_id: int):
    return await db.query(...)
```

3. **Connection Pooling**
```python
# Пул соединений для PostgreSQL
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

---

## 🔐 БЕЗОПАСНОСТЬ

### Чек-лист безопасности

- [ ] Firewall настроен (UFW)
- [ ] SSH доступ только по ключам
- [ ] Fail2ban установлен
- [ ] PostgreSQL не доступна извне
- [ ] Redis защищен паролем
- [ ] .env файлы в .gitignore
- [ ] SSL сертификат установлен
- [ ] Rate limiting на API
- [ ] CORS настроен правильно
- [ ] Логирование включено
- [ ] Бэкапы автоматизированы

### Настройка Firewall

```bash
# Настройка UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Fail2ban для защиты от брутфорса
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

---

## 📊 МОНИТОРИНГ И OBSERVABILITY

### Метрики для отслеживания

1. **System Metrics**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network traffic

2. **Application Metrics**
   - Messages per second
   - Processing latency
   - Queue depth
   - Claude API calls per minute
   - Error rate

3. **Business Metrics**
   - Active chats
   - Response time (Fast Lane)
   - Batch processing time
   - Cost per message

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Telegram Analyzer Monitoring",
    "panels": [
      {
        "title": "Messages Rate",
        "targets": [
          {
            "expr": "rate(messages_received_total[5m])"
          }
        ]
      },
      {
        "title": "Queue Depth",
        "targets": [
          {
            "expr": "redis_queue_length"
          }
        ]
      },
      {
        "title": "API Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))"
          }
        ]
      }
    ]
  }
}
```

---

## 💰 ОЦЕНКА СТОИМОСТИ

### Месячные затраты (при 1000 сообщений/день)

| Компонент | Стоимость |
|-----------|-----------|
| **VPS (4 cores, 8GB RAM)** | $40/мес |
| **Claude API (30k tokens/day)** | $150/мес |
| **Backup storage (50GB)** | $5/мес |
| **Domain + SSL** | $15/год |
| **Мониторинг (Grafana Cloud)** | $0 (free tier) |
| **ИТОГО** | ~$195/мес |

### Сравнение с текущим решением

| Метрика | Текущее (v1.0) | Новое (v2.0) |
|---------|----------------|--------------|
| Задержка обработки | 24+ часов | 5-15 минут |
| Автоматизация | Ручная | Полная |
| Стоимость | $0 (ручной труд) | $195/мес |
| Масштабируемость | Низкая | Высокая |

---

## 🎯 ПЛАН РЕАЛИЗАЦИИ (ROADMAP)

### Фаза 1: MVP (2-3 недели)
- ✅ Исправление текущих багов
- [ ] UserBot + базовый мониторинг
- [ ] PostgreSQL схема
- [ ] Анонимизация данных
- [ ] Простой батч процессор

### Фаза 2: Real-time + Приоритизация (2 недели)
- [ ] Fast Lane / Slow Lane
- [ ] Priority Detector
- [ ] Redis очередь
- [ ] Celery воркеры

### Фаза 3: AI Assistant Bot (2 недели)
- [ ] LangChain интеграция
- [ ] Контекстные ответы
- [ ] Векторный поиск
- [ ] Feedback loop

### Фаза 4: Production Hardening (1 неделя)
- [ ] Мониторинг (Prometheus + Grafana)
- [ ] Алерты
- [ ] Бэкапы
- [ ] Документация

### Фаза 5: Advanced Features (ongoing)
- [ ] Web dashboard
- [ ] Analytics
- [ ] A/B testing ответов
- [ ] Multi-language support

---

## 📚 ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ

### Документация
- Telethon: https://docs.telethon.dev/
- FastAPI: https://fastapi.tiangolo.com/
- Celery: https://docs.celeryproject.org/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Claude API: https://docs.anthropic.com/

### Best Practices
- 12-Factor App: https://12factor.net/
- PostgreSQL Tuning: https://pgtune.leopard.in.ua/
- Redis Best Practices: https://redis.io/docs/management/optimization/

---

## 🤝 ЗАКЛЮЧЕНИЕ

Данная архитектура представляет собой **production-ready** решение для real-time мониторинга и анализа Telegram чатов с использованием AI.

**Ключевые преимущества:**
1. Масштабируемость - легко добавлять новые чаты и воркеры
2. Оптимизация затрат - гибридный подход Fast/Slow Lane
3. Надежность - fault tolerance через очереди и retry механизмы
4. Безопасность - анонимизация данных и best practices
5. Observability - полный мониторинг всех компонентов

**Следующие шаги:**
1. Согласовать архитектуру с командой
2. Начать с MVP (Фаза 1)
3. Итеративно добавлять функциональность
4. Собирать метрики и оптимизировать

---

*Документ создан: 2026-02-03*
*Версия: 2.0 DRAFT*
*Автор: Claude AI + Development Team*
