"""CosmOS config — parses cosmos.yaml with Pydantic."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    command: str = "hermes"
    timeout_sec: int = 600
    enabled: bool = True
    model: Optional[str] = None  # Agent-specific model override (e.g. opencode)


class MemorySQLiteConfig(BaseModel):
    enabled: bool = True
    path: str = "data/cosmos.sqlite"


class MemoryObsidianConfig(BaseModel):
    enabled: bool = True
    vault_path: str = "~/Sync/Obsidian/Mobile"
    notes_folder: str = "CosmOS"


class MemoryConfig(BaseModel):
    sqlite: MemorySQLiteConfig = Field(default_factory=MemorySQLiteConfig)
    obsidian: MemoryObsidianConfig = Field(default_factory=MemoryObsidianConfig)


class ExecutionConfig(BaseModel):
    default_timeout_sec: int = 600
    use_worktrees: bool = True
    verify_results: bool = True
    max_concurrent_tasks: int = 3


class LoggingConfig(BaseModel):
    level: str = "INFO"
    dir: str = "data/logs"
    max_file_size_mb: int = 10
    keep_days: int = 30


class CosmOSConfig(BaseModel):
    name: str = "CosmOS"
    version: str = "0.1.0"
    root: str = "~/Sync/GPT/CosmOS"
    agents: dict[str, AgentConfig] = Field(default_factory=lambda: {
        "hermes": AgentConfig(command="hermes"),
    })
    default_agent: str = "hermes"
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "CosmOSConfig":
        if path is None:
            path = Path.home() / "Sync/GPT/CosmOS/cosmos.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        raw = yaml.safe_load(path.read_text())
        # Merge top-level + nested project block
        data = dict(raw.get("project", {}))
        for key in ("agents", "memory", "execution", "logging"):
            if key in raw:
                data[key] = raw[key]
        if "default" in data.get("agents", {}):
            data["default_agent"] = data["agents"].pop("default")
        return cls(**data)
