"""CosmOS CLI — commands for task, status, doctor, agents, remote.

Supports local and remote (SSH) agent execution.
"""

import json
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .config import CosmOSConfig
from .core.state import TaskStore
from .core.router import TaskRouter
from .agents.base import Capability
from .agents.remote_agent import RemoteAgent

# Memory
from .memory import MemoryItem
from .memory.sqlite_memory import SQLiteMemory
from .memory.obsidian_memory import ObsidianMemory

# Global state (initialised lazily)
_cfg: CosmOSConfig | None = None
_store: TaskStore | None = None
_router: TaskRouter | None = None

console = Console()
app = typer.Typer(
    name="cosmos",
    help="CosmOS — настраиваемая агентная ОС",
    no_args_is_help=True,
    add_completion=False,
)


def _get_config() -> CosmOSConfig:
    global _cfg
    if _cfg is None:
        try:
            _cfg = CosmOSConfig.load()
        except FileNotFoundError:
            console.print("[red]✗ config not found:[/] cosmos.yaml")
            raise typer.Exit(1)
    return _cfg


def _get_store() -> TaskStore:
    global _store
    if _store is None:
        cfg = _get_config()
        path = cfg.memory.sqlite.path
        if not Path(path).is_absolute():
            root = Path(cfg.root).expanduser()
            path = str(root / path)
        _store = TaskStore(path)
    return _store


def _get_router() -> TaskRouter:
    global _router
    if _router is None:
        _router = TaskRouter(_get_config(), _get_store(), memory_stores=_get_memory())
    return _router


# ── Commands ──────────────────────────────────────────


@app.command()
def task(
    description: str = typer.Argument(..., help="Описание задачи"),
    agent: str = typer.Option(None, "--agent", "-a", help="Агент (hermes, claude, opencode...)"),
    host: str = typer.Option(None, "--host", "-h", help="Удалённый хост (из cosmos.yaml remote_hosts)"),
    path: str = typer.Option(None, "--path", "-p", help="Рабочая папка на удалённом хосте (по умолчанию ~/.cosmos/<id>)"),
):
    """Создать и выполнить задачу через агента.

    Укажите --host для выполнения на удалённом сервере через SSH.
    Удалённые задачи запускаются в фоне, коннект не удерживается.

    Укажите --path для задания рабочей папки на удалённом хосте.
    Если не указано, создаётся ~/.cosmos/<id>/.
    """
    router = _get_router()

    with console.status("[bold green]Выполняю задачу...") as _s:
        result = router.run_task(description, agent_name=agent, host=host, path=path)

    is_remote = (result.get("metadata") or {}).get("remote", False)
    status_icon = "✅" if result["status"] == "completed" else "❌"
    remote_icon = "🖥️ " if is_remote else ""

    console.print(f"\n{status_icon} {remote_icon}[bold]Задача:[/] {description}")
    console.print(f"   ID:     {result['id']}")
    console.print(f"   Агент:  {result['agent']}")
    console.print(f"   Статус: {result['status']}")

    if is_remote:
        meta = result.get("metadata", {})
        console.print(f"   Хост:   {meta.get('remote_host', '?')} ({meta.get('remote_host_address', '?')})")
        console.print(f"   Remote ID: {meta.get('remote_task_id', '?')}")
        console.print(f"   Path:   {meta.get('run_path', '~/.cosmos/<id>')}")
        if result["status"] == "running":
            console.print("[yellow]   ⏳ Задача выполняется на удалённом сервере.[/]")
            console.print("   Используйте [bold]cosmos status --poll[/bold] для обновления.")

    if result.get("duration_sec"):
        console.print(f"   Время:  {result['duration_sec']}с")

    if result.get("verified") is not None:
        v = "✅" if result["verified"] else "⚠️"
        console.print(f"   Вериф.: {v}")

    if result["status"] == "completed" and result["result"]:
        console.print(Panel(
            result["result"][:2000],
            title="Результат",
            border_style="green",
        ))
    if result["error"]:
        console.print(f"[red]Ошибка:[/] {result['error'][:500]}")


