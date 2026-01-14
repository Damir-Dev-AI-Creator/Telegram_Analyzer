# 📦 Сборка Ysell Analyzer в standalone приложение

## 🎯 Цель
Создать один исполняемый файл (.exe для Windows, .app для macOS, бинарник для Linux) без необходимости установки Python.

---

## 🛠️ Способ 1: PyInstaller (Рекомендуется)

### Установка PyInstaller
```bash
pip install pyinstaller
```

### Windows — сборка .exe

```bash
cd ysell_analyzer_improved

pyinstaller --noconfirm --onefile --windowed ^
    --name "YsellAnalyzer" ^
    --icon "resources/icon.ico" ^
    --add-data "core;core" ^
    --add-data "services;services" ^
    --add-data "ui;ui" ^
    --hidden-import "customtkinter" ^
    --hidden-import "telethon" ^
    --hidden-import "anthropic" ^
    --hidden-import "pandas" ^
    --hidden-import "docx" ^
    --collect-all "customtkinter" ^
    --collect-all "telethon" ^
    main.py
```

### macOS — сборка .app

```bash
cd ysell_analyzer_improved

pyinstaller --noconfirm --onefile --windowed \
    --name "YsellAnalyzer" \
    --icon "resources/icon.icns" \
    --add-data "core:core" \
    --add-data "services:services" \
    --add-data "ui:ui" \
    --hidden-import "customtkinter" \
    --hidden-import "telethon" \
    --hidden-import "anthropic" \
    --hidden-import "pandas" \
    --hidden-import "docx" \
    --collect-all "customtkinter" \
    --collect-all "telethon" \
    --osx-bundle-identifier "com.ysell.analyzer" \
    main.py
```

### Linux — сборка бинарника

```bash
cd ysell_analyzer_improved

pyinstaller --noconfirm --onefile --windowed \
    --name "YsellAnalyzer" \
    --add-data "core:core" \
    --add-data "services:services" \
    --add-data "ui:ui" \
    --hidden-import "customtkinter" \
    --hidden-import "telethon" \
    --hidden-import "anthropic" \
    --hidden-import "pandas" \
    --hidden-import "docx" \
    --collect-all "customtkinter" \
    --collect-all "telethon" \
    main.py
```

### Результат
После сборки файл будет в папке `dist/`:
- Windows: `dist/YsellAnalyzer.exe`
- macOS: `dist/YsellAnalyzer.app`
- Linux: `dist/YsellAnalyzer`

---

## 🛠️ Способ 2: Spec-файл PyInstaller (Более надёжный)

Создайте файл `YsellAnalyzer.spec` и запустите:
```bash
pyinstaller YsellAnalyzer.spec
```

---

## 🛠️ Способ 3: Nuitka (Более быстрое приложение)

### Установка
```bash
pip install nuitka ordered-set zstandard
```

### Windows
```bash
nuitka --standalone --onefile ^
    --windows-console-mode=disable ^
    --enable-plugin=tk-inter ^
    --include-package=customtkinter ^
    --include-package=telethon ^
    --include-package=anthropic ^
    --include-package=pandas ^
    --include-package=docx ^
    --windows-icon-from-ico=resources/icon.ico ^
    --output-filename=YsellAnalyzer.exe ^
    main.py
```

### macOS
```bash
nuitka --standalone --onefile \
    --macos-create-app-bundle \
    --enable-plugin=tk-inter \
    --include-package=customtkinter \
    --include-package=telethon \
    --include-package=anthropic \
    --include-package=pandas \
    --include-package=docx \
    --macos-app-icon=resources/icon.png \
    --output-filename=YsellAnalyzer \
    main.py
```

---

## ⚠️ Важные замечания

### 1. Кросс-компиляция НЕ поддерживается
- Для Windows .exe — собирайте на Windows
- Для macOS .app — собирайте на macOS  
- Для Linux — собирайте на Linux

### 2. Размер файла
- PyInstaller: ~50-150 MB (включает Python runtime)
- Nuitka: ~30-80 MB (компилирует в машинный код)

### 3. Антивирусы
Windows Defender и другие антивирусы могут ложно срабатывать на PyInstaller-сборки. Решения:
- Подписать .exe цифровой подписью
- Добавить в исключения антивируса
- Использовать Nuitka (меньше ложных срабатываний)

### 4. Данные пользователя
Приложение автоматически создаёт папки при первом запуске:
- Windows: `%APPDATA%\YsellAnalyzer\` и `Documents\YsellAnalyzer\`
- macOS: `~/Library/Application Support/YsellAnalyzer/` и `~/Documents/YsellAnalyzer/`
- Linux: `~/.config/YsellAnalyzer/` и `~/Documents/YsellAnalyzer/`

---

## 🔧 Автоматизация сборки

### GitHub Actions (CI/CD)

Создайте `.github/workflows/build.yml` для автоматической сборки на всех платформах при создании релиза.

---

## 📋 Чек-лист перед распространением

- [ ] Протестировать на чистой системе без Python
- [ ] Проверить, что окно настройки появляется при первом запуске
- [ ] Проверить экспорт из Telegram
- [ ] Проверить анализ Claude API
- [ ] Проверить создание DOCX отчётов
- [ ] Добавить иконку приложения
- [ ] Создать README для пользователей

---

## 📝 Что получит пользователь

1. **Один файл** — YsellAnalyzer.exe (или .app / бинарник)
2. **Первый запуск** — появится окно настройки с полями:
   - Telegram API ID
   - Telegram API Hash
   - Номер телефона
   - Claude API Key
3. **После настройки** — данные сохраняются локально
4. **Работа** — полнофункциональное приложение без Python

