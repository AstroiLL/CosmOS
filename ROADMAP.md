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

## Phase 1 — CLI MVP

- [x] `cosmos task "..."`
- [x] SQLite task/session store
- [x] router для выбора Hermes/Claude/Codex
- [x] Hermes adapter
- [x] generic CLI adapter
- [x] базовый лог задач + events
- [x] конфиг агентов
- [x] `cosmos status`
- [x] `cosmos doctor`

## Phase 2 — Agent adapters

- [x] Claude Code adapter — `claude -p "query"`
- [ ] ~~Codex adapter~~ (отложено)
- [x] OpenCode adapter — `opencode run --model <m> <msg>`
- [x] capability registry
- [x] worktree isolation для кодовых задач — `WorktreeManager`
- [x] verifier результата — `Verifier`

## Phase 3 — Memory MVP

- [ ] Obsidian adapter
- [ ] SQLite task/session/event store
- [ ] простая индексация заметок
- [ ] memory routing: SQLite / Obsidian / Mem0 / skills
- [ ] export/import памяти

## Phase 4 — API + Telegram

- [ ] HTTP API
- [ ] Telegram interface
- [ ] webhook endpoint
- [ ] уведомления о завершении задач

## Phase 5 — Web UI

- [ ] Dashboard
- [ ] Tasks screen
- [ ] Agents screen
- [ ] Memory screen
- [ ] Automations screen
- [ ] Settings screen
- [ ] UI по референсам из `img/`

## Phase 6 — Automation

- [ ] cron tasks
- [ ] webhooks
- [ ] watchers
- [ ] scheduled summaries
- [ ] stuck task detector

## Phase 7 — Portable deployment

- [ ] `scripts/install.sh`
- [ ] `cosmos doctor`
- [ ] backup/restore scripts
- [ ] Dockerfile
- [ ] docker-compose.yaml
- [ ] systemd user service
- [ ] deployment guide

## Phase 8 — Hardening

- [ ] permission model
- [ ] audit log
- [ ] approvals for risky actions
- [ ] tests
- [ ] observability
- [ ] recovery procedures
