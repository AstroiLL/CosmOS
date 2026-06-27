# CosmOS

**Настраиваемая и расширяемая агентная ОС.**  
Слой-оркестратор над AI CLI/агентами: Hermes, Claude Code, OpenCode.

```
cosmos task "Напиши что такое CosmOS"         # → Hermes (исследование)
cosmos task "Создай hello.py" --agent claude   # → Claude Code (кодинг)
cosmos task "fix the bug" --agent opencode     # → OpenCode (кодинг)
cosmos status                                   #  → история задач
cosmos agents                                    #  → кто доступен
cosmos doctor                                    #  → проверка здоровья
```

## Быстрый старт

```bash
# Установка зависимостей
cd ~/Sync/GPT/CosmOS
uv sync

# Проверка
uv run cosmos doctor

# Создать задачу
uv run cosmos task "Какая сейчас погода в Краснодаре"
```

## Архитектура

```
┌─────────────────────────────────────────────────┐
│                   Interfaces                    │
│  CLI (typer)  │  API (fastapi)  │  Web  │  TG   │
├─────────────────────────────────────────────────┤
│                   Core                          │
│  TaskRouter → AgentSelector → Executor → Store  │
│  CapabilityRegistry  │  Verifier  │  EventBus   │
├─────────────────────────────────────────────────┤
│                Agent Runtime                    │
│  HermesAgent  │  ClaudeAgent  │  OpenCodeAgent  │
│  ShellAgent   │  WorktreeManager                │
├─────────────────────────────────────────────────┤
│                  Memory                         │
│  SQLite (state)  │  Obsidian  │  Mem0  │  vec   │
├─────────────────────────────────────────────────┤
│               Automation                        │
│  Cron  │  Webhooks  │  Watchers                 │
└─────────────────────────────────────────────────┘
```

## Агенты

| Агент | Возможности | Команда |
|-------|-------------|---------|
| Hermes | `research, chat, automation, shell` | `hermes chat -q "..."` |
| Claude | `coding, research, chat, shell` | `claude -p "..."` |
| OpenCode | `coding, shell` | `opencode run --model <m> "..."` |
| Shell | `shell` | любой shell-команда |

## Реализованные команды

| Команда | Описание |
|---------|----------|
| `cosmos task <описание>` | Создать и выполнить задачу |
| `cosmos task <...> --agent claude` | Явно указать агента |
| `cosmos status` | Список задач |
| `cosmos status --status failed` | Фильтр по статусу |
| `cosmos agents` | Список агентов + возможности |
| `cosmos doctor` | Проверка окружения |

## Фазы развития

- ✅ **Phase 0** — Foundation (структура, конфиги, roadmap)
- ✅ **Phase 1** — CLI MVP (task, status, doctor, Hermes adapter)
- ✅ **Phase 2** — Agent adapters (Claude, OpenCode, capability registry, verifier, worktree)
- 🔜 **Phase 3** — Memory MVP (Obsidian, индексация)
- 🔜 **Phase 4** — API + Telegram
- 🔜 **Phase 5** — Web UI
- 🔜 **Phase 6** — Automation
- 🔜 **Phase 7** — Portable deployment
- 🔜 **Phase 8** — Hardening

## Структура проекта

```
CosmOS/
├── cosmos.yaml            # Главный конфиг
├── .env.example           # Шаблон секретов
├── pyproject.toml         # Зависимости (uv)
├── README.md
├── ROADMAP.md
├── ARCHITECTURE.md
├── docs/
│   ├── os-build-plan.md   # Детальный план построения
│   ├── tech-stack.md      # Стек технологий
│   ├── mvp-scenarios.md   # Сценарии использования
│   ├── glossary.md
│   └── web-ui-guidelines.md
├── img/                   # Референсы Web UI
├── data/
│   ├── cosmos.sqlite      # Task store
│   └── logs/
└── src/cosmos/
    ├── cli.py             # Typer CLI (task, status, agents, doctor)
    ├── config.py          # Pydantic → cosmos.yaml
    ├── core/
    │   ├── state.py       # SQLite TaskStore
    │   └── router.py      # TaskRouter + capability registry
    └── agents/
        ├── base.py        # BaseAgent, AgentResult, Capability, AgentInfo
        ├── hermes_agent.py
        ├── claude_agent.py
        ├── opencode_agent.py
        ├── shell_agent.py
        ├── worktree.py    # Git worktree isolation
        └── verifier.py    # Result verification
```

## Принципы

1. **Не заменяет агентов** — координирует их, хранит контекст и проверяет результат.
2. **Переносимость** — одна команда на чистой машине поднимает CosmOS.
3. **Агент-friendly** — код и конфиги должны быть понятны AI-агентам.
4. **Проверка** — CosmOS не верит агентам на слово, он верифицирует результат.