@app.command()
def status(
    limit: int = typer.Option(10, "--limit", "-l", help="Сколько задач показать"),
    filter_status: str = typer.Option(None, "--status", "-s", help="Фильтр по статусу"),
    poll: bool = typer.Option(False, "--poll", "-p", help="Проверить статус удалённых задач"),
):
    """Показать статус задач.

    Используйте --poll, чтобы проверить завершение удалённых задач.
    """
    store = _get_store()
    tasks = store.list_tasks(limit=limit, status=filter_status)

    if not tasks:
        console.print("[yellow]Нет задач[/]")
        raise typer.Exit(0)

    # Poll remote tasks if requested
    if poll:
        router = _get_router()
        for t in tasks:
            if t["status"] == "running" and (t.get("metadata") or {}).get("remote"):
                with console.status(f"[dim]Опрашиваю {t['id']}...") as _s:
                    updated = router.poll_remote_task(t["id"])
                if updated:
                    t.update(updated)

    table = Table(box=box.ROUNDED)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Описание", style="white")
    table.add_column("Агент", style="blue")
    table.add_column("Статус")
    table.add_column("Хост", style="dim")
    table.add_column("Создана", style="dim")

    for t in tasks:
        status_style = {
            "completed": "green",
            "running": "yellow",
            "pending": "dim",
            "failed": "red",
            "cancelled": "dim",
        }.get(t["status"], "white")
        desc = t["description"][:50] + ("..." if len(t["description"]) > 50 else "")
        created = t["created_at"][:19].replace("T", " ")
        meta = t.get("metadata") or {}
        host_display = meta.get("remote_host", "")
        agent_display = t.get("agent", "")
        host_str = f"🖥 {host_display}" if host_display else ""

        table.add_row(
            t["id"],
            desc,
            agent_display,
            f"[{status_style}]{t['status']}[/]",
            host_str,
            created,
        )
    console.print(table)


@app.command()
def agents():
    """Показать подключённых агентов и их возможности."""
    router = _get_router()
    agents_list = router.list_agents()

    table = Table(box=box.ROUNDED)
    table.add_column("Агент", style="cyan", no_wrap=True)
    table.add_column("Команда", style="blue")
    table.add_column("Доступен", style="bold")
    table.add_column("Возможности")
    table.add_column("Описание")

    for a in agents_list:
        avail_icon = "✅" if a.available else "❌"
        caps = ", ".join(c.value for c in a.capabilities)
        table.add_row(a.name, a.command, avail_icon, caps, a.description)
    console.print(table)


@app.command()
def doctor():
    """Проверка окружения CosmOS (включая удалённые хосты)."""
    console.print("[bold]CosmOS Health Check[/bold]\n")

    checks = []

    # Python
    import sys
    py_ok = sys.version_info >= (3, 11)
    checks.append(("Python 3.11+", py_ok, sys.version.split()[0]))

    # Config
    try:
        cfg = _get_config()
        checks.append(("cosmos.yaml", True, f"{cfg.name} v{cfg.version}"))

        # Remote hosts
        if cfg.remote_hosts:
            for host_name, host_cfg in cfg.remote_hosts.items():
                from .agents.ssh_runner import SSHRunner
                runner = SSHRunner(host_name, host_cfg)
                available = runner.check_available()
                status = "✅ reachable" if available else "❌ unreachable"
                checks.append((
                    f"  Remote: {host_name}",
                    available,
                    f"{host_cfg.user}@{host_cfg.host}:{host_cfg.port} — {status}",
                ))
        else:
            checks.append(("Remote hosts", True, "none configured"))
    except FileNotFoundError:
        checks.append(("cosmos.yaml", False, "not found"))
    except Exception as e:
        checks.append(("cosmos.yaml", False, str(e)))

    # SQLite
    try:
        store = _get_store()
        h = store.health()
        checks.append(("SQLite store", h["connected"],
                       f"{h['task_count']} tasks @ {h['path']}"))
    except Exception as e:
        checks.append(("SQLite store", False, str(e)))

    # Agents
    try:
        router = _get_router()
        for info in router.list_agents():
            if info.name == "shell":
                continue
            status = "✅ available" if info.available else "❌ not installed"
            caps = ", ".join(c.value for c in info.capabilities)
            checks.append((f"Agent: {info.name}", info.available,
                          f"{status} ({caps})"))
    except Exception as e:
        checks.append(("Agents", False, str(e)))

    # pyproject
    pp = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    checks.append(("pyproject.toml", pp.exists(), str(pp)))

    # Render
    for name, ok, detail in checks:
        icon = "✅" if ok else "❌"
        console.print(f"  {icon} [bold]{name}[/]")
        console.print(f"       {detail}")

    # Summary
    total = len(checks)
    passed = sum(1 for _, ok, _ in checks if ok)
    console.print(f"\n[bold]{'✅ Все проверки пройдены' if passed == total else '⚠️ ' + str(passed) + '/' + str(total) + ' пройдено'}[/]")


# ── Remote subcommands ───────────────────────────────


