"""Generic shell/CLI adapter — runs any shell command."""

import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from .base import BaseAgent, AgentResult


class ShellAgent(BaseAgent):
    """Adapter that runs a shell command as a task.

    Useful for quick scripts, system commands, or future CLI agents
    that don't have a dedicated adapter yet.
    """

    def __init__(self, command: str = "bash", timeout_sec: int = 600):
        super().__init__(name="shell", command=command, timeout_sec=timeout_sec)

    def run(self, query: str, workdir: Optional[str] = None) -> AgentResult:
        start = time.time()
        try:
            result = subprocess.run(
                query,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                cwd=workdir or Path.home(),
                executable=self.command,
            )
            duration = time.time() - start
            return AgentResult(
                success=result.returncode == 0,
                output=result.stdout.strip(),
                error=result.stderr.strip() if result.stderr else None,
                exit_code=result.returncode,
                duration_sec=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            return AgentResult(
                success=False,
                error=f"Timeout after {self.timeout_sec}s",
                duration_sec=duration,
                exit_code=-1,
            )
        except Exception as e:
            duration = time.time() - start
            return AgentResult(
                success=False,
                error=str(e),
                duration_sec=duration,
                exit_code=-1,
            )

    def check_available(self) -> bool:
        return shutil.which(self.command) is not None
