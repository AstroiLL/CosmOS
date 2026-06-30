#!/usr/bin/env bash
# ── CosmOS — запуск всех сервисов ──────────────────────
# Использование: ./start.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔧 CosmOS — запуск сервисов..."

# Активировать виртуальное окружение
if [ ! -d ".venv" ]; then
    echo "❌ .venv не найден. Создай: uv venv"
    exit 1
fi
source .venv/bin/activate

# PID-файлы
API_PID_FILE="/tmp/cosmos-api.pid"
TG_PID_FILE="/tmp/cosmos-telegram.pid"

# ── API сервер (FastAPI + Web UI) ─────────────────────
echo "  ⚡ API сервер → порт 7455"
cosmos api &
echo $! > "$API_PID_FILE"
sleep 2

# ── Telegram бот ───────────────────────────────────────
echo "  🤖 Telegram бот"
cosmos bot telegram --daemon
echo $! > "$TG_PID_FILE"

echo ""
echo "✅ CosmOS запущен!"
echo "   Web UI:   http://ryzen:7455"
echo "   Telegram: активен"
echo ""
echo "   Стоп:     ./stop.sh"
echo "   Рестарт:  ./restart.sh"