@app.command()
def remote(
    action: str = typer.Argument(..., help="Действие: list, poll, cancel, clean"),
    task_id: str = typer.Option(None, "--task", "-t", help="ID задачи для poll/cancel/clean"),
):
    """Управление удалёнными задачами.

    \b
    Примеры:
      cosmos remote list              — список всех удалённых задач
      cosmos remote poll --task <id>  — проверить статус удалённой задачи
      cosmos remote cancel --task <id> — отменить удалённую задачу
      cosmos remote clean --task <id> — удалить папку задачи на хосте

    \b
    Папка задачи НЕ удаляется автоматически при отмене или завершении.
    Используйте `remote clean` чтобы вручную очистить папку на хосте.
    Нельзя очистить папку незавершённой задачи (running/pending).
    """
    router = _get_router()

    if action == "list":
        store = _get_store()
        tasks = store.list_tasks(limit=50)
        remote_tasks = [t for t in tasks if (t.get("metadata") or {}).get("remote")]

        if not remote_tasks:
            console.print("[yellow]Нет удалённых задач[/]")
            raise typer.Exit(0)

        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Описание")
        table.add_column("Хост")
        table.add_column("Remote ID")
        table.add_column("Статус")
        for t in remote_tasks:
            meta = t.get("metadata") or {}
            table.add_row(
                t["id"],
                t["description"][:40] + "...",
                meta.get("remote_host", "?"),
                meta.get("remote_task_id", "?")[:12],
                t["status"],
            )
        console.print(table)

    elif action == "poll":
        if not task_id:
            console.print("[red]Укажите --task <id>[/]")
            raise typer.Exit(1)
        with console.status(f"[dim]Опрашиваю задачу {task_id}...") as _s:
            updated = router.poll_remote_task(task_id)
        if updated:
            status_icon = "✅" if updated["status"] == "completed" else "❌"
            console.print(f"\n{status_icon} [bold]Задача {task_id}[/]")
            console.print(f"   Статус: {updated['status']}")
            if updated["result"]:
                console.print(Panel(
                    updated["result"][:2000],
                    title="Результат",
                    border_style="green",
                ))
            if updated.get("error"):
                console.print(f"[red]Ошибка:[/] {updated['error'][:500]}")

    elif action == "cancel":
        if not task_id:
            console.print("[red]Укажите --task <id>[/]")
            raise typer.Exit(1)

        store = _get_store()
        task = store.get_task(task_id)
        if not task:
            console.print(f"[red]Задача {task_id} не найдена[/]")
            raise typer.Exit(1)

        meta = task.get("metadata") or {}
        host_name = meta.get("remote_host")
        remote_task_id = meta.get("remote_task_id")
        if not host_name or not remote_task_id:
            console.print("[red]Задача не является удалённой[/]")
            raise typer.Exit(1)

        # Find the remote agent
        for name, agent in router.remote_agents.items():
            if agent.host_name == host_name:
                err = agent.cancel_task(remote_task_id)
                if err:
                    console.print(f"[red]Ошибка отмены:[/] {err}")
                else:
                    store.update_task(task_id, status="cancelled")
                    console.print(f"[green]Задача {task_id} отменена на {host_name}[/]")
                raise typer.Exit(0)

        console.print(f"[red]Агент для хоста {host_name} не найден[/]")

    elif action == "clean":
        if not task_id:
            console.print("[red]Укажите --task <id>[/]")
            raise typer.Exit(1)

        store = _get_store()
        task = store.get_task(task_id)
        if not task:
            console.print(f"[red]Задача {task_id} не найдена[/]")
            raise typer.Exit(1)

        # Нельзя очистить незавершённую задачу
        if task["status"] in ("running", "pending"):
            console.print(f"[red]Задача {task_id} ещё не завершена (статус: {task['status']}).[/]")
            console.print("  Дождитесь завершения или отмените задачу сначала.")
            raise typer.Exit(1)

        meta = task.get("metadata") or {}
        host_name = meta.get("remote_host")
        remote_task_id = meta.get("remote_task_id")
        if not host_name or not remote_task_id:
            console.print("[red]Задача не является удалённой[/]")
            raise typer.Exit(1)

        # Find the remote agent
        for name, agent in router.remote_agents.items():
            if agent.host_name == host_name:
                err = agent.cleanup_task(remote_task_id)
                if err:
                    console.print(f"[red]Ошибка очистки:[/] {err}")
                else:
                    console.print(f"[green]Папка задачи {task_id} удалена на {host_name}[/]")
                raise typer.Exit(0)

        console.print(f"[red]Агент для хоста {host_name} не найден[/]")

    else:
        console.print(f"[red]Неизвестное действие: {action}. Допустимо: list, poll, cancel, clean[/]")


