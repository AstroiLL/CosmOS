# CosmOS — план построения агентной ОС

## Цель

CosmOS — переносимая, расширяемая агентная ОС, которая объединяет разные AI CLI/агенты, интерфейсы и памяти в единую управляемую систему.

Ключевые требования:

- легко разворачивается на новой машине;
- работает локально и может жить на сервере;
- поддерживает разные агенты: Hermes, Claude Code, Codex, OpenCode и другие;
- имеет несколько интерфейсов: CLI, Web, Telegram, API;
- использует несколько типов памяти: Obsidian, SQLite/session DB, Mem0, vector DB, skills;
- легко редактируется агентами: простая структура, декларативные конфиги, минимум скрытой магии.

---

## Блоки системы

### 1. CosmOS Core / Kernel

Задача: центральное ядро, которое принимает задачи, выбирает маршрут и контролирует выполнение.

Компоненты:

- task registry — список задач, статусы, история;
- router — классификация задачи и выбор исполнителя;
- agent selector — выбор Hermes/Claude/Codex/другого агента;
- execution manager — запуск процессов, таймауты, логи;
- policy layer — разрешения, опасные команды, доступ к файлам;
- event bus — события: task.created, task.started, task.completed, memory.updated;
- state store — SQLite как базовое локальное состояние.

Результат блока:

- команда или API-вызов создаёт задачу;
- задача получает исполнителя;
- результат сохраняется и возвращается пользователю.

---

### 2. Agent Runtime Layer

Задача: единый способ работать с разными агентными CLI.

Компоненты:

- Hermes adapter;
- Claude Code adapter;
- Codex adapter;
- OpenCode adapter;
- generic CLI adapter;
- worktree/container isolation для задач с кодом;
- verifier — проверка результата после агента.

Принцип:

CosmOS не должен слепо верить агентам. Агент выполнил — CosmOS проверил: файлы, diff, тесты, логи, результат.

---

### 3. Interface Layer

Задача: разные входы в одну систему.

Интерфейсы:

- CLI: `cosmos task "..."`, `cosmos status`, `cosmos agents`, `cosmos memory`;
- Web UI: панель задач, агентов, памяти, автоматизаций;
- Telegram: быстрые команды и уведомления;
- HTTP API: интеграция с внешними сервисами;
- Webhooks: событие снаружи → задача внутри CosmOS.

Требование к Web UI:

- современный, простой интерфейс;
- визуальные референсы лежат в `img/`;
- компоненты должны быть маленькими и легко редактируемыми агентами.

---

### 4. Memory Layer

Задача: хранить разные типы памяти в правильных местах.

Типы памяти:

- operational memory — текущие задачи, статусы, логи;
- session memory — история взаимодействий;
- personal/project memory — Obsidian vault;
- semantic memory — vector DB / embeddings;
- procedural memory — skills, инструкции, workflow;
- external knowledge — NotebookLM, Google Drive, документы.

Базовая схема:

- SQLite — состояние CosmOS, задачи, события;
- Obsidian — человекочитаемая база знаний;
- Mem0 — персональные факты/предпочтения;
- vector DB — поиск по документам и заметкам;
- skills — повторяемые процедуры для агентов.

---

### 5. Tool / Integration Layer

Задача: подключать внешние инструменты без переписывания ядра.

Компоненты:

- MCP servers;
- shell tools;
- Python scripts;
- Google Workspace;
- NotebookLM;
- Obsidian;
- Home Assistant / smart home позже;
- custom plugins.

Принцип:

Каждая интеграция — адаптер с явным конфигом и health-check.

---

### 6. Automation Layer

Задача: автономная работа без постоянного ручного запуска.

Компоненты:

- cron jobs;
- watchers;
- webhooks;
- scheduled reports;
- background tasks;
- alerts/notifications.

Примеры:

- ежедневная сводка;
- мониторинг серверов;
- обновление индекса Obsidian;
- синхронизация знаний в NotebookLM;
- проверка зависших задач.

