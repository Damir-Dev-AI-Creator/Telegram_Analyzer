# Telegram Bot с Mini App для Ysell Analyzer

Современная реализация Ysell Analyzer в виде Telegram бота с полноценным веб-интерфейсом (Mini App).

## 🎯 Возможности

- ✅ **Telegram Mini App** - полноценный UI интерфейс прямо в Telegram
- ✅ **Мультипользовательский** - каждый пользователь работает со своими API ключами
- ✅ **Безопасность** - все API ключи шифруются и хранятся отдельно для каждого пользователя
- ✅ **Экспорт чатов** - выгрузка полной истории Telegram переписок
- ✅ **AI Анализ** - анализ с помощью Claude AI и генерация DOCX отчетов
- ✅ **Асинхронная обработка** - задачи выполняются в фоне

## 📋 Архитектура

```
telegram_bot/
├── bot.py                 # Telegram Bot (python-telegram-bot)
├── backend/
│   └── api.py            # FastAPI REST API для Mini App
├── database/
│   └── models.py         # SQLAlchemy модели + шифрование
├── frontend/             # React приложение (Mini App)
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ExportTab.jsx
│   │   │   ├── AnalysisTab.jsx
│   │   │   └── SettingsTab.jsx
│   │   └── services/
│   │       └── api.js    # Axios API клиент
│   ├── package.json
│   └── vite.config.js
└── requirements.txt
```

## 🚀 Быстрый старт

### 1. Создание Telegram бота

