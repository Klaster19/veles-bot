#!/bin/bash

# Демон для автоматического запуска Telegram бота

# Путь к директории проекта (измените при необходимости)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Имя процесса
PROCESS_NAME="veles-telegram-bot"

# Лог-файл
LOG_FILE="$PROJECT_DIR/bot.log"

# PID-файл
PID_FILE="$PROJECT_DIR/bot.pid"

# Интервал перезапуска в секундах
RESTART_INTERVAL=5

# Функция для запуска бота
start_bot() {
    echo "$(date): Запуск Telegram бота..." >> "$LOG_FILE"
    
    # Активируем виртуальное окружение и запускаем бота
    cd "$PROJECT_DIR"
    source venv/bin/activate
    python3 bot.py >> "$LOG_FILE" 2>&1 &
    
    # Сохраняем PID процесса
    echo $! > "$PID_FILE"
    
    echo "$(date): Telegram бот запущен с PID $(cat $PID_FILE)" >> "$LOG_FILE"
}

# Функция для остановки бота
stop_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo "$(date): Остановка Telegram бота (PID: $PID)..." >> "$LOG_FILE"
        
        # Пробуем корректно завершить процесс
        kill -TERM $PID 2>/dev/null
        
        # Ждем 10 секунд для корректного завершения
        sleep 10
        
        # Если процесс все еще существует, убиваем его принудительно
        if kill -0 $PID 2>/dev/null; then
            echo "$(date): Принудительная остановка Telegram бота (PID: $PID)..." >> "$LOG_FILE"
            kill -KILL $PID 2>/dev/null
        fi
        
        # Удаляем PID-файл
        rm -f "$PID_FILE"
        
        echo "$(date): Telegram бот остановлен" >> "$LOG_FILE"
    else
        echo "$(date): PID-файл не найден. Бот не запущен." >> "$LOG_FILE"
    fi
}

# Функция для проверки статуса бота
status_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            echo "Telegram бот запущен (PID: $PID)"
            return 0
        else
            echo "Telegram бот не запущен (найден PID-файл, но процесс не существует)"
            return 1
        fi
    else
        echo "Telegram бот не запущен (PID-файл не найден)"
        return 1
    fi
}

# Функция для перезапуска бота
restart_bot() {
    stop_bot
    sleep 2
    start_bot
}

# Основной цикл демона
daemon_loop() {
    while true; do
        # Проверяем, запущен ли бот
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ! kill -0 $PID 2>/dev/null; then
                echo "$(date): Обнаружено падение Telegram бота. Перезапуск..." >> "$LOG_FILE"
                rm -f "$PID_FILE"
                start_bot
            fi
        else
            echo "$(date): Telegram бот не запущен. Запуск..." >> "$LOG_FILE"
            start_bot
        fi
        
        # Ждем перед следующей проверкой
        sleep $RESTART_INTERVAL
    done
}

# Обработка аргументов командной строки
case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        status_bot
        ;;
    daemon)
        daemon_loop
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|daemon}"
        echo "  start   - запустить Telegram бота"
        echo "  stop    - остановить Telegram бота"
        echo "  restart - перезапустить Telegram бота"
        echo "  status  - проверить статус Telegram бота"
        echo "  daemon  - запустить демон в фоновом режиме"
        exit 1
        ;;
esac

exit 0