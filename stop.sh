#!/usr/bin/env bash
# ── CosmOS — останов всех сервисов ─────────────────────
# Использование: ./stop.sh

echo "🛑 CosmOS — останов сервисов..."

# Останов API сервера
API_PID_FILE="/tmp/cosmos-api.pid"
if [ -f "$API_PID_FILE" ]; then
    PID=$(cat "$API_PID_FILE")
    if kill "$PID" 2>/dev/null; then
        echo "  ⚡ API сервер остановлен (PID: $PID)"
    else
        echo "  ⚡ API сервер не запущен"
    fi
    rm -f "$API_PID_FILE"
fi

# Останов Telegram бота
TG_PID_FILE="/tmp/cosmos-telegram.pid"
if [ -f "$TG_PID_FILE" ]; then
    PID=$(cat "$TG_PID_FILE")
    if kill "$PID" 2>/dev/null; then
        echo "  🤖 Telegram бот остановлен (PID: $PID)"
    else
        echo "  🤖 Telegram бот не запущен"
    fi
    rm -f "$TG_PID_FILE"
fi

# Дополнительная чистка: убить процессы cosmos, которые могли остаться
pkill -f "uvicorn.*cosmos" 2>/dev/null && echo "  🔄 Лишние процессы uvicorn очищены"

echo "✅ CosmOS остановлен"
