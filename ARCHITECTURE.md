# Архитектура CosmOS

## Core / Kernel

- **TaskRouter** — принимает задачу, выбирает агента по имени или capability
- **AgentSelector** — fallback-цепочка: запрошенный → дефолтный → shell
- **CapabilityRegistry** — каждый агент заявляет, что умеет (coding, research, chat...)
- **TaskStore (SQLite)** — задачи, события, health
- **EventBus** — события task.created, task.running, task.completed, task.failed
- **Verifier** — проверка результата: exit code, вывод, ошибки, таймауты

## Agent Runtime Layer

| Агент | Движок | Capabilities |
|-------|--------|-------------|
| Hermes | `hermes chat -q "..."` | research, automation, chat, shell |
| Claude | `claude -p "..."` | coding, research, chat, shell |
| OpenCode | `opencode run --model <m> "..."` | coding, shell |
| Shell | любой shell | shell |

- **WorktreeManager** — изолированный git worktree для кодовых задач
- **Result Verifier** — проверка exit code, пустого вывода, ошибок, таймаутов, git diff

## Interface Layer

- **CLI** — Typer (task, status, agents, doctor)
- **Web UI** — Phase 5 (React + Vite + Tailwind)
- **Telegram** — Phase 4
- **HTTP/API** — Phase 4 (FastAPI)

## Memory Layer

- **SQLite** — состояние CosmOS, задачи, события (✅ Phase 1)
- **Obsidian** — человекочитаемая база знаний (Phase 3)
- **Mem0** — персональные факты (Phase 3)
- **Vector DB** — поиск по документам (Phase 3)
- **Skills** — процедурная память для агентов

## Automation Layer (Phase 6)

- Cron jobs
- Webhooks
- Filesystem watchers
- Scheduled summaries

## Portability (Phase 7)

- `install.sh`
- `cosmos doctor`
- backup/restore
- Dockerfile + docker-compose
- systemd user service

## Principle

**CosmOS не заменяет агентов. Он координирует их, хранит контекст и проверяет результат.**
