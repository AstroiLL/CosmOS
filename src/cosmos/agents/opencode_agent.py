"""OpenCode agent adapter — runs opencode CLI for coding tasks."""

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from .base import BaseAgent, AgentResult, Capability


class OpenCodeAgent(BaseAgent):
    """Adapter for OpenCode CLI (`opencode`).

    OpenCode is an autonomous coding agent that edits code files.
    Subcommands: `opencode run <message>` for one-shot, `opencode` for TUI.
    Default model: `opencode/deepseek-v4-flash-free` (free tier).
    """

    def __init__(self, command: str = "opencode", timeout_sec: int = 600,
                 model: Optional[str] = None):
        super().__init__(
            name="opencode", command=command, timeout_sec=timeout_sec,
            capabilities={Capability.CODING, Capability.SHELL},
        )
        self.model = model or "opencode/deepseek-v4-flash-free"

    def run(self, query: str, workdir: Optional[str] = None) -> AgentResult:
        start = time.time()
        resolved_cmd = self._resolve_command()
        if resolved_cmd is None:
            return AgentResult(
                success=False,
                error=("OpenCode CLI not found. "
                       "Install: curl -fsSL https://get.opencode.ai | bash"),
                exit_code=-1,
            )
        try:
            # `opencode run --model <model> <message>` — one-shot coding
            cmd = [resolved_cmd, "run", "--model", self.model, query]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                cwd=workdir or Path.home(),
            )
            duration = time.time() - start
            output = (result.stdout or "")
            stderr = result.stderr.strip() if result.stderr else None
            return AgentResult(
                success=result.returncode == 0,
                output=output.strip(),
                error=stderr if (stderr and result.returncode != 0) else None,
                exit_code=result.returncode,
                duration_sec=duration,
            )
        except subprocess.TimeoutExpired:
            return AgentResult(
                success=False,
                error=f"Timeout after {self.timeout_sec}s",
                exit_code=-1,
                duration_sec=time.time() - start,
            )
        except FileNotFoundError:
            return AgentResult(
                success=False,
                error=f"OpenCode CLI not found: '{resolved_cmd}'.",
                exit_code=-1,
            )
        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                exit_code=-1,
                duration_sec=time.time() - start,
            )

    def _resolve_command(self) -> Optional[str]:
        """Try to find opencode executable via PATH and common locations."""
        # Direct PATH lookup
        if shutil.which(self.command):
            return self.command
        # Common npm global locations
        candidates = [
            Path.home() / ".npm-global/bin/opencode",
            Path.home() / ".npm/bin/opencode",
            Path.home() / "node_modules/.bin/opencode",
            Path("/usr/local/bin/opencode"),
            Path("/usr/bin/opencode"),
            # Custom / OpenCode default install
            Path.home() / ".opencode/bin/opencode",
        ]
        for p in candidates:
            if p.exists() and p.stat().st_mode & 0o111:
                return str(p)
        return None

    def check_available(self) -> bool:
        return self._resolve_command() is not None
