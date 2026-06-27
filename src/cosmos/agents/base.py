"""Base agent adapter interface with capability registry."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Capability(str, Enum):
    """Agent capability types."""
    CODING = "coding"
    RESEARCH = "research"
    AUTOMATION = "automation"
    SHELL = "shell"
    CHAT = "chat"


@dataclass
class AgentResult:
    success: bool
    output: str = ""
    error: Optional[str] = None
    exit_code: int = 0
    duration_sec: float = 0.0
    stderr: str = ""
    artifacts: dict = field(default_factory=dict)
    # Verifier results
    verified: Optional[bool] = None
    verification_details: str = ""


@dataclass
class AgentInfo:
    """Agent metadata for the capability registry."""
    name: str
    command: str
    capabilities: set[Capability]
    available: bool = False
    version: str = ""
    description: str = ""


class BaseAgent(ABC):
    """Abstract base for all agent adapters."""

    def __init__(self, name: str, command: str, timeout_sec: int = 600,
                 capabilities: Optional[set[Capability]] = None):
        self.name = name
        self.command = command
        self.timeout_sec = timeout_sec
        self._capabilities = capabilities or {Capability.SHELL}

    @property
    def capabilities(self) -> set[Capability]:
        return self._capabilities

    def info(self) -> AgentInfo:
        return AgentInfo(
            name=self.name,
            command=self.command,
            capabilities=self.capabilities,
            available=self.check_available(),
        )

    @abstractmethod
    def run(self, query: str, workdir: Optional[str] = None) -> AgentResult:
        """Run a task with the agent. Returns result."""
        ...

    @abstractmethod
    def check_available(self) -> bool:
        """Check if this agent CLI is available on the system."""
        ...

    def __str__(self) -> str:
        return f"Agent({self.name}: {self.command})"
