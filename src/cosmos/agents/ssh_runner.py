"""SSHRunner — submit, poll, cancel tasks on remote hosts via SSH.

Task lifecycle on remote host:
  <workdir>/<task_id>/
    ├── agent_cmd    — the command that was run
    ├── pid          — PID of the background process
    ├── started_at   — ISO timestamp
    ├── stdout       — captured stdout (written live while running)
    ├── stderr       — captured stderr
    └── exit_status  — written when process exits (exit code or -1 if failed)
"""

import json
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import RemoteHostConfig


@dataclass
class RemoteTaskStatus:
    """Status of a task running on a remote host."""
    task_id: str
    host_name: str
    running: bool = True
    completed: bool = False
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    duration_sec: Optional[float] = None
    started_at: Optional[str] = None


class SSHRunner:
    """Submit, poll, and cancel tasks on a remote host through SSH."""

    def __init__(self, host_name: str, config: RemoteHostConfig):
        self.host_name = host_name
        self.config = config
        self._remote_home: str | None = None

    def _get_remote_home(self) -> str:
        """Get the home directory of the remote user (cached)."""
        if self._remote_home is None:
            result = self._run_ssh("echo $HOME", timeout=10)
            home = result.stdout.strip()
            if not home:
                home = f"/home/{self.config.user}"
            self._remote_home = home
        return self._remote_home

    # ── SSH helpers ──────────────────────────────────────

    def _ssh_cmd(self, remote_cmd: str) -> list[str]:
        """Build an SSH command list."""
        cmd = [
            "ssh",
            "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "BatchMode=yes",
            "-p", str(self.config.port),
            "-i", str(Path(self.config.key).expanduser()),
            f"{self.config.user}@{self.config.host}",
            remote_cmd,
        ]
        return cmd

    def _run_ssh(self, remote_cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a command on the remote host and return result."""
        cmd = self._ssh_cmd(remote_cmd)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _tasks_dir(self) -> str:
        """Base directory for task tracking files on the remote host (absolute path)."""
        return f"{self._get_remote_home()}/.cosmos/tasks"

    def _remote_path(self, *parts: str) -> str:
        """Build an absolute remote path under the tasks directory."""
        base = self._tasks_dir()
        return f"{base}/{'/'.join(parts)}"

    def _write_remote_file(self, path: str, content: str) -> subprocess.CompletedProcess:
        """Write content to a remote file via SSH + heredoc.

        Uses quoted heredoc ('ENDOFFILE') so content is taken literally —
        no shell escaping needed.
        """
        remote_cmd = (
            f"mkdir -p {shlex.quote(str(Path(path).parent))}"
            f" && cat > {shlex.quote(path)} << 'ENDOFFILE'\n"
            f"{content}\n"
            f"ENDOFFILE"
        )
        return self._run_ssh(remote_cmd)

    def _read_remote_file(self, path: str) -> Optional[str]:
        """Read a remote file via SSH + cat. Returns None if file doesn't exist."""
        result = self._run_ssh(f"cat {shlex.quote(path)} 2>/dev/null || echo '__NOT_FOUND__'")
        if result.returncode != 0 or result.stdout.strip() == "__NOT_FOUND__":
            return None
        return result.stdout

    # ── Public API ───────────────────────────────────────

    def check_available(self) -> bool:
        """Check if the remote host is reachable via SSH."""
        try:
            result = self._run_ssh("echo 'ok'", timeout=15)
            return result.returncode == 0 and result.stdout.strip() == "ok"
        except (subprocess.TimeoutExpired, OSError):
            return False

    def submit(self, task_id: str, agent_cmd: str,
               run_dir: Optional[str] = None) -> Optional[str]:
        """Submit a task to run in background on the remote host.

        Writes a wrapper script to the remote host, then executes it
        via nohup. This avoids shell quoting issues with env vars and
        complex agent commands.

        Args:
            task_id: Unique task identifier.
            agent_cmd: Command to run (may include cd/env wrappers).
            run_dir: Working directory for the agent on the remote host.
                     If None, defaults to $HOME/.cosmos/<task_id>/.

        Returns an error message if submission failed, None on success.
        """
        task_dir = self._remote_path(task_id)
        started_at = datetime.now(timezone.utc).isoformat()
        effective_run = run_dir or f"{self._get_remote_home()}/.cosmos/{task_id}"

        # Write a wrapper script on the remote host
        wrapper_script = (
            "#!/bin/sh\n"
            f"TASK_DIR={task_dir}\n"
            f"RUN_DIR={effective_run}\n"
            f"AGENT_CMD={agent_cmd}\n"
            "\n"
            f"mkdir -p \"$TASK_DIR\"\n"
            f"echo '{started_at}' > \"$TASK_DIR/started_at\"\n"
            f"echo \"$AGENT_CMD\" > \"$TASK_DIR/agent_cmd\"\n"
            f"echo \"$RUN_DIR\" > \"$TASK_DIR/run_dir\"\n"
            f"echo \"$$\" > \"$TASK_DIR/pid\"\n"
            f"mkdir -p \"$RUN_DIR\"\n"
            f"cd \"$RUN_DIR\"\n"
            f"eval \"$AGENT_CMD\" > \"$TASK_DIR/stdout\" 2> \"$TASK_DIR/stderr\"\n"
            f"echo \"$?\" > \"$TASK_DIR/exit_status\"\n"
        )

        wrapper_path = f"{task_dir}/runner.sh"

        # Step 1: write the wrapper script
        write_result = self._write_remote_file(wrapper_path, wrapper_script)
        if write_result.returncode != 0:
            return f"Failed to write wrapper: {write_result.stderr.strip() or write_result.stdout.strip()}"

        # Step 2: make it executable and run via nohup
        run_cmd = f"chmod +x {wrapper_path} && nohup {wrapper_path} > /dev/null 2>&1 &"
        result = self._run_ssh(run_cmd, timeout=15)
        if result.returncode != 0:
            return f"SSH submit failed: {result.stderr.strip() or result.stdout.strip()}"
        return None

    def poll(self, task_id: str) -> RemoteTaskStatus:
        """Poll the status of a task on the remote host."""
        task_dir = self._remote_path(task_id)
        status = RemoteTaskStatus(
            task_id=task_id,
            host_name=self.host_name,
        )

        # Check if exit_status exists (task completed)
        exit_code_raw = self._read_remote_file(f"{task_dir}/exit_status")
        if exit_code_raw is not None:
            status.completed = True
            status.running = False
            try:
                status.exit_code = int(exit_code_raw.strip())
            except (ValueError, TypeError):
                status.exit_code = -1
        else:
            # Check if pid exists (task still running or was never started)
            pid_raw = self._read_remote_file(f"{task_dir}/pid")
            if pid_raw is None:
                status.running = False
                status.error = "Task not found on remote host"
            else:
                # Check if process is still alive
                pid = pid_raw.strip()
                alive = self._run_ssh(f"kill -0 {shlex.quote(pid)} 2>/dev/null && echo 'alive' || echo 'dead'")
                if alive.stdout.strip() != "alive":
                    status.running = False
                    status.error = "Process died unexpectedly (no exit_status file)"

        # Read stdout/stderr
        stdout = self._read_remote_file(f"{task_dir}/stdout")
        if stdout is not None:
            status.stdout = stdout

        stderr = self._read_remote_file(f"{task_dir}/stderr")
        if stderr is not None:
            status.stderr = stderr

        # Read started_at
        started = self._read_remote_file(f"{task_dir}/started_at")
        if started is not None:
            status.started_at = started.strip()
            try:
                start = datetime.fromisoformat(started.strip())
                status.duration_sec = (datetime.now(timezone.utc) - start).total_seconds()
            except (ValueError, TypeError):
                pass

        return status

    def cancel(self, task_id: str) -> Optional[str]:
        """Cancel a running task on the remote host.

        Returns error message or None on success.
        """
        pid_raw = self._read_remote_file(self._remote_path(task_id, "pid"))
        if pid_raw is None:
            return "Task not found on remote host"

        pid = pid_raw.strip()
        result = self._run_ssh(f"kill {shlex.quote(pid)} 2>&1", timeout=10)
        if result.returncode != 0 and "No such process" not in result.stderr:
            return f"Failed to cancel: {result.stderr.strip()}"

        # Mark as cancelled
        self._run_ssh(f"echo '-1' > {shlex.quote(self._remote_path(task_id, 'exit_status'))}")
        return None

    def cleanup(self, task_id: str) -> Optional[str]:
        """Remove task directory from remote host."""
        task_dir = self._remote_path(task_id)
        result = self._run_ssh(f"rm -rf {shlex.quote(task_dir)}", timeout=10)
        if result.returncode != 0:
            return f"Cleanup failed: {result.stderr.strip()}"
        return None
