# Roadmap

## Phase 0 — Project foundation

- [x] Создать рабочую папку
- [x] Создать структуру проекта
- [x] Описать архитектурные блоки
- [x] Зафиксировать UI-направление
- [x] Зафиксировать NotebookLM Agent OS как референс
- [x] Составить план построения ОС: `docs/os-build-plan.md`
- [x] Описать MVP-сценарии: `docs/mvp-scenarios.md`
- [x] Выбрать стек первого прототипа: `docs/tech-stack.md`
- [x] Создать `cosmos.yaml`
- [x] Создать `.env.example`
- [x] Инициализировать Git-репозиторий
- [x] Создать публичный репозиторий на GitHub (AstroiLL/CosmOS)
- [x] Настроить `.gitignore` (исключены `.env`, `*.sqlite`, `__pycache__/`, секреты)
- [x] Запушить проект в GitHub

## Phase 1 — CLI MVP

- [x] `cosmos task "..."` — создать и выполнить задачу
- [x] SQLite task/session store
- [x] Router для выбора Hermes/Claude/OpenCode
- [x] Hermes adapter
- [x] generic CLI adapter (Shell)
- [x] Базовый лог задач + events
- [x] Конфиг агентов (`cosmos.yaml`)
- [x] `cosmos status` — список задач
- [x] `cosmos doctor` — проверка окружения
- [x] `cosmos agents` — таблица агентов

## Phase 2 — Agent adapters

- [x] Claude adapter — `claude -p "query"`
- [x] OpenCode adapter — `opencode run --model <m> <msg>`
- [x] Capability registry — каждый агент заявляет возможности
- [x] Worktree isolation для кодовых задач — `WorktreeManager`
- [x] Verifier результата — `Verifier` (exit code, вывод, ошибки, таймаут)
- [ ] ~~Codex adapter~~ (отложено)

## Phase 2.5 — Remote SSH agents

- [x] `SSHRunner` — submit/poll/cancel/cleanup через SSH
- [x] Фоновый запуск: `nohup` + wrapper script, коннект не удерживается
- [x] `RemoteAgent(BaseAgent)` — адаптер для удалённых CLI
- [x] Remote host config (`remote_hosts` в `cosmos.yaml`)
- [x] `shell_env` — кастомное окружение (PATH и т.д.)
- [x] `cosmos task "..." --host <name> --agent <agent>` — задача на удалённом хосте
- [x] `cosmos task --path /custom/dir` — рабочая папка на удалённой машине
- [x] Авто `~/.cosmos/<id>/` при отсутствии `--path`
- [x] `cosmos status --poll` — проверить завершение удалённых задач
- [x] `cosmos remote {list,poll,cancel,clean}` — управление удалёнными задачами
- [x] Трекинг-файлы на хосте: `~/.cosmos/tasks/<id>/{pid,stdout,stderr,exit_status}`
- [x] Подключённые хосты: geekom (✅ opencode), kz (✅ opencode), relaxagent (⏳ opencode)

## Phase 3 — Memory

- [x] SQLiteMemory — key-value store + FTS5 full-text search
- [x] Obsidian adapter — .md в Vault/CosmOS/{Tasks,Knowledge,Agents,Journal}
- [x] Memory routing: SQLite + Obsidian активны одновременно
- [x] Индексация: FTS5 (SQLite) + ripgrep (Obsidian vault)
- [x] `cosmos memory {write,search,status}` — CLI для работы с памятью
- [x] Auto-write результатов задач в оба хранилища
- [ ] Export/import памяти (отложено)

## Phase 4 — API + Telegram

- [x] Telegram bot scaffold — `cosmos bot telegram`, python-telegram-bot, polling
- [x] Bot commands — /task, /status, /memory, /doctor, /agents, /help
- [x] Markdown formatter для результатов задач
- [x] HTTP API (FastAPI) — `cosmos api`, config, health/version
- [x] API endpoints — tasks CRUD, agents, doctor, memory/search
- [x] API key auth — Bearer middleware, env-переменная, dev mode fallback
- [x] .env загрузка через python-dotenv
- [ ] Уведомления о завершении задач (отложено)

## Phase 5 — Web UI

- [ ] Dashboard
- [ ] Tasks screen
- [ ] Agents screen
- [ ] Memory screen
- [ ] Automations screen
- [ ] Settings screen
- [ ] UI по референсам из `img/`

## Phase 6 — Automation

- [x] Cron — ежедневный авто-коммит и пуш в GitHub (3:00 MSK)
- [ ] Slack/Telegram-оповещения
- [ ] Watchers (файловые/директориальные)
- [ ] Scheduled summaries
- [ ] Stuck task detector

## Phase 7 — Portable deployment

- [ ] `scripts/install.sh` — установка зависимостей и окружения
- [ ] `cosmos doctor` (есть, расширить)
- [ ] Backup/restore scripts
- [ ] Dockerfile
- [ ] docker-compose.yaml
- [ ] systemd user service
- [ ] Deployment guide

## Phase 8 — Hardening

- [ ] Permission model
- [ ] Audit log
- [ ] Approvals for risky actions
- [ ] Tests (unit / integration / e2e)
- [ ] Observability (metrics, traces)
- [ ] Recovery procedures

---

**Legend:** `[x]` — done, `[ ]` — todo, `[~]` — in progress, `[~~]` — cancelled/delayed
