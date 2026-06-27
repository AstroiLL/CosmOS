"""Claude Code agent adapter — runs claude CLI with one-shot queries."""

import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from .base import BaseAgent, AgentResult, Capability


class ClaudeAgent(BaseAgent):
    """Adapter for Claude Code CLI (`claude`).

    Uses `claude -p "query"` for one-shot non-interactive mode.
    Claude Code is best for high-context implementation and PR work.
    """

    def __init__(self, command: str = "claude", timeout_sec: int = 600,
                 model: Optional[str] = None):
        super().__init__(
            name="claude", command=command, timeout_sec=timeout_sec,
            capabilities={Capability.CODING, Capability.RESEARCH,
                          Capability.CHAT, Capability.SHELL},
        )
        self.model = model

    def run(self, query: str, workdir: Optional[str] = None) -> AgentResult:
        start = time.time()
        if not self.check_available():
            return AgentResult(
                success=False,
                error=f"Claude CLI not found: '{self.command}'. Install: npm install -g @anthropic-ai/claude-code",
                exit_code=-1,
            )
        try:
            cmd = [self.command, "-p", query]
            if self.model:
                cmd.extend(["--model", self.model])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                cwd=workdir or Path.home(),
            )
            duration = time.time() - start
            return AgentResult(
                success=result.returncode == 0,
                output=result.stdout.strip(),
                error=result.stderr.strip() if result.stderr and result.returncode != 0 else None,
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
        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                exit_code=-1,
                duration_sec=time.time() - start,
            )

    def check_available(self) -> bool:
        return shutil.which(self.command) is not None