---

### 7. Portability / Deployment Layer

Задача: CosmOS легко переносится и разворачивается на новой машине.

Компоненты:

- `install.sh` — первичная установка;
- `cosmos doctor` — проверка окружения;
- `cosmos backup` — экспорт состояния;
- `cosmos restore` — восстановление;
- `.env.example` — список секретов без самих секретов;
- `cosmos.yaml` — главный переносимый конфиг;
- Docker/Compose профиль для серверного запуска;
- systemd user service для Linux;
- миграции SQLite;
- health checks для агентов и интеграций.

Что должно переноситься:

- код проекта;
- конфиги без секретов;
- список подключённых агентов;
- структура памяти;
- SQLite state при необходимости;
- skills/workflows;
- документация и bootstrap scripts.

Что не должно храниться в Git:

- API keys;
- OAuth tokens;
- приватные cookie/session files;
- личные базы данных без явного решения;
- большие логи.

---

## Этапы построения

### Этап 0 — Foundation

Цель: проект можно открыть, понять и безопасно развивать.

Задачи:

- [x] создать папку проекта;
- [x] создать базовую структуру;
- [x] описать архитектурные блоки;
- [x] зафиксировать UI-направление;
- [x] зафиксировать NotebookLM Agent OS как референс;
- [x] выбрать стек MVP;
- [x] создать главный `cosmos.yaml`;
- [x] создать `.env.example`;
- [x] создать bootstrap/install план.

Acceptance criteria:

- ✅ новый агент понимает проект по README + docs;
- ✅ есть понятный roadmap;
- ✅ нет секретов в репозитории.

---

### Этап 1 — CLI MVP

Цель: минимальная рабочая CosmOS через командную строку.

Задачи:

- [x] команда `cosmos task "..."`;
- [x] SQLite task store;
- [x] базовый router задач;
- [x] Hermes adapter;
- [x] generic shell/CLI adapter;
- [x] логирование выполнения + events;
- [x] команда `cosmos status`;
- [x] команда `cosmos doctor`.

Acceptance criteria:

- ✅ можно создать задачу из CLI;
- ✅ CosmOS запускает Hermes или shell adapter;
- ✅ результат сохраняется;
- ✅ `cosmos status` показывает историю.

---

### Этап 2 — Agent Adapters

Цель: подключить несколько AI CLI под единым интерфейсом.

Задачи:

- [x] Claude Code adapter;
- [ ] ~~Codex adapter~~ (отложено);
- [x] OpenCode adapter;
- [x] adapter capability registry;
- [x] per-agent config;
- [x] таймауты и отмена задач;
- [x] режим worktree isolation для кодовых задач;
- [x] verifier после выполнения.

Acceptance criteria:

- ✅ один и тот же task API может запускать разных агентов;
- ✅ выбор агента задаётся явно или через router;
- ✅ CosmOS проверяет результат, а не только читает self-report агента.

---

### Этап 3 — Memory MVP

Цель: сделать память частью ОС, а не приложением сбоку.

Задачи:

- [ ] SQLite schema: tasks, events, sessions, artifacts;
- [ ] Obsidian adapter: read/search/write safe notes;
- [ ] memory routing: что писать в Obsidian, что в SQLite, что в skills;
- [ ] индексация заметок;
- [ ] подключение NotebookLM как reference/knowledge source;
- [ ] memory export/import.

Acceptance criteria:

- задача может сохранять артефакты и заметки;
- Obsidian используется аккуратно и предсказуемо;
- можно перенести состояние памяти на другую машину.

---

### Этап 4 — API + Telegram

Цель: использовать CosmOS не только из терминала.

Задачи:

- [ ] FastAPI/HTTP API;
- [ ] endpoints: create task, list tasks, get task, cancel task;
- [ ] Telegram command interface;
- [ ] уведомления о завершении задач;
- [ ] webhook endpoint.

