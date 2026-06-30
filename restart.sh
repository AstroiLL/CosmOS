#!/usr/bin/env bash
# ── CosmOS — перезапуск всех сервисов ──────────────────
# Использование: ./restart.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔄 CosmOS — перезапуск сервисов..."
"$SCRIPT_DIR/stop.sh"
sleep 2
"$SCRIPT_DIR/start.sh"
