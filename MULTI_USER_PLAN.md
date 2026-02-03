# 🔐 Multi-User система - План реализации

## 🎯 Цель

Сделать бота **полностью независимым для каждого пользователя**:
- Каждый пользователь использует **свои API ключи** (API_ID, API_HASH, PHONE)
- Каждый работает со **своими чатами** через свой Telegram аккаунт
- **Изолированные данные**: сессии, экспорты, настройки
- **Опциональный CLAUDE_API_KEY** для каждого пользователя

---

## 📊 Текущее состояние vs Целевое

### ❌ Текущее состояние (Single-User)
```
.env файл (глобальный):
├── API_ID (один для всех)
├── API_HASH (один для всех)
├── PHONE (один для всех)
├── CLAUDE_API_KEY (один для всех)
├── BOT_TOKEN (глобальный)
└── OWNER_ID (только один пользователь)

Ограничения:
- Только владелец может использовать
- Все используют один Telegram аккаунт
- Нет изоляции данных
```

### ✅ Целевое состояние (Multi-User)
```
.env файл (только бот):
└── BOT_TOKEN (глобальный для бота)

База данных (per-user):
User 1:
├── user_id: 123456789
├── api_id: 12345678
├── api_hash: abcd1234...
├── phone: +1234567890
├── claude_api_key: sk-ant-...
├── session_string: (зашифрованная сессия)
└── settings: {...}

User 2:
├── user_id: 987654321
├── api_id: 87654321
├── api_hash: dcba4321...
├── phone: +9876543210
├── claude_api_key: sk-ant-...
├── session_string: (зашифрованная сессия)
└── settings: {...}

Преимущества:
✅ Любой может использовать бота
✅ Каждый работает со своими чатами
✅ Полная изоляция данных
✅ Масштабируемость
```

---

## 🏗️ Архитектура Multi-User системы

```
┌─────────────────────────────────────────────────────────┐
│                    TELEGRAM BOT                         │
│                                                         │
│  User 1 → Bot → User 1 Settings → User 1 Telegram      │
│  User 2 → Bot → User 2 Settings → User 2 Telegram      │
│  User N → Bot → User N Settings → User N Telegram      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    DATABASE (SQLite)                     │
│                                                         │
│  ┌─────────────────────────────────────────┐           │
│  │ users                                   │           │
│  ├─────────────────────────────────────────┤           │
│  │ user_id (PK)      : BigInteger          │           │
│  │ username          : String              │           │
│  │ first_name        : String              │           │
│  │ api_id            : Integer             │           │
│  │ api_hash          : String              │           │
│  │ phone             : String              │           │
│  │ claude_api_key    : String (optional)   │           │
│  │ session_string    : Text (encrypted)    │           │
│  │ is_configured     : Boolean             │           │
│  │ is_authorized     : Boolean             │           │
│  │ created_at        : DateTime            │           │
│  │ last_active       : DateTime            │           │
│  └─────────────────────────────────────────┘           │
│                                                         │
│  ┌─────────────────────────────────────────┐           │
│  │ user_settings                           │           │
│  ├─────────────────────────────────────────┤           │
│  │ user_id (FK)      : BigInteger          │           │
│  │ exclude_user_id   : Integer             │           │
│  │ exclude_username  : String              │           │
│  │ default_limit     : Integer             │           │
│  │ export_folder     : String              │           │
│  └─────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              PER-USER FILE STORAGE                      │
│                                                         │
│  data/                                                  │
│  ├── users/                                            │
│  │   ├── 123456789/                                   │
│  │   │   ├── exports/        (CSV файлы)              │
│  │   │   ├── analysis/       (DOCX файлы)             │
│  │   │   └── session.session (Telethon сессия)        │
│  │   ├── 987654321/                                   │
│  │   │   ├── exports/                                 │
│  │   │   ├── analysis/                                │
│  │   │   └── session.session                          │
│  │   └── ...                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Этапы реализации

### **Этап 1: База данных**

#### 1.1. Создать модели SQLAlchemy
```python
# core/database.py

class User(Base):
    """Пользователь бота"""
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    first_name = Column(String(255))
    api_id = Column(Integer)
    api_hash = Column(String(255))
    phone = Column(String(50))
    claude_api_key = Column(String(512))
    session_string = Column(Text)  # StringSession от Telethon
    is_configured = Column(Boolean, default=False)
    is_authorized = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

