# CosmOS — Запуск сервисов

## Требования

- **Python 3.11+** с установленным `uv`
- **Node.js 18+** для сборки Web UI (один раз)
- Виртуальное окружение: `uv venv && source .venv/bin/activate && uv sync`

## Быстрый старт

```bash
cd /home/astroill/Sync/GPT/CosmOS

# 1. Активировать окружение
source .venv/bin/activate

# 2. Собрать Web UI (только после изменений)
cd ui && npm run build && cd ..

# 3. Запустить все сервисы
./start.sh
```

## Скрипты

| Команда | Описание |
|---|---|
| `./start.sh` | Запуск API сервера и Telegram бота |
| `./stop.sh` | Останов всех сервисов |
| `./restart.sh` | Перезапуск (stop + start) |

## Сервисы

### 1. API сервер + Web UI

```
cosmos api
```

- **Порт:** 7455 (настроен в `cosmos.yaml`)
- **Хост:** 0.0.0.0 (доступен из LAN)
- **URL:** `http://ryzen:7455` или `http://10.10.10.50:7455`
- Раздаёт SPA (Svelte 5) из `ui/dist/`
- REST API: `/api/v1/*`

**Запуск вручную:**
```bash
cd /home/astroill/Sync/GPT/CosmOS
source .venv/bin/activate
cosmos api
```

### 2. Telegram бот

```
cosmos bot telegram
```

- Режим поллинга (не webhook)
- Флаг `--daemon` для запуска в фоне

**Запуск вручную:**
```bash
cd /home/astroill/Sync/GPT/CosmOS
source .venv/bin/activate
cosmos bot telegram
```

### 3. Hermes Agent (AI-агент)

Hermes — не отдельный сервис, а **встроенный агент** в роутере. Запускается как часть API.
При создании задачи с `--agent hermes` выполняется локально через CLI Hermes.

### 4. Удалённые агенты (SSH)

Подключаются через SSH без отдельного сервиса. Настроены в `cosmos.yaml`:

| Хост | Адрес | Агенты |
|---|---|---|
| geekom | `10.10.10.13` | opencode |
| kz | `45.152.87.160` | opencode |
| relaxagent | `203.161.41.197` | opencode |

## Проверка работоспособности

```bash
# Проверить API
curl -s http://localhost:7455/api/v1/doctor

# Проверить Web UI
curl -s -o /dev/null -w '%{http_code}' http://localhost:7455/

# Проверить агентов
curl -s http://localhost:7455/api/v1/agents | python3 -m json.tool
```

Ожидаемый ответ doctor:
```json
{"status":"ok","checks":{"config":"CosmOS v0.1.0","task_store":"ok","agents_available":7,"agents_total":7,"remote_hosts":3}}
```

## После перезагрузки сервера

```bash
cd /home/astroill/Sync/GPT/CosmOS
source .venv/bin/activate
./start.sh
```

Или одной строкой:
```bash
cd /home/astroill/Sync/GPT/CosmOS && source .venv/bin/activate && ./start.sh
```

## Частые проблемы

### Порт занят
```bash
# Проверить, кто на порту
ss -tlnp | grep 7455

# Принудительно убить процесс
kill $(ss -tlnp | grep 7455 | grep -oP 'pid=\K[0-9]+')
```

### UV не установлен
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Web UI не обновляется
```bash
cd /home/astroill/Sync/GPT/CosmOS/ui && npm run build
```
После сборки достаточно убить и перезапустить API — reload не требуется.
