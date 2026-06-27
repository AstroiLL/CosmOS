"""CosmOS CLI — commands for task, status, doctor."""

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .config import CosmOSConfig
from .core.state import TaskStore
from .core.router import TaskRouter
from .agents.base import Capability

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
        _router = TaskRouter(_get_config(), _get_store())
    return _router


# ── Commands ──────────────────────────────────────────


@app.command()
def task(
    description: str = typer.Argument(..., help="Описание задачи"),
    agent: str = typer.Option(None, "--agent", "-a", help="Агент (hermes, opencode...)"),
):
    """Создать и выполнить задачу через агента."""
    with console.status("[bold green]Выполняю задачу...") as _s:
        router = _get_router()
        result = router.run_task(description, agent_name=agent)
    status_icon = "✅" if result["status"] == "completed" else "❌"
    console.print(f"\n{status_icon} [bold]Задача:[/] {description}")
    console.print(f"   ID:     {result['id']}")
    console.print(f"   Агент:  {result['agent']}")
    console.print(f"   Статус: {result['status']}")
    console.print(f"   Время:  {result.get('duration_sec', '?')}с")
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
):
    """Показать статус задач."""
    store = _get_store()
    tasks = store.list_tasks(limit=limit, status=filter_status)

    if not tasks:
        console.print("[yellow]Нет задач[/]")
        raise typer.Exit(0)

    table = Table(box=box.ROUNDED)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Описание", style="white")
    table.add_column("Агент", style="blue")
    table.add_column("Статус")
    table.add_column("Создана", style="dim")

    for t in tasks:
        status_style = {
            "completed": "green",
            "running": "yellow",
            "pending": "dim",
            "failed": "red",
            "cancelled": "dim",
        }.get(t["status"], "white")
        desc = t["description"][:60] + ("..." if len(t["description"]) > 60 else "")
        created = t["created_at"][:19].replace("T", " ")
        table.add_row(
            t["id"],
            desc,
            t["agent"],
            f"[{status_style}]{t['status']}[/]",
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
    """Проверка окружения CosmOS."""
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
                continue  # always available
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


def main():
    app()