Acceptance criteria:

- задачу можно создать через API;
- Telegram показывает статус и результат;
- внешние события могут запускать задачи.

---

### Этап 5 — Web UI

Цель: современная панель управления агентной ОС.

Задачи:

- [ ] выбрать frontend stack;
- [ ] сделать dashboard;
- [ ] экран Tasks;
- [ ] экран Agents;
- [ ] экран Memory;
- [ ] экран Automations;
- [ ] экран Settings;
- [ ] использовать референсы из `img/`;
- [ ] держать UI максимально редактируемым агентами.

Acceptance criteria:

- видно активные/завершённые задачи;
- можно создать задачу из Web UI;
- видно подключённых агентов и их health;
- компоненты маленькие и понятные.

---

### Этап 6 — Automations

Цель: CosmOS умеет работать фоном.

Задачи:

- [ ] cron scheduler integration;
- [ ] filesystem watchers;
- [ ] recurring tasks;
- [ ] scheduled summaries;
- [ ] notification routing;
- [ ] stuck task detector.

Acceptance criteria:

- можно создать регулярную задачу;
- CosmOS присылает уведомления;
- зависшие задачи обнаруживаются.

---

### Этап 7 — Portable Deployment

Цель: новая машина поднимает CosmOS быстро и предсказуемо.

Задачи:

- [ ] `scripts/install.sh`;
- [ ] `scripts/doctor.sh` или `cosmos doctor`;
- [ ] `scripts/backup.sh`;
- [ ] `scripts/restore.sh`;
- [ ] Dockerfile;
- [ ] docker-compose.yaml;
- [ ] systemd user service;
- [ ] migration scripts;
- [ ] deployment guide.

Acceptance criteria:

- на новой Linux-машине можно выполнить install + restore;
- CosmOS поднимает CLI/API/Web;
- отсутствующие агенты показываются как missing, а не ломают систему;
- секреты вводятся отдельно и не лежат в Git.

---

### Этап 8 — Hardening

Цель: система становится надёжной, безопасной и удобной для долгой жизни.

Задачи:

- [ ] permission model;
- [ ] audit log;
- [ ] approvals for risky actions;
- [ ] backup policy;
- [ ] tests;
- [ ] error recovery;
- [ ] observability dashboard;
- [ ] documentation for agents and humans.

Acceptance criteria:

- опасные действия требуют подтверждения;
- можно понять, что сделал агент и почему;
- сбой не уничтожает состояние;
- есть тесты основных сценариев.

---

## Рекомендуемый первый вертикальный срез

Не строить всё сразу. Первый рабочий срез:

1. `cosmos task "..."`
2. SQLite task store.
3. Hermes adapter.
4. `cosmos status`.
5. `cosmos doctor`.
6. `cosmos.yaml`.
7. Простая переносимость: install script + `.env.example`.

После этого уже добавлять Claude/Codex, API, Web UI и память.

---

## Предлагаемый стек MVP

Backend / CLI:

- Python 3.11+;
- Typer или Click для CLI;
- Pydantic для конфигов;
- SQLite для state;
- SQLModel или SQLAlchemy позже, если схемы усложнятся;
- subprocess/pty/tmux для CLI-агентов;
- FastAPI для API на этапе 4.

Frontend позже:

- React/Vite или Next.js;
- простая компонентная структура;
- Tailwind или CSS variables;
- shadcn/ui возможно, если не усложнит агентное редактирование.

Deployment:

- uv для Python-зависимостей;
- Docker/Compose для серверного режима;
- systemd user service для Linux;
- backup/restore через tar + SQLite dump.

---

## Северная звезда

CosmOS должна быть не красивой игрушкой, а рабочей мастерской:

- задача входит через любой интерфейс;
- ядро выбирает агента;
- агент работает в контролируемом окружении;
- результат проверяется;
- память обновляется;
- пользователь видит простой итог.

Коротко: **one mind, many agents, portable home**.
