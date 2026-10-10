#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "==================================================="
echo "    Запуск обучающего бота Marie Laveau Staff"
echo "==================================================="

# Проверка Python 3
if ! command -v python3 &> /dev/null; then
    echo "[ОШИБКА] Python 3 не найден!"
    exit 1
fi

echo "[1/2] Проверка зависимостей..."
pip3 install -r requirements.txt --quiet

echo "[2/2] Запуск бота..."
echo "Бот работает! Для остановки нажмите Ctrl + C"
echo "==================================================="

while true; do
    python3 bot.py || true
    echo "[ВНИМАНИЕ] Бот остановлен. Перезапуск через 5 секунд..."
    sleep 5
done
