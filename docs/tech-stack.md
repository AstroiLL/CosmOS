# Стек первого прототипа CosmOS

## Backend / CLI

| Компонент | Выбор | Почему |
|-----------|-------|--------|
| Язык | Python 3.11+ | Универсальность, экосистема, Hermes тоже на Python |
| CLI framework | Typer | Простой, типобезопасный, автогенерация help |
| Конфиги | Pydantic + YAML | Валидация, типы, человекочитаемый формат |
| State DB | SQLite (stdlib) | Без внешних зависимостей, переносимость |
| ORM (позже) | SQLModel | Pydantic + SQLAlchemy, минимум бойлерплейта |
| Запуск агентов | subprocess | One-shot режим для всех агентов |
| API (Phase 4) | FastAPI | Быстрый, асинхронный, автодокументация |
| Зависимости | uv | Быстрый, современный, замена pip/venv |

## Агенты

| Агент | Режим | Статус |
|-------|-------|--------|
| **Hermes** | `hermes chat -q "..."` | ✅ Phase 1 |
| **Claude Code** | `claude -p "..."` | ✅ Phase 2 |
| **OpenCode** | `opencode run --model <m> "..."` | ✅ Phase 2 |
| **Shell** | любая shell-команда | ✅ Phase 1 |
| Codex | — | ⏳ отложено |

## Frontend (Phase 5)

| Компонент | Выбор | Почему |
|-----------|-------|--------|
| Framework | React + Vite | Быстрый dev-сервер, простая компонентная модель |
| Styling | Tailwind CSS | Утилитарный, легко редактируется агентами |
| Components | shadcn/ui (опционально) | Копируемые компоненты, не black-box библиотека |
| State | Zustand или React Context | Минимум магии, легко понять |

## Deployment (Phase 7)

| Компонент | Выбор | Почему |
|-----------|-------|--------|
| Python deps | uv | Быстрый, lockfile, воспроизводимость |
| Серверный режим | Docker + Compose | Изолированное окружение, легко переносить |
| Linux service | systemd user service | Стандартный, надёжный |
| Backup | tar + SQLite dump | Просто, без специализированных инструментов |

## Структура проекта (текущая)

```
cosmos/
├── pyproject.toml      # uv / pip зависимости
├── cosmos.yaml         # главный конфиг
├── .env                # секреты (не в Git)
├── .env.example        # шаблон секретов
└── src/cosmos/
    ├── __init__.py
    ├── cli.py          # Typer CLI entry point (task, status, agents, doctor)
    ├── config.py       # Pydantic config model
    ├── core/
    │   ├── __init__.py
    │   ├── state.py    # SQLite TaskStore
    │   └── router.py   # TaskRouter + capability registry
    ├── agents/
    │   ├── __init__.py
    │   ├── base.py     # BaseAgent, AgentResult, Capability, AgentInfo
    │   ├── hermes_agent.py  # Hermes adapter
    │   ├── claude_agent.py  # Claude Code adapter
    │   ├── opencode_agent.py  # OpenCode adapter
    │   ├── shell_agent.py   # Generic CLI adapter
    │   ├── worktree.py    # Git worktree isolation
    │   └── verifier.py    # Result verification
    ├── memory/          # Phase 3
    └── interfaces/      # Phase 4-5
```

## Принципы выбора

1. **Минимум зависимостей** — каждая новая зависимость должна оправдывать сложность переноса.
2. **Переносимость прежде всего** — если инструмент не ставится одной командой на чистую Linux-машину, ищем альтернативу.
3. **Агент-friendly** — код и конфиги должны быть понятны AI-агентам, которые будут их редактировать.
4. **Python first** — всё, что можно сделать на Python, делаем на Python. Shell-скрипты только для bootstrap/deployment.
