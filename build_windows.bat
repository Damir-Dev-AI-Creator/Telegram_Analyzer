@echo off
REM ============================================
REM Скрипт сборки Ysell Analyzer для Windows
REM ============================================

echo.
echo ========================================
echo   Сборка Ysell Analyzer v0.2.0
echo ========================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python 3.9+ с python.org
    pause
    exit /b 1
)

REM Проверка/установка PyInstaller
echo [1/4] Проверка PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo      Установка PyInstaller...
    pip install pyinstaller
)

REM Проверка зависимостей
echo [2/4] Проверка зависимостей...
pip install -r requirements.txt -q

REM Очистка предыдущей сборки
echo [3/4] Очистка...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

REM Сборка
echo [4/4] Сборка приложения...
echo      Это может занять несколько минут...
echo.

pyinstaller YsellAnalyzer.spec --noconfirm

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сборка не удалась!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   СБОРКА ЗАВЕРШЕНА УСПЕШНО!
echo ========================================
echo.
echo Файл: dist\YsellAnalyzer.exe
echo Размер: 
for %%A in (dist\YsellAnalyzer.exe) do echo    %%~zA bytes
echo.
echo Теперь вы можете отправить YsellAnalyzer.exe
echo любому пользователю Windows.
echo.

pause
