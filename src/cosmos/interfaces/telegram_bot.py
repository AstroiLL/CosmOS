"""Telegram bot interface for CosmOS.

Commands:
  /task <desc> [--agent X] [--host Y]  — создать задачу
  /status [id]                          — список задач / детали
  /memory search <query>                — поиск по памяти
  /doctor                               — диагностика
  /agents                               — список агентов
  /help                                 — справка
"""

import logging
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from ..config import CosmOSConfig
from ..core.state import TaskStore
from ..core.router import TaskRouter

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot that exposes CosmOS commands."""

    def __init__(self, config: CosmOSConfig, router: TaskRouter, store: TaskStore):
        self.config = config
        self.router = router
        self.store = store
        self.tg_config = config.interfaces.telegram

    # ── Entry point ─────────────────────────────────────

    def run(self):
        """Blocking entry point. Starts polling, handles signals internally."""
        app = Application.builder().token(self.tg_config.bot_token).build()
        app.bot_data["router"] = self.router
        app.bot_data["store"] = self.store
        app.bot_data["config"] = self.config
        app.bot_data["bot"] = self

        self._register_handlers(app)
        logger.info(
            "Telegram bot starting (polling interval=%ss)...",
            self.tg_config.polling_interval,
        )
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    # ── Handlers ─────────────────────────────────────────

    def _register_handlers(self, app: Application):
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("task", self.cmd_task))
        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(CommandHandler("memory", self.cmd_memory))
        app.add_handler(CommandHandler("doctor", self.cmd_doctor))
        app.add_handler(CommandHandler("agents", self.cmd_agents))

    async def _check_user(self, update: Update) -> bool:
        """Check if user is allowed. Reject silently if not."""
        user_id = update.effective_user.id if update.effective_user else None
        if not self.tg_config.allowed_user_ids:
            return True  # no whitelist = open (single-user default)
        if user_id and user_id in self.tg_config.allowed_user_ids:
            return True
        logger.warning("Rejected user_id=%s (not in whitelist)", user_id)
        await update.message.reply_text("⛔ Access denied")
        return False

    async def _reply(self, update: Update, text: str):
        """Safe reply with markdown."""
        try:
            await update.message.reply_text(text, disable_web_page_preview=True)
        except Exception as e:
            logger.warning("Failed to send reply: %s", e)

    # ── /start, /help ──────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_user(update):
            return
        await self._reply(
            update,
            "👋 *CosmOS* — агентная ОС в работе.\n"
            "Используй /help для списка команд.",
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_user(update):
            return
        await self._reply(
            update,
            "*CosmOS — команды бота*\n\n"
            "/task `<описание>` — создать задачу\n"
            "/task `<описание>` `--agent hermes` — указать агента\n"
            "/task `<описание>` `--host geekom` — на удалённом хосте\n"
            "/status — последние задачи\n"
            "/status `<id>` — детали задачи\n"
            "/memory search `<запрос>` — поиск по памяти\n"
            "/doctor — диагностика\n"
            "/agents — список агентов\n"
            "/help — эта справка",
        )

    # ── /task ──────────────────────────────────────────

    async def cmd_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_user(update):
            return
        args = context.args
        if not args:
            await self._reply(update, "❓ Укажи описание задачи.\nПример: `/task Проверь диск на geekom`")
            return

        # Parse --agent and --host flags
        description_parts = []
        agent_name: Optional[str] = None
        host: Optional[str] = None
        it = iter(args)
        for arg in it:
            if arg == "--agent":
                agent_name = next(it, None)
            elif arg == "--host":
                host = next(it, None)
            else:
                description_parts.append(arg)
        description = " ".join(description_parts)

        if not description:
            await self._reply(update, "❓ Укажи описание задачи.")
            return

        # Run the task
        try:
            task = self.router.run_task(
                description=description,
                agent_name=agent_name,
                host=host,
            )
            await self._reply(update, self._format_task_result(task))
        except Exception as e:
            logger.exception("Task failed")
            await self._reply(update, f"❌ *Ошибка:* {e}")

    # ── /status ────────────────────────────────────────

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_user(update):
            return
        args = context.args

        if args:
            # Single task detail
            task_id = args[0]
            task = self.store.get_task(task_id)
            if not task:
                await self._reply(update, f"❌ Задача `{task_id}` не найдена.")
                return
            await self._reply(update, self._format_task_detail(task))
        else:
            # List recent tasks
            tasks = self.store.list_tasks(limit=10)
            if not tasks:
                await self._reply(update, "📭 Нет задач.")
                return
            await self._reply(update, self._format_task_list(tasks))

    # ── /memory search ─────────────────────────────────

    async def cmd_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_user(update):
            return
        args = context.args
        if not args or args[0] != "search":
            await self._reply(
                update,
                "❓ Использование: `/memory search <запрос>`",
            )
            return

        query = " ".join(args[1:])
        if not query:
            await self._reply(update, "❓ Укажи поисковый запрос.")
            return

        from ..memory import MemoryItem
        from ..memory.sqlite_memory import SQLiteMemory
        from ..memory.obsidian_memory import ObsidianMemory

        memory_cfg = self.config.memory
        results: list[MemoryItem] = []

        if memory_cfg.sqlite.enabled:
            sqlite_path = memory_cfg.sqlite.path
            if not sqlite_path.startswith("/"):
                root = Path(self.config.root)
                sqlite_path = str(root / sqlite_path)
            sqlite = SQLiteMemory(sqlite_path)
            results.extend(sqlite.search(query, limit=5))

        if memory_cfg.obsidian.enabled:
            obsidian = ObsidianMemory(
                vault_path=memory_cfg.obsidian.vault_path,
                notes_folder=memory_cfg.obsidian.notes_folder,
            )
            results.extend(obsidian.search(query, limit=5))

        if not results:
            await self._reply(update, f"🔍 Ничего не найдено по запросу: `{query}`")
            return

        lines = ["🔍 *Результаты поиска:*\n"]
        for item in results[:10]:
            preview = item.content[:120].replace("\n", " ")
            icon = "📄" if item.source == "sqlite" else "📓"
            lines.append(f"{icon} `{item.key}` ({item.source})")
            lines.append(f"   _{preview}_\n")
        await self._reply(update, "\n".join(lines))

    # ── /doctor ────────────────────────────────────────

    async def cmd_doctor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_user(update):
            return
        cfg = self.config
        lines = ["🩺 *CosmOS Doctor*\n"]

        # Config
        lines.append(f"• Конфиг: ✅ `{cfg.name}` v{cfg.version}")

        # SQLite store
        try:
            _ = self.store.health()
            lines.append("• TaskStore: ✅")
        except Exception:
            lines.append("• TaskStore: ❌")

        # Memory
        if cfg.memory.sqlite.enabled:
            from ..memory.sqlite_memory import SQLiteMemory
            sqlite_path = cfg.memory.sqlite.path
            if not sqlite_path.startswith("/"):
                sqlite_path = str(Path(cfg.root) / sqlite_path)
            sqlite = SQLiteMemory(sqlite_path)
            lines.append(f"• SQLiteMemory: {'✅' if sqlite.health() else '❌'}")

        if cfg.memory.obsidian.enabled:
            from ..memory.obsidian_memory import ObsidianMemory
            obsidian = ObsidianMemory(
                vault_path=cfg.memory.obsidian.vault_path,
                notes_folder=cfg.memory.obsidian.notes_folder,
            )
            lines.append(f"• Obsidian: {'✅' if obsidian.health() else '❌'}")

        # Agents
        agents = self.router.list_agents()
        available = [a for a in agents if a.available]
        lines.append(f"• Агенты: {len(available)}/{len(agents)} доступны")

        # Remote hosts
        if cfg.remote_hosts:
            lines.append(f"• Хосты: {len(cfg.remote_hosts)} в конфиге")
            for name, hc in cfg.remote_hosts.items():
                lines.append(f"   - {name} ({hc.host})")

        await self._reply(update, "\n".join(lines))

    # ── /agents ────────────────────────────────────────

    async def cmd_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_user(update):
            return
        agents = self.router.list_agents()
        if not agents:
            await self._reply(update, "📭 Нет зарегистрированных агентов.")
            return

        lines = ["🤖 *Доступные агенты:*\n"]
        for a in agents:
            status = "✅" if a.available else "❌"
            caps = ", ".join(sorted(c.value for c in a.capabilities))
            lines.append(f"{status} `{a.name}` — {a.description}")
            lines.append(f"   возможности: {caps}")
        await self._reply(update, "\n".join(lines))

    # ── Formatting helpers ─────────────────────────────

    @staticmethod
    def _format_task_result(task: dict) -> str:
        """Format a single completed task result for Telegram."""
        task_id = task.get("id", "?")
        desc = task.get("description", "")
        status = task.get("status", "unknown")
        agent = task.get("agent", "?")
        duration = task.get("duration_sec", 0)
        meta = task.get("metadata", {}) or {}

        icon = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"
        lines = [
            f"{icon} *Задача:* `{desc}`",
            f"• Статус: `{status}`",
            f"• Агент: `{agent}`",
        ]
        if duration:
            lines.append(f"• Время: {duration:.1f}с")

        host = meta.get("remote_host", meta.get("host", ""))
        if host:
            lines.append(f"• Хост: `{host}`")

        if meta.get("remote_task_id"):
            lines.append(f"• Remote ID: `{meta['remote_task_id']}`")

        result = task.get("result", "")
        if result:
            preview = result[:300].replace("\n", " ").strip()
            lines.append(f"• Результат: _{preview}_")

        error = task.get("error", "")
        if error:
            lines.append(f"• Ошибка: `{error[:200]}`")

        lines.append(f"\n📎 ID: `{task_id}`")
        return "\n".join(lines)

    @staticmethod
    def _format_task_list(tasks: list[dict]) -> str:
        """Format recent task list."""
        lines = ["📋 *Последние задачи:*\n"]
        for t in tasks:
            tid = t.get("id", "?")[:8]
            desc = (t.get("description", "") or "")[:50]
            status = t.get("status", "?")
            icon = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"
            lines.append(f"{icon} `{tid}` {desc}")
        lines.append("\nИспользуй `/status <id>` для деталей.")
        return "\n".join(lines)

    @staticmethod
    def _format_task_detail(task: dict) -> str:
        """Format detailed task info."""
        return TelegramBot._format_task_result(task)
