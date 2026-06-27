"""SQLite state store for CosmOS tasks, events, and sessions."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class TaskStore:
    """Lightweight SQLite store for CosmOS tasks and events."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                agent TEXT NOT NULL DEFAULT 'hermes',
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','running','completed','failed','cancelled')),
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                result TEXT,
                error TEXT,
                metadata TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL REFERENCES tasks(id),
                type TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
        """)
        self._conn.commit()

    # ── Tasks ────────────────────────────────────────────

    def create_task(self, description: str, agent: str = "hermes",
                    metadata: Optional[dict] = None) -> str:
        task_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO tasks (id, description, agent, status, created_at, metadata) VALUES (?,?,?,?,?,?)",
            (task_id, description, agent, "pending", now,
             json.dumps(metadata or {})),
        )
        self._conn.commit()
        self._add_event(task_id, "task.created", {"description": description, "agent": agent})
        return task_id

    def _parse_metadata(self, row: dict) -> dict:
        """Parse metadata field from JSON string to dict."""
        if isinstance(row.get("metadata"), str):
            try:
                row["metadata"] = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                row["metadata"] = {}
        return row

    def get_task(self, task_id: str) -> Optional[dict]:
        row = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return self._parse_metadata(dict(row))

    def list_tasks(self, limit: int = 20, status: Optional[str] = None) -> list[dict]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._parse_metadata(dict(r)) for r in rows]

    def update_task(self, task_id: str, status: Optional[str] = None,
                    result: Optional[str] = None, error: Optional[str] = None,
                    metadata: Optional[dict] = None):
        now = datetime.now(timezone.utc).isoformat()
        updates = []
        params = []
        if status:
            updates.append("status = ?")
            params.append(status)
            if status == "running":
                updates.append("started_at = ?")
                params.append(now)
            elif status in ("completed", "failed", "cancelled"):
                updates.append("finished_at = ?")
                params.append(now)
        if result is not None:
            updates.append("result = ?")
            params.append(result)
        if error is not None:
            updates.append("error = ?")
            params.append(error)
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))
        if not updates:
            return
        params.append(task_id)
        self._conn.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params
        )
        self._conn.commit()
        if status:
            self._add_event(task_id, f"task.{status}",
                            {"status": status, "result": result, "error": error})

    def delete_task(self, task_id: str):
        self._conn.execute("DELETE FROM events WHERE task_id = ?", (task_id,))
        self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._conn.commit()

    # ── Events ───────────────────────────────────────────

    def _add_event(self, task_id: str, event_type: str, payload: Optional[dict] = None):
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO events (task_id, type, payload, created_at) VALUES (?,?,?,?)",
            (task_id, event_type, json.dumps(payload or {}), now),
        )
        self._conn.commit()

    def get_events(self, task_id: str, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM events WHERE task_id = ? ORDER BY id ASC LIMIT ?",
            (task_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Health ────────────────────────────────────────────

    def health(self) -> dict:
        try:
            self._conn.execute("SELECT 1").fetchone()
            task_count = self._conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            return {"connected": True, "task_count": task_count, "path": self.db_path}
        except Exception as e:
            return {"connected": False, "error": str(e), "path": self.db_path}

    def close(self):
        self._conn.close()
