"""Memory adapter interface for CosmOS storage backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class MemoryItem:
    """A single memory entry retrieved from any memory backend."""
    key: str
    content: str
    source: str = ""          # sqlite, obsidian, hermes, etc.
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    score: float = 1.0         # relevance score for search results


class MemoryAdapter(ABC):
    """Abstract base for all memory backends (SQLite, Obsidian, etc.)."""

    @abstractmethod
    def store(self, key: str, content: str, tags: Optional[list[str]] = None,
              metadata: Optional[dict] = None) -> str:
        """Store a value by key. Returns the key."""
        ...

    @abstractmethod
    def retrieve(self, key: str) -> Optional[MemoryItem]:
        """Retrieve a single entry by exact key."""
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[MemoryItem]:
        """Search entries by query text."""
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete an entry by key. Returns True if existed."""
        ...

    @abstractmethod
    def health(self) -> bool:
        """Check if the backend is available."""
        ...

    def list_keys(self, prefix: str = "", limit: int = 50) -> list[str]:
        """List available keys (optional, not all backends support it)."""
        return []