class UserSettings(Base):
    """Настройки пользователя"""
    user_id = Column(BigInteger, ForeignKey('users.user_id'), primary_key=True)
    exclude_user_id = Column(Integer, default=0)
    exclude_username = Column(String(255), default="")
    default_limit = Column(Integer, default=10000)
```

#### 1.2. Создать менеджер БД
```python
# core/db_manager.py

class DatabaseManager:
    """Менеджер для работы с БД"""

    async def get_user(self, user_id: int) -> Optional[User]
    async def create_user(self, user_id: int, ...) -> User
    async def update_user(self, user_id: int, **kwargs)
    async def is_user_configured(self, user_id: int) -> bool
    async def save_session(self, user_id: int, session_string: str)
```

#### 1.3. Инициализация БД
```python
# При старте бота создавать БД если её нет
DATABASE_PATH = "data/bot.db"
engine = create_async_engine(f"sqlite+aiosqlite:///{DATABASE_PATH}")
```

---

### **Этап 2: Onboarding процесс**

#### 2.1. FSM States для настройки
```python
# bot/states/setup_states.py

class SetupStates(StatesGroup):
    waiting_api_id = State()
    waiting_api_hash = State()
    waiting_phone = State()
    waiting_code = State()
    waiting_password = State()  # 2FA
    waiting_claude_key = State()
```

#### 2.2. Handler /start для новых пользователей
```python
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # Проверить настроен ли пользователь
    user = await db.get_user(user_id)

    if not user or not user.is_configured:
        # Начать процесс настройки
        await message.answer(
            "👋 Привет! Для начала работы нужно настроить бота.\n\n"
            "Мне понадобятся твои Telegram API ключи.\n"
            "Получить их можно здесь: https://my.telegram.org/apps\n\n"
            "Отправь мне <b>API_ID</b> (8 цифр):"
        )
        await state.set_state(SetupStates.waiting_api_id)
    else:
        # Показать главное меню
        await show_main_menu(message)
```

#### 2.3. Сбор API_ID, API_HASH, PHONE
```python
@router.message(SetupStates.waiting_api_id)
async def process_api_id(message: Message, state: FSMContext):
    api_id = message.text.strip()

    # Валидация
    if not api_id.isdigit():
        await message.answer("❌ API_ID должен быть числом. Попробуй еще раз:")
        return

    await state.update_data(api_id=int(api_id))
    await message.answer("✅ API_ID сохранен!\n\nТеперь отправь <b>API_HASH</b>:")
    await state.set_state(SetupStates.waiting_api_hash)