1. Найдите [@BotFather](https://t.me/Botfather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните полученный токен

### 2. Установка зависимостей

#### Backend (Python)

```bash
cd telegram_bot
pip install -r requirements.txt
```

#### Frontend (React)

```bash
cd frontend
npm install
```

### 3. Конфигурация

Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Заполните переменные:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
WEBAPP_URL=https://your-mini-app-url.com
API_URL=https://your-api-url.com
```

### 4. Запуск

#### Development режим

**Terminal 1 - Backend API:**
```bash
cd telegram_bot
python -m uvicorn backend.api:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd telegram_bot/frontend
npm run dev
```

**Terminal 3 - Telegram Bot:**
```bash
cd telegram_bot
python bot.py
```

#### Production режим

См. раздел "Развертывание в продакшен" ниже.

## 📱 Использование

### Для пользователей

1. Найдите вашего бота в Telegram
2. Отправьте команду `/start`
3. Нажмите "🚀 Открыть Ysell Analyzer"
4. Перейдите в "⚙️ Настройки" и введите API ключи:
   - **Telegram API**: получите на https://my.telegram.org/apps
   - **Claude API**: получите на https://console.anthropic.com

5. Используйте приложение:
   - **📱 Экспорт**: экспорт истории чата в CSV
   - **🤖 Анализ**: анализ CSV с Claude AI

### Команды бота

- `/start` - Главное меню
- `/app` - Открыть приложение
- `/help` - Справка
- `/about` - О приложении

## 🔒 Безопасность

### Шифрование данных

Все API ключи пользователей автоматически шифруются с помощью Fernet (симметричное шифрование):

- Генерируется уникальный ключ шифрования при первом запуске
- Ключ хранится в `data/.encryption_key` с правами доступа 600
- Все API ключи в БД хранятся в зашифрованном виде
- Расшифровка происходит только при использовании

### Аутентификация

Используется встроенная аутентификация Telegram WebApp:

1. Telegram передает `initData` при открытии Mini App
2. Backend валидирует `initData` используя HMAC-SHA256 с секретным ключом бота
3. Проверяется подпись и время создания (не старше 1 часа)
4. Пользователь идентифицируется по Telegram ID

### База данных

- SQLite для хранения пользовательских настроек и задач
- Автоматическое создание таблиц при первом запуске
- Изоляция данных между пользователями

## 🌐 Развертывание в продакшен

### Вариант 1: VPS (Рекомендуется)

#### Требования
- Ubuntu 20.04+ / Debian 11+
- Python 3.9+
- Node.js 18+
- Nginx
- Certbot (для SSL)

#### Шаги

**1. Установка зависимостей:**

```bash
# Python
sudo apt update
sudo apt install python3-pip python3-venv nginx certbot python3-certbot-nginx

# Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs
```

**2. Клонирование репозитория:**

```bash
git clone https://github.com/your-repo/Telegram_Analyzer.git
cd Telegram_Analyzer/telegram_bot
```

**3. Настройка Backend:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Создайте .env файл
cp .env.example .env
nano .env  # Заполните переменные
```

**4. Настройка Frontend:**

```bash
cd frontend
npm install
npm run build  # Создаст dist/ папку
```

**5. Конфигурация Nginx:**

```nginx
# /etc/nginx/sites-available/ysell-analyzer
server {
    listen 80;
    server_name api.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

server {
    listen 80;
    server_name app.your-domain.com;

    root /path/to/telegram_bot/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ysell-analyzer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**6. SSL сертификаты:**

```bash
sudo certbot --nginx -d api.your-domain.com -d app.your-domain.com
```

**7. Systemd сервисы:**

**Backend API:**
```ini
# /etc/systemd/system/ysell-api.service
[Unit]
Description=Ysell Analyzer API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/telegram_bot
Environment="PATH=/path/to/telegram_bot/venv/bin"
ExecStart=/path/to/telegram_bot/venv/bin/uvicorn backend.api:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Telegram Bot:**
```ini
# /etc/systemd/system/ysell-bot.service
[Unit]
Description=Ysell Analyzer Telegram Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/telegram_bot
Environment="PATH=/path/to/telegram_bot/venv/bin"
ExecStart=/path/to/telegram_bot/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ysell-api ysell-bot
sudo systemctl start ysell-api ysell-bot
```

**8. Настройка Mini App в BotFather:**

1. Отправьте `/newapp` в [@BotFather](https://t.me/BotFather)
2. Выберите вашего бота
3. Введите название приложения
4. Загрузите иконку (512x512 PNG)
5. Введите URL: `https://app.your-domain.com`
6. Сохраните

### Вариант 2: Docker (Альтернатива)

Создайте `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - WEBAPP_URL=${WEBAPP_URL}
    volumes:
      - ./data:/app/data

  bot:
    build:
      context: .
      dockerfile: Dockerfile.bot
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - WEBAPP_URL=${WEBAPP_URL}
    depends_on:
      - api

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
```

Запуск:
```bash
docker-compose up -d
```

## 📊 Мониторинг

### Логи

```bash
# Backend API
sudo journalctl -u ysell-api -f

# Telegram Bot
sudo journalctl -u ysell-bot -f

# Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Метрики

Рекомендуется использовать:
- **Prometheus** + **Grafana** для метрик
- **Sentry** для отслеживания ошибок
- **Uptime Kuma** для мониторинга доступности

## 🔧 Troubleshooting

### Проблема: Bot не отвечает

**Решение:**
1. Проверьте логи: `sudo journalctl -u ysell-bot -n 50`
2. Убедитесь что токен правильный в `.env`
3. Проверьте интернет соединение

### Проблема: Mini App не открывается

**Решение:**
1. Проверьте что frontend собран: `cd frontend && npm run build`
2. Убедитесь что Nginx правильно настроен
3. Проверьте SSL сертификаты: `sudo certbot certificates`
4. Проверьте что URL в BotFather совпадает с реальным

### Проблема: API ошибки 401

**Решение:**
1. Проверьте что `TELEGRAM_BOT_TOKEN` совпадает в `.env` и BotFather
2. Убедитесь что часы на сервере синхронизированы: `timedatectl`
3. Проверьте логи backend: `sudo journalctl -u ysell-api -n 50`

### Проблема: Экспорт не работает

**Решение:**
1. Убедитесь что пользователь ввел правильные Telegram API ключи
2. Проверьте что номер телефона в международном формате (+7...)
3. Проверьте права доступа к `/tmp/telegram_bot_sessions/`

## 📝 API Документация

После запуска backend, документация доступна по адресу:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🤝 Вклад в разработку

1. Fork репозитория
2. Создайте feature branch: `git checkout -b feature/amazing-feature`
3. Commit изменения: `git commit -m 'Add amazing feature'`
4. Push в branch: `git push origin feature/amazing-feature`
5. Откройте Pull Request

## 📄 Лицензия

MIT License - см. [LICENSE](../LICENSE)

## 💬 Поддержка

- GitHub Issues: https://github.com/Damir-Dev-AI-Creator/Telegram_Analyzer/issues
- Email: support@your-domain.com

## 🎉 Благодарности

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Anthropic Claude](https://www.anthropic.com/)
- [Telethon](https://github.com/LonamiWebs/Telethon)

---

Made with ❤️ for Telegram Community
