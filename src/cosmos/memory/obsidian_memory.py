"""ObsidianMemory — read/write CosmOS notes in an Obsidian vault.

Files go to Vault/CosmOS/ with subdirectories per category.
All notes are valid .md with YAML frontmatter — readable and editable
in Obsidian.
"""

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import MemoryAdapter, MemoryItem


class ObsidianMemory(MemoryAdapter):
    """Store and retrieve memory entries as .md files in an Obsidian vault.

    Directory structure:
      Vault/CosmOS/
        Tasks/<key>.md
        Knowledge/<key>.md
        Agents/<key>.md
        Journal/<key>.md
    """

    def __init__(self, vault_path: str, notes_folder: str = "CosmOS"):
        self.vault = Path(vault_path).expanduser()
        self.base = self.vault / notes_folder
        self.base.mkdir(parents=True, exist_ok=True)
        # Ensure subdirectories exist
        for sub in ("Tasks", "Knowledge", "Agents", "Journal"):
            (self.base / sub).mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        """Determine the file path for a key based on its prefix.

        Keys follow: <Category>/<name> or just <name> (defaults to Knowledge/).
        """
        if "/" in key:
            parts = key.split("/", 1)
            subdir = parts[0].capitalize()
            name = parts[1]
        else:
            subdir = "Knowledge"
            name = key

        # Validate subdir
        if subdir not in ("Tasks", "Knowledge", "Agents", "Journal"):
            subdir = "Knowledge"

        if not name.endswith(".md"):
            name = f"{name}.md"
        return self.base / subdir / name

    def _key_from_path(self, path: Path) -> str:
        """Reverse: file path → key."""
        rel = path.relative_to(self.base)
        parts = rel.parts
        if len(parts) >= 2:
            stem = Path(*parts[1:]).with_suffix("").as_posix()
            return f"{parts[0]}/{stem}"
        return parts[0].replace(".md", "")

    def _read_frontmatter(self, path: Path) -> dict:
        """Parse YAML frontmatter from a .md file."""
        content = path.read_text(encoding="utf-8", errors="replace")
        meta = {}
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if m:
            for line in m.group(1).strip().split("\n"):
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip().strip('"').strip("'")
        return meta

    def _strip_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter, return body."""
        return re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, count=1, flags=re.DOTALL)

    def _build_md(self, content: str, tags: Optional[list[str]] = None,
                  metadata: Optional[dict] = None) -> str:
        """Build a .md string with YAML frontmatter."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        meta = dict(metadata or {})
        tag_str = ", ".join(tags) if tags else ""

        frontmatter = (
            "---\n"
            f"created: {meta.get('created_at', now)}\n"
            f"updated: {now}\n"
            f"source: cosmos\n"
        )
        if tag_str:
            frontmatter += f"tags: [{tag_str}]\n"
        if meta.get("agent"):
            frontmatter += f"agent: {meta['agent']}\n"
        if meta.get("host"):
            frontmatter += f"host: {meta['host']}\n"
        if meta.get("task_id"):
            frontmatter += f"task_id: {meta['task_id']}\n"
        if meta.get("status"):
            frontmatter += f"status: {meta['status']}\n"
        frontmatter += "---\n\n"

        return frontmatter + content.strip() + "\n"

    # ── MemoryAdapter API ────────────────────────────────

    def store(self, key: str, content: str, tags: Optional[list[str]] = None,
              metadata: Optional[dict] = None) -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        md = self._build_md(content, tags=tags, metadata=metadata)
        path.write_text(md, encoding="utf-8")
        return key

    def retrieve(self, key: str) -> Optional[MemoryItem]:
        path = self._path_for(key)
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8", errors="replace")
        meta = self._read_frontmatter(path)
        body = self._strip_frontmatter(content)
        tags_str = meta.get("tags", "")
        tags = [t.strip() for t in tags_str.strip("[]").split(",") if t.strip()]
        return MemoryItem(
            key=key,
            content=body,
            source="obsidian",
            tags=tags,
            created_at=meta.get("created", ""),
            score=1.0,
        )

    def search(self, query: str, limit: int = 10) -> list[MemoryItem]:
        """Search .md files via grep/ripgrep."""
        # Try rg (ripgrep) first, fall back to grep
        rg_cmd = ["rg", "-l", "-i", query, str(self.base)]
        try:
            result = subprocess.run(
                rg_cmd, capture_output=True, text=True, timeout=15
            )
            files = [Path(p) for p in result.stdout.strip().split("\n") if p]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback: grep
            try:
                result = subprocess.run(
                    ["grep", "-rl", "-i", query, str(self.base)],
                    capture_output=True, text=True, timeout=15,
                )
                files = [Path(p) for p in result.stdout.strip().split("\n") if p]
            except (subprocess.TimeoutExpired, FileNotFoundError):
                files = []

        items = []
        for path in files[:limit]:
            key = self._key_from_path(path)
            item = self.retrieve(key)
            if item:
                items.append(item)
        return items

    def delete(self, key: str) -> bool:
        path = self._path_for(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def health(self) -> bool:
        return self.base.exists() and self.base.is_dir()

    def list_keys(self, prefix: str = "", limit: int = 50) -> list[str]:
        glob_pattern = f"**/{prefix}*.md" if prefix else "**/*.md"
        files = sorted(self.base.glob(glob_pattern))[:limit]
        return [self._key_from_path(p) for p in files]
