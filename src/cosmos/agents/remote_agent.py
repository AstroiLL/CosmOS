"""RemoteAgent — runs an agent on a remote host via SSH.

Submits tasks in background (nohup), closes SSH, returns immediately.
Result can be retrieved later via poll_status().

Task working directory:
  - If `path` is provided → the agent runs in that directory
  - If not → auto-created ~/.cosmos/<task_id>/
Tracking files (pid, stdout, stderr, exit_status) always go to ~/.cosmos/tasks/<task_id>/
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
        model: Optional[str] = None,
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
        self.model = model
        self.runner = SSHRunner(host_name, host_config)

    def _build_agent_cmd(self, query: str) -> str:
        """Build the actual agent CLI command to run on the remote host.

        NOTE: Does NOT shell-escape the query — that is handled by
        shlex.quote() in SSHRunner.submit(). This method only builds
        the command structure.
        """
        # Build agent-specific command syntax
        if self.agent_command == "claude":
            agent_cmd = f"claude -p {query}"
        elif self.agent_command == "opencode":
            model_flag = f" --model {self.model}" if self.model else ""
            agent_cmd = f"opencode run{model_flag} {query}"
        else:
            # Default: hermes, codex, shell — pass query as positional arg
            agent_cmd = f"{self.agent_command} {query}"

        # Prepend environment if configured
        if self.host_config.shell_env:
            exports = []
            for key, val in self.host_config.shell_env.items():
                # Use double quotes so variables like $PATH get expanded
                exports.append(f"export {key}=\"{val}\"")
            env_exports = " && ".join(exports) + " && "
            return f"{env_exports}{agent_cmd}"

        return agent_cmd

    def check_available(self) -> bool:
        """Check if the remote host is reachable via SSH."""
        return self.runner.check_available()

    def run(self, query: str, workdir: Optional[str] = None) -> AgentResult:
        """Submit task to remote host in background, wait briefly, return.

        The task continues running on the remote host after this returns.
        Use poll_status() to check completion later.

        Args:
            query: The task description / prompt for the agent.
            workdir: Used as `path` — the working directory for the agent
                     on the remote host. If None, ~/.cosmos/<task_id>/ is
                     auto-created.
        """
        import uuid
        task_id = str(uuid.uuid4())[:12]
        agent_cmd = self._build_agent_cmd(query)
        run_dir = workdir  # workdir from BaseAgent signature = run path

        start = time.time()
        err = self.runner.submit(task_id, agent_cmd, run_dir=run_dir)
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

        # Resolve the effective run path using the same logic as submit()
        if run_dir:
            effective_run = run_dir
        else:
            import subprocess as _sp
            home_result = self.runner._run_ssh("echo $HOME", timeout=5)
            remote_home = home_result.stdout.strip() or f"/home/{self.host_config.user}"
            effective_run = f"{remote_home}/.cosmos/{task_id}"

        return AgentResult(
            success=True,
            output=f"Task submitted to {self.host_name} ({self.host_config.host}). "
                   f"Remote task ID: {task_id}. "
                   f"Run path: {effective_run}.",
            duration_sec=submit_duration,
            artifacts={
                "remote": True,
                "host": self.host_name,
                "host_address": self.host_config.host,
                "remote_task_id": task_id,
                "agent_cmd": self.agent_command,
                "run_path": effective_run,
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
