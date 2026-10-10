@echo off
chcp 65001 > nul
title Marie Laveau Staff Bot

echo ===================================================
echo     Запуск обучающего бота Marie Laveau Staff
echo ===================================================
echo.

:: Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден на этом компьютере!
    echo Скачайте и установите Python с сайта https://python.org
    echo Обязательно поставьте галочку "Add Python to PATH" при установке.
    pause
    exit /b
)

:: Проверка и установка зависимостей
echo [1/2] Проверка библиотек...
pip install -r requirements.txt --quiet

echo [2/2] Запуск бота...
echo Бот работает! Не закрывайте это окно.
echo Чтобы остановить бота, нажмите Ctrl + C
echo ===================================================
echo.

:loop
python bot.py
echo.
echo [ВНИМАНИЕ] Бот был остановлен или произошёл сбой.
echo Перезапуск через 5 секунд... (нажмите Ctrl+C для отмены)
timeout /t 5 >nul
goto loop