def _get_memory() -> dict[str, SQLiteMemory | ObsidianMemory]:
    """Initialise memory backends from config."""
    cfg = _get_config()
    stores = {}

    # SQLite memory
    sqlite_path = cfg.memory.sqlite.path
    if not Path(sqlite_path).is_absolute():
        root = Path(cfg.root).expanduser()
        sqlite_path = str(root / sqlite_path)
    stores["sqlite"] = SQLiteMemory(sqlite_path)

    # Obsidian memory
    if cfg.memory.obsidian.enabled:
        stores["obsidian"] = ObsidianMemory(
            vault_path=cfg.memory.obsidian.vault_path,
            notes_folder=cfg.memory.obsidian.notes_folder,
        )

    return stores


@app.command()
def memory(
    action: str = typer.Argument(..., help="Действие: write, search, status"),
    key: str = typer.Option("", "--key", "-k", help="Ключ записи (например Tasks/test или Knowledge/arch)"),
    content: str = typer.Option("", "--content", "-c", help="Содержимое для write"),
    tags: str = typer.Option("", "--tags", "-t", help="Теги через запятую"),
    query: str = typer.Option("", "--query", "-q", help="Поисковый запрос"),
    source: str = typer.Option("all", "--source", "-s", help="Источник: sqlite, obsidian, all"),
    limit: int = typer.Option(10, "--limit", "-l", help="Лимит результатов"),
):
    """Управление памятью CosmOS.

    \b
    Примеры:
      cosmos memory write --key Tasks/test --content "результат..." --tags test,ops
      cosmos memory search --query "архитектура роутера"
      cosmos memory search --query "ssh" --source obsidian
      cosmos memory status
    """
    stores = _get_memory()

    if action == "write":
        if not key:
            console.print("[red]Укажите --key[/]")
            raise typer.Exit(1)
        if not content:
            # Read from stdin if no --content
            content = typer.prompt("Введите содержимое (Ctrl+D для завершения)",
                                   default="", show_default=False)

        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        # Write to all active stores
        keys = []
        for name, store in stores.items():
            k = store.store(key, content, tags=tag_list)
            keys.append(f"{name}:{k}")

        console.print(f"[green]✓ Записано: {', '.join(keys)}[/]")

    elif action == "search":
        if not query:
            console.print("[red]Укажите --query[/]")
            raise typer.Exit(1)

        results: list[MemoryItem] = []
        for name, store in stores.items():
            if source in ("all", name):
                results.extend(store.search(query, limit=limit))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:limit]

        if not results:
            console.print("[yellow]Ничего не найдено[/]")
            raise typer.Exit(0)

        table = Table(box=box.ROUNDED)
        table.add_column("Ключ", style="cyan")
        table.add_column("Источник", style="blue")
        table.add_column("Контент", style="white")
        table.add_column("Теги", style="dim")
        for item in results:
            content_preview = item.content[:80].replace("\n", " ")
            tags_str = ", ".join(item.tags[:3])
            table.add_row(item.key, item.source, content_preview, tags_str)
        console.print(table)

    elif action == "status":
        table = Table(box=box.ROUNDED)
        table.add_column("Источник", style="cyan")
        table.add_column("Статус", style="bold")
        table.add_column("Детали")

        for name, store in stores.items():
            ok = store.health()
            icon = "✅" if ok else "❌"
            if isinstance(store, SQLiteMemory):
                detail = f"путь: {store.db_path}"
            elif isinstance(store, ObsidianMemory):
                detail = f"vault: {store.base}"
            else:
                detail = ""
            table.add_row(name, icon, detail)

        console.print(table)

    else:
        console.print(f"[red]Неизвестное действие: {action}. Допустимо: write, search, status[/]")


@app.command()
def bot(
    platform: str = typer.Argument("telegram",
                                   help="Платформа бота (telegram)"),
    daemon: bool = typer.Option(False, "--daemon",
                                help="Запустить в фоне (через nohup)"),
):
    """Запустить интерфейс-бота (Telegram / будущие платформы)."""
    if platform == "telegram":
        cfg = _get_config()
        if not cfg.interfaces.telegram.enabled:
            console.print("[red]Telegram bot отключён в конфиге (interfaces.telegram.enabled=false)[/]")
            raise typer.Exit(1)
        if not cfg.interfaces.telegram.bot_token:
            console.print("[red]TELEGRAM_COSMOS_BOT_TOKEN не задан. Укажи в .env[/]")
            raise typer.Exit(1)

        store = _get_store()
        router = _get_router()

        if daemon:
            import subprocess
            import sys
            # Re-launch self without --daemon in background
            cmd = [sys.executable, "-m", "cosmos", "bot", "telegram"]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            console.print(f"[green]✓ Telegram bot запущен в фоне (PID: {proc.pid})[/]")
            return

        from .interfaces.telegram_bot import TelegramBot
        console.print("[blue]Запуск Telegram бота...[/]")
        TelegramBot(cfg, router, store).run()
    else:
        console.print(f"[red]Неизвестная платформа: {platform}. Допустимо: telegram[/]")


def main():
    app()
