"""CosmOS config — parses cosmos.yaml with Pydantic."""

import os
import re
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    command: str = "hermes"
    timeout_sec: int = 600
    enabled: bool = True
    model: Optional[str] = None  # Agent-specific model override (e.g. opencode)


class RemoteHostConfig(BaseModel):
    """SSH host config for remote agent execution."""
    host: str
    user: str
    port: int = 22
    key: str = "~/.ssh/id_ed25519"
    timeout_sec: int = 3600
    agents: list[str] = []  # which agent CLIs are available on this host
    shell_env: dict[str, str] = Field(default_factory=dict)  # extra env vars (e.g. PATH additions)


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


class TelegramConfig(BaseModel):
    """Telegram bot interface config."""
    enabled: bool = False
    bot_token: str = ""
    allowed_user_ids: list[int] = Field(default_factory=list)
    polling_interval: int = 3


class APIConfig(BaseModel):
    """HTTP API interface config."""
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 7455
    api_key: str = ""
    cors_origins: list[str] = Field(default_factory=list)


class CLIConfig(BaseModel):
    """CLI interface config."""
    enabled: bool = True


class WebConfig(BaseModel):
    """Web UI interface config (future)."""
    enabled: bool = False
    port: int = 8401


class InterfacesConfig(BaseModel):
    """All interfaces config block."""
    cli: CLIConfig = Field(default_factory=CLIConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)


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
    remote_hosts: dict[str, RemoteHostConfig] = Field(default_factory=dict)
    interfaces: InterfacesConfig = Field(default_factory=InterfacesConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "CosmOSConfig":
        if path is None:
            path = Path.home() / "Sync/GPT/CosmOS/cosmos.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")

        # Load .env from project root and Hermes secrets
        project_root = path.parent
        dotenv_path = project_root / ".env"
        if dotenv_path.exists():
            load_dotenv(dotenv_path)

        raw_text = path.read_text()
        # Resolve ${VAR} and ${VAR:-default} from environment
        raw_text = cls._resolve_env(raw_text)
        raw = yaml.safe_load(raw_text)
        # Merge top-level + nested project block
        data = dict(raw.get("project", {}))
        for key in ("agents", "remote_hosts", "interfaces", "memory", "execution", "logging"):
            if key in raw:
                value = raw[key]
                # YAML returns None for empty comment-only blocks
                if value is not None:
                    data[key] = value
        if "default" in data.get("agents", {}):
            data["default_agent"] = data["agents"].pop("default")
        return cls(**data)

    @staticmethod
    def _resolve_env(text: str) -> str:
        """Replace ${VAR} and ${VAR:-default} patterns with env values."""

        def _replace(m: re.Match) -> str:
            expr = m.group(1)
            if ":-" in expr:
                var, default = expr.split(":-", 1)
                return os.environ.get(var, default)
            return os.environ.get(expr, "")

        return re.sub(r"\$\{([^}]+)\}", _replace, text)
