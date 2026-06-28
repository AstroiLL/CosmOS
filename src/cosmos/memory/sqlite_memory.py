"""SQLiteMemory — key-value store with FTS5 search for CosmOS.

Separate from TaskStore; stores arbitrary memory entries with tags,
full-text search, and metadata.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import MemoryAdapter, MemoryItem


class SQLiteMemory(MemoryAdapter):
    """SQLite-backed key-value memory with FTS5 full-text search."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                source TEXT DEFAULT 'cosmos',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS kv_fts USING fts5(
                key, content, tags,
                content=kv_store, content_rowid=rowid
            );
            CREATE TRIGGER IF NOT EXISTS kv_ai AFTER INSERT ON kv_store BEGIN
                INSERT INTO kv_fts(rowid, key, content, tags)
                VALUES (new.rowid, new.key, new.content, new.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS kv_ad AFTER DELETE ON kv_store BEGIN
                INSERT INTO kv_fts(kv_fts, rowid, key, content, tags)
                VALUES ('delete', old.rowid, old.key, old.content, old.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS kv_au AFTER UPDATE ON kv_store BEGIN
                INSERT INTO kv_fts(kv_fts, rowid, key, content, tags)
                VALUES ('delete', old.rowid, old.key, old.content, old.tags);
                INSERT INTO kv_fts(rowid, key, content, tags)
                VALUES (new.rowid, new.key, new.content, new.tags);
            END;
        """)
        self._conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── MemoryAdapter API ────────────────────────────────

    def store(self, key: str, content: str, tags: Optional[list[str]] = None,
              metadata: Optional[dict] = None) -> str:
        now = self._now()
        tags_json = json.dumps(tags or [])
        meta_json = json.dumps(metadata or {})
        self._conn.execute(
            """INSERT OR REPLACE INTO kv_store
               (key, content, tags, metadata, source, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'cosmos', COALESCE(
                   (SELECT created_at FROM kv_store WHERE key = ?), ?
               ), ?)""",
            (key, content, tags_json, meta_json, key, now, now),
        )
        self._conn.commit()
        return key

    def retrieve(self, key: str) -> Optional[MemoryItem]:
        row = self._conn.execute(
            "SELECT * FROM kv_store WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        return MemoryItem(
            key=d["key"],
            content=d["content"],
            source="sqlite",
            tags=json.loads(d.get("tags", "[]")),
            created_at=d.get("created_at", ""),
            score=1.0,
        )

    def search(self, query: str, limit: int = 10) -> list[MemoryItem]:
        if not query.strip():
            return self._recent(limit)
        try:
            rows = self._conn.execute(
                """SELECT kv.key, kv.content, kv.tags, kv.created_at, rank
                   FROM kv_fts
                   JOIN kv_store kv ON kv.rowid = kv_fts.rowid
                   WHERE kv_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS5 syntax error — fall back to LIKE search
            rows = self._conn.execute(
                """SELECT key, content, tags, created_at, 1.0 as rank
                   FROM kv_store
                   WHERE content LIKE ? OR key LIKE ?
                   LIMIT ?""",
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            results.append(MemoryItem(
                key=d["key"],
                content=d["content"],
                source="sqlite",
                tags=json.loads(d.get("tags", "[]")),
                created_at=d.get("created_at", ""),
                score=float(1.0 / (d.get("rank", 1.0) or 1.0)),
            ))
        return results

    def delete(self, key: str) -> bool:
        cur = self._conn.execute("DELETE FROM kv_store WHERE key = ?", (key,))
        self._conn.commit()
        return cur.rowcount > 0

    def health(self) -> bool:
        try:
            self._conn.execute("SELECT 1 FROM kv_store LIMIT 1")
            return True
        except Exception:
            return False

    def list_keys(self, prefix: str = "", limit: int = 50) -> list[str]:
        if prefix:
            rows = self._conn.execute(
                "SELECT key FROM kv_store WHERE key LIKE ? LIMIT ?",
                (f"{prefix}%", limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT key FROM kv_store LIMIT ?", (limit,)
            ).fetchall()
        return [r["key"] for r in rows]

    def _recent(self, limit: int = 10) -> list[MemoryItem]:
        rows = self._conn.execute(
            "SELECT key, content, tags, created_at FROM kv_store ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            MemoryItem(
                key=r["key"],
                content=r["content"],
                source="sqlite",
                tags=json.loads(r.get("tags", "[]")),
                created_at=r.get("created_at", ""),
                score=1.0,
            )
            for r in rows
        ]

    def close(self):
        self._conn.close()
