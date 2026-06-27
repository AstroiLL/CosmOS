"""RemoteAgent — runs an agent on a remote host via SSH.

Submits tasks in background (nohup), closes SSH, returns immediately.
Result can be retrieved later via poll_status().
"""

import time
from typing import Optional

from .base import BaseAgent, AgentResult, Capability
from .ssh_runner import SSHRunner, RemoteHostConfig


class RemoteAgent(BaseAgent):
    """Agent adapter that runs another agent CLI on a remote host via SSH.

    The task is submitted via SSH, runs in background (nohup), and the
    SSH connection is closed immediately. Results are polled asynchronously.
    """

    def __init__(
        self,
        name: str,
        host_name: str,
        host_config: RemoteHostConfig,
        agent_command: str = "hermes",
        capabilities: Optional[set[Capability]] = None,
    ):
        super().__init__(
            name=name,
            command=f"ssh://{host_name}/{agent_command}",
            timeout_sec=host_config.timeout_sec,
            capabilities=capabilities or {Capability.SHELL},
        )
        self.host_name = host_name
        self.host_config = host_config
        self.agent_command = agent_command
        self.runner = SSHRunner(host_name, host_config)

    def _build_agent_cmd(self, query: str, workdir: Optional[str] = None) -> str:
        """Build the actual agent CLI command to run on the remote host."""
        cmd_parts = [self.agent_command]

        # For claude, use -p for prompt
        if self.agent_command == "claude":
            escaped = query.replace("'", "'\\''")
            cmd_parts.extend(["-p", f"'{escaped}'"])
        else:
            escaped = query.replace("'", "'\\''")
            cmd_parts.append(f"'{escaped}'")

        if workdir:
            return f"cd {workdir} && {' '.join(cmd_parts)}"
        return " ".join(cmd_parts)

    def check_available(self) -> bool:
        """Check if the remote host is reachable via SSH."""
        return self.runner.check_available()

    def run(self, query: str, workdir: Optional[str] = None) -> AgentResult:
        """Submit task to remote host in background, wait briefly, return.

        The task continues running on the remote host after this returns.
        Use poll_status() to check completion later.
        """
        import uuid
        task_id = str(uuid.uuid4())[:12]
        agent_cmd = self._build_agent_cmd(query, workdir)

        start = time.time()
        err = self.runner.submit(task_id, agent_cmd)
        submit_duration = time.time() - start

        if err:
            return AgentResult(
                success=False,
                error=f"Remote submit failed: {err}",
                duration_sec=submit_duration,
            )

        # Brief verification that the process started
        time.sleep(2)
        status = self.runner.poll(task_id)

        if status.error and not status.running:
            return AgentResult(
                success=False,
                error=f"Remote task failed to start: {status.error}",
                stderr=status.stderr,
                duration_sec=time.time() - start,
            )

        return AgentResult(
            success=True,
            output=f"Task submitted to {self.host_name} ({self.host_config.host}). "
                   f"Remote task ID: {task_id}. Use 'cosmos status' to check result.",
            duration_sec=submit_duration,
            artifacts={
                "remote": True,
                "host": self.host_name,
                "host_address": self.host_config.host,
                "remote_task_id": task_id,
                "agent_cmd": self.agent_command,
                "running": status.running,
            },
        )

    def poll_status(self, remote_task_id: str) -> AgentResult:
        """Poll the status of a previously submitted remote task."""
        status = self.runner.poll(remote_task_id)

        if status.error:
            return AgentResult(
                success=False,
                error=status.error,
                artifacts={"remote": True, "remote_task_id": remote_task_id},
            )

        result = AgentResult(
            success=status.exit_code == 0 if status.completed else True,
            output=status.stdout,
            error=status.stderr or None,
            exit_code=status.exit_code or 0,
            duration_sec=status.duration_sec or 0.0,
            artifacts={
                "remote": True,
                "host": self.host_name,
                "host_address": self.host_config.host,
                "remote_task_id": remote_task_id,
                "running": status.running,
                "completed": status.completed,
            },
        )

        if status.stderr:
            result.verification_details = f"stderr: {status.stderr[:500]}"

        return result

    def cancel_task(self, remote_task_id: str) -> Optional[str]:
        """Cancel a running task on the remote host."""
        return self.runner.cancel(remote_task_id)
