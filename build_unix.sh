#!/bin/bash
# ============================================
# Скрипт сборки Ysell Analyzer для macOS/Linux
# ============================================

set -e

echo ""
echo "========================================"
echo "  Сборка Ysell Analyzer v0.2.0"
echo "========================================"
echo ""

# Определение ОС
OS="$(uname -s)"
case "${OS}" in
    Darwin*)    PLATFORM="macOS";;
    Linux*)     PLATFORM="Linux";;
    *)          PLATFORM="Unknown";;
esac

echo "Платформа: $PLATFORM"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "[ОШИБКА] Python3 не найден!"
    echo "Установите Python 3.9+:"
    if [ "$PLATFORM" = "macOS" ]; then
        echo "  brew install python"
    else
        echo "  sudo apt install python3 python3-pip"
    fi
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python версия: $PYTHON_VERSION"

# Проверка/установка PyInstaller
echo "[1/4] Проверка PyInstaller..."
if ! python3 -m pip show pyinstaller &> /dev/null; then
    echo "      Установка PyInstaller..."
    python3 -m pip install pyinstaller
fi

# Установка зависимостей
echo "[2/4] Проверка зависимостей..."
python3 -m pip install -r requirements.txt -q

# Очистка
echo "[3/4] Очистка предыдущей сборки..."
rm -rf dist build

# Сборка
echo "[4/4] Сборка приложения..."
echo "      Это может занять несколько минут..."
echo ""

python3 -m PyInstaller YsellAnalyzer.spec --noconfirm

if [ $? -ne 0 ]; then
    echo ""
    echo "[ОШИБКА] Сборка не удалась!"
    exit 1
fi

echo ""
echo "========================================"
echo "  СБОРКА ЗАВЕРШЕНА УСПЕШНО!"
echo "========================================"
echo ""

if [ "$PLATFORM" = "macOS" ]; then
    echo "Приложение: dist/YsellAnalyzer.app"
    if [ -d "dist/YsellAnalyzer.app" ]; then
        SIZE=$(du -sh "dist/YsellAnalyzer.app" | cut -f1)
        echo "Размер: $SIZE"
    fi
    echo ""
    echo "Для распространения:"
    echo "  1. Скопируйте YsellAnalyzer.app в /Applications"
    echo "  2. Или создайте DMG: hdiutil create -volname YsellAnalyzer -srcfolder dist/YsellAnalyzer.app -ov YsellAnalyzer.dmg"
else
    echo "Файл: dist/YsellAnalyzer"
    if [ -f "dist/YsellAnalyzer" ]; then
        SIZE=$(du -h "dist/YsellAnalyzer" | cut -f1)
        echo "Размер: $SIZE"
        chmod +x "dist/YsellAnalyzer"
    fi
fi

echo ""
echo "Теперь вы можете отправить приложение"
echo "любому пользователю $PLATFORM."
echo ""