# Аналогично для API_HASH и PHONE
```

#### 2.4. Авторизация через Telegram
```python
@router.message(SetupStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    data = await state.get_data()

    # Создать клиент Telethon
    client = TelegramClient(
        StringSession(),
        data['api_id'],
        data['api_hash']
    )

    await client.connect()
    await client.send_code_request(phone)

    await state.update_data(phone=phone, client=client)
    await message.answer(
        "📱 Код отправлен на твой Telegram!\n\n"
        "Отправь мне код из сообщения:"
    )
    await state.set_state(SetupStates.waiting_code)
```

#### 2.5. Ввод кода подтверждения
```python
@router.message(SetupStates.waiting_code)
async def process_code(message: Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()

    try:
        await data['client'].sign_in(data['phone'], code)

        # Сохранить сессию
        session_string = data['client'].session.save()

        # Сохранить в БД
        await db.create_user(
            user_id=message.from_user.id,
            api_id=data['api_id'],
            api_hash=data['api_hash'],
            phone=data['phone'],
            session_string=session_string,
            is_configured=True,
            is_authorized=True
        )

        await message.answer(
            "✅ <b>Настройка завершена!</b>\n\n"
            "Теперь ты можешь использовать все команды бота.\n"
            "Используй /help для справки."
        )

        await state.clear()

    except SessionPasswordNeededError:
        await message.answer("🔐 Введи пароль двухфакторной аутентификации:")
        await state.set_state(SetupStates.waiting_password)
```

---

### **Этап 3: Обновление существующих компонентов**

#### 3.1. Убрать AuthMiddleware (или сделать опциональным)
```python
# bot/main.py

# УДАЛИТЬ:
# dp.message.middleware(AuthMiddleware(owner_id=OWNER_ID))

# Вместо этого: проверка is_configured
```

#### 3.2. Обновить services/telegram.py
```python
# services/telegram.py

async def export_telegram_csv_for_user(
    user_id: int,
    chat: str,
    start_date: str = None,
    end_date: str = None,
    limit: int = 10000
):
    """Экспорт для конкретного пользователя"""

    # Загрузить настройки пользователя из БД
    user = await db.get_user(user_id)

    if not user or not user.is_authorized:
        raise ValueError("Пользователь не настроен")

    # Создать клиент из сохраненной сессии
    client = TelegramClient(
        StringSession(user.session_string),
        user.api_id,
        user.api_hash
    )

    await client.connect()

    # Экспорт в папку пользователя
    export_folder = f"data/users/{user_id}/exports"
    os.makedirs(export_folder, exist_ok=True)

    # ... остальная логика экспорта
```

#### 3.3. Обновить task_worker.py
```python
# services/task_worker.py

async def _process_export(self, task: Task):
    user_id = task.user_id

    # Использовать настройки конкретного пользователя
    result_filename = await export_telegram_csv_for_user(
        user_id=user_id,
        chat=task.data['chat_id'],
        ...
    )

    # Отправить файл пользователю
    file_path = f"data/users/{user_id}/exports/{result_filename}"
    ...
```

---

### **Этап 4: Команда /settings**

#### 4.1. Просмотр настроек
```python
@router.message(Command("settings"))
async def cmd_settings(message: Message):
    user = await db.get_user(message.from_user.id)

    if not user:
        await message.answer("❌ Ты не настроен. Используй /start")
        return

    settings_text = f"""
⚙️ <b>Твои настройки</b>

<b>Telegram API:</b>
• API ID: <code>{user.api_id}</code>
• Телефон: <code>{user.phone}</code>
• Авторизован: {'✅' if user.is_authorized else '❌'}

<b>Claude API:</b>
• Настроен: {'✅ Да' if user.claude_api_key else '❌ Нет'}

<b>Действия:</b>
/settings_edit - Изменить настройки
/settings_reauth - Переавторизоваться
/settings_claude - Настроить Claude API
"""

    await message.answer(settings_text)
```

#### 4.2. Редактирование настроек
```python
@router.message(Command("settings_edit"))
async def cmd_settings_edit(message: Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📝 API ID", callback_data="edit_api_id"))
    keyboard.add(InlineKeyboardButton(text="📝 API Hash", callback_data="edit_api_hash"))
    keyboard.add(InlineKeyboardButton(text="📱 Телефон", callback_data="edit_phone"))
    keyboard.add(InlineKeyboardButton(text="🤖 Claude API", callback_data="edit_claude"))

    await message.answer(
        "Что хочешь изменить?",
        reply_markup=keyboard.as_markup()
    )
```

---

### **Этап 5: Безопасность и изоляция**

#### 5.1. Шифрование session_string
```python
# core/encryption.py

from cryptography.fernet import Fernet

def encrypt_session(session_string: str, key: bytes) -> str:
    """Шифровать session string"""
    f = Fernet(key)
    return f.encrypt(session_string.encode()).decode()

def decrypt_session(encrypted: str, key: bytes) -> str:
    """Расшифровать session string"""
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()
```

#### 5.2. Изоляция файлов
```python
# Структура папок
data/
├── bot.db                    # База данных
├── users/
│   ├── 123456789/
│   │   ├── exports/          # CSV файлы этого пользователя
│   │   ├── analysis/         # DOCX файлы
│   │   └── session.session   # Telethon сессия (опционально)
│   ├── 987654321/
│   │   ├── exports/
│   │   ├── analysis/
│   │   └── session.session
```

#### 5.3. Квоты и лимиты (опционально)
```python
class User(Base):
    # Добавить поля для контроля использования
    export_count = Column(Integer, default=0)
    analyze_count = Column(Integer, default=0)
    last_export = Column(DateTime)

    # Лимиты
    daily_export_limit = Column(Integer, default=10)
    daily_analyze_limit = Column(Integer, default=5)
```

---

## 🔄 Workflow нового пользователя

```
1. User отправляет /start боту

2. Бот проверяет: есть ли user в БД?
   ❌ Нет → Начать onboarding
   ✅ Да → Показать главное меню

3. Onboarding процесс:
   a) Бот: "Отправь API_ID"
   b) User: 12345678
   c) Бот: "Отправь API_HASH"
   d) User: abcd1234...
   e) Бот: "Отправь номер телефона"
   f) User: +1234567890
   g) Бот отправляет код через Telegram API
   h) Бот: "Отправь код подтверждения"
   i) User: 12345
   j) Бот: "✅ Авторизация успешна!"
   k) Сохранение session_string в БД

