"""Hermes agent adapter — runs hermes CLI with one-shot queries."""

import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from .base import BaseAgent, AgentResult, Capability


class HermesAgent(BaseAgent):
    """Adapter for Hermes Agent CLI (`hermes`)."""

    def __init__(self, command: str = "hermes", timeout_sec: int = 600):
        super().__init__(
            name="hermes", command=command, timeout_sec=timeout_sec,
            capabilities={Capability.RESEARCH, Capability.AUTOMATION,
                          Capability.CHAT, Capability.SHELL},
        )

    def run(self, query: str, workdir: Optional[str] = None) -> AgentResult:
        start = time.time()
        try:
            cmd = [self.command, "chat", "-q", query, "-Q"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                cwd=workdir or Path.home(),
                env=None,  # inherit parent env
            )
            duration = time.time() - start
            if result.returncode == 0:
                return AgentResult(
                    success=True,
                    output=result.stdout.strip(),
                    exit_code=0,
                    duration_sec=duration,
                )
            else:
                return AgentResult(
                    success=False,
                    output=result.stdout.strip(),
                    error=result.stderr.strip() or f"Exit code {result.returncode}",
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
        except FileNotFoundError:
            return AgentResult(
                success=False,
                error=f"Hermes CLI not found: '{self.command}'. Is Hermes installed?",
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