4. User может использовать все команды:
   /export @my_channel
   /analyze file.csv
   /exportanalyze @support

5. Каждый работает со своими чатами через свой аккаунт
```

---

## 📊 Сравнение: До и После

| Аспект | До (Single-User) | После (Multi-User) |
|--------|------------------|-------------------|
| Пользователи | Только владелец (OWNER_ID) | Любой желающий |
| API ключи | Общие из .env | У каждого свои в БД |
| Telegram аккаунт | Один для всех | У каждого свой |
| Чаты | Только владельца | Свои для каждого |
| Изоляция данных | Нет | Полная изоляция |
| Масштабируемость | Нет | Да |
| Безопасность | Низкая | Высокая |

---

## 🚀 Преимущества Multi-User системы

### Для пользователей
✅ **Простота**: Не нужно деплоить свою копию бота
✅ **Приватность**: Работа только со своими чатами
✅ **Удобство**: Настройка один раз через /start
✅ **Безопасность**: Данные изолированы

### Для разработчика
✅ **Масштабируемость**: Один бот для всех
✅ **Монетизация**: Можно добавить платные тарифы
✅ **Статистика**: Видно сколько пользователей
✅ **Обновления**: Один деплой для всех

---

## ⚠️ Важные замечания

### Безопасность
- **Шифровать session_string** в БД
- **HTTPS только** для вебхуков (если используются)
- **Rate limiting** для защиты от спама
- **Валидация** всех входных данных

### Производительность
- **Connection pooling** для БД
- **Кеширование** часто используемых данных
- **Асинхронность** везде (asyncio, aiofiles, etc)
- **Очистка** старых файлов периодически

### Юридические аспекты
- **GDPR compliance** - право на удаление данных
- **Privacy Policy** - описать что хранится
- **Terms of Service** - правила использования
- **Команда /delete_account** для удаления всех данных

---

## 📋 Checklist реализации

### Этап 1: База данных
- [ ] Создать модели User и UserSettings
- [ ] Создать DatabaseManager
- [ ] Инициализация БД при старте
- [ ] Тесты CRUD операций

### Этап 2: Onboarding
- [ ] FSM states для настройки
- [ ] Handler /start для новых пользователей
- [ ] Сбор API_ID, API_HASH, PHONE
- [ ] Авторизация через Telegram
- [ ] Обработка 2FA
- [ ] Сохранение session_string
- [ ] Опциональный ввод CLAUDE_API_KEY

### Этап 3: Обновление компонентов
- [ ] Убрать/обновить AuthMiddleware
- [ ] Обновить services/telegram.py (per-user)
- [ ] Обновить task_worker.py (per-user)
- [ ] Обновить handlers для работы с БД
- [ ] Per-user файловая структура

### Этап 4: Команда /settings
- [ ] Просмотр текущих настроек
- [ ] Редактирование настроек
- [ ] Переавторизация
- [ ] Настройка Claude API
- [ ] Удаление аккаунта

### Этап 5: Безопасность
- [ ] Шифрование session_string
- [ ] Изоляция файлов per-user
- [ ] Rate limiting
- [ ] Валидация входных данных

### Этап 6: Тестирование
- [ ] Onboarding нового пользователя
- [ ] Экспорт с разных аккаунтов
- [ ] Анализ с разными API ключами
- [ ] Изоляция данных
- [ ] Производительность под нагрузкой

---

## 🎓 Следующие шаги

После реализации Multi-User системы можно добавить:

1. **Веб-интерфейс** - управление через браузер
2. **API endpoint** - программный доступ
3. **Subscription модель** - платные тарифы
4. **Аналитика** - дашборд с метриками
5. **Уведомления** - email/push при завершении задач

---

**Дата создания:** 2026-01-26
**Версия:** 1.0
**Статус:** План для реализации
