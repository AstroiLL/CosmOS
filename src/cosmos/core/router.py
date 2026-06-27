"""Task router — maps tasks to the right agent with capability registry.

Supports local and remote (SSH) agents. Remote tasks are submitted in
background and can be polled later.
"""

import json
from pathlib import Path
from typing import Optional

from ..config import CosmOSConfig
from ..core.state import TaskStore
from ..agents.base import AgentResult, BaseAgent, Capability, AgentInfo
from ..agents.hermes_agent import HermesAgent
from ..agents.shell_agent import ShellAgent
from ..agents.claude_agent import ClaudeAgent
from ..agents.opencode_agent import OpenCodeAgent
from ..agents.remote_agent import RemoteAgent
from ..agents.worktree import WorktreeManager
from ..agents.verifier import Verifier


class TaskRouter:
    """Routes a task description to the appropriate agent — local or remote."""

    def __init__(self, config: CosmOSConfig, store: TaskStore):
        self.config = config
        self.store = store
        self.agents: dict[str, BaseAgent] = {}
        self.remote_agents: dict[str, RemoteAgent] = {}
        self._init_agents()

    def _init_agents(self):
        """Initialise available agents from config — local and remote."""
        ac = self.config.agents
        # Local agents
        if "hermes" in ac and ac["hermes"].enabled:
            self.agents["hermes"] = HermesAgent(
                command=ac["hermes"].command,
                timeout_sec=ac["hermes"].timeout_sec,
            )
        if "claude" in ac and ac["claude"].enabled:
            self.agents["claude"] = ClaudeAgent(
                command=ac["claude"].command,
                timeout_sec=ac["claude"].timeout_sec,
                model=ac["claude"].model,
            )
        if "opencode" in ac and ac["opencode"].enabled:
            self.agents["opencode"] = OpenCodeAgent(
                command=ac["opencode"].command,
                timeout_sec=ac["opencode"].timeout_sec,
                model=ac["opencode"].model or "opencode/deepseek-v4-flash-free",
            )

        # Remote agents (one per host × each declared agent CLI)
        for host_name, host_cfg in self.config.remote_hosts.items():
            agent_list = host_cfg.agents or ["hermes", "claude", "opencode"]
            for agent_cli in agent_list:
                if agent_cli not in ac or not ac[agent_cli].enabled:
                    continue
                remote_name = f"{host_name}/{agent_cli}"
                remote = RemoteAgent(
                    name=remote_name,
                    host_name=host_name,
                    host_config=host_cfg,
                    agent_command=agent_cli,
                    capabilities=self._get_remote_capabilities(agent_cli),
                )
                self.agents[remote_name] = remote
                self.remote_agents[remote_name] = remote

    @staticmethod
    def _get_remote_capabilities(agent_cli: str) -> set[Capability]:
        """Map a CLI name to capabilities (same as local agents)."""
        mapping = {
            "hermes": {Capability.AUTOMATION, Capability.RESEARCH, Capability.SHELL},
            "claude": {Capability.CODING, Capability.RESEARCH, Capability.CHAT},
            "opencode": {Capability.CODING, Capability.SHELL, Capability.RESEARCH},
            "codex": {Capability.CODING, Capability.RESEARCH},
        }
        return mapping.get(agent_cli, {Capability.SHELL})

    def get_agent(self, agent_name: Optional[str] = None,
                  host: Optional[str] = None,
                  required_capability: Optional[Capability] = None) -> BaseAgent:
        """Resolve agent by name, host, or capability.

        Priority:
          1. Exact name match
          2. host/agent_name (remote)
          3. Capability match (checks local first, then remote)
          4. Fallback chain
        """
        name = agent_name or self.config.default_agent

        # 1. Exact match by name
        if name in self.agents and self.agents[name].check_available():
            return self.agents[name]

        # 2. Host + agent name → remote
        if host:
            # Try remote names that match host
            for rname, ragent in self.remote_agents.items():
                if rname.startswith(f"{host}/"):
                    if agent_name and not rname.endswith(f"/{agent_name}"):
                        continue
                    if ragent.check_available():
                        return ragent
            # Try the host directly as a remote-runner name
            remote_key = f"{host}/{agent_name or 'hermes'}"
            if remote_key in self.remote_agents and self.remote_agents[remote_key].check_available():
                return self.remote_agents[remote_key]

        # 3. Capability match (local first, then remote)
        if required_capability:
            for agent in self.agents.values():
                if agent.check_available() and required_capability in agent.capabilities:
                    return agent
            # Also check remote agents
            for agent in self.remote_agents.values():
                if agent.check_available() and required_capability in agent.capabilities:
                    return agent

        # 4. Fallback chain
        for fallback in ("hermes",):
            if fallback in self.agents and self.agents[fallback].check_available():
                return self.agents[fallback]

        # Last resort
        return ShellAgent()

    def list_agents(self) -> list[AgentInfo]:
        """List all registered agents with availability and capabilities."""
        results = []
        for agent in self.agents.values():
            info = agent.info()
            # Annotate remote agents
            if agent.name in self.remote_agents:
                ra = self.remote_agents[agent.name]
                info.description = f"Remote on {ra.host_name} ({ra.host_config.host})"
            results.append(info)
        # Add shell as always available
        results.append(AgentInfo(
            name="shell", command="bash",
            capabilities={Capability.SHELL},
            available=True,
            description="Generic shell command executor",
        ))
        return results

    def run_task(self, description: str, agent_name: Optional[str] = None,
                 host: Optional[str] = None,
                 workdir: Optional[str] = None,
                 metadata: Optional[dict] = None) -> dict:
        """Create a task and run it. For remote hosts, submits in background.

        Returns task dict with remote status info if applicable.
        """
        # Determine agent
        agent = self.get_agent(agent_name, host=host)

        # Create task in store
        task_metadata = {
            **(metadata or {}),
            "workdir": workdir or "",
        }
        task_id = self.store.create_task(
            description=description,
            agent=agent.name,
            metadata=task_metadata,
        )

        # Remote agent: submit in background, don't wait
        if agent.name in self.remote_agents:
            remote_agent = self.remote_agents[agent.name]
            self.store.update_task(task_id, status="running")
            result: AgentResult = remote_agent.run(description, workdir=workdir)

            if result.success and result.artifacts.get("remote_task_id"):
                # Store remote info in metadata
                remote_id = result.artifacts["remote_task_id"]
                self.store.update_task(
                    task_id, status="running",
                    result=result.output,
                    metadata={
                        **task_metadata,
                        "remote": True,
                        "remote_host": remote_agent.host_name,
                        "remote_host_address": remote_agent.host_config.host,
                        "remote_task_id": remote_id,
                    },
                )
            else:
                self.store.update_task(
                    task_id, status="failed",
                    result=result.output, error=result.error,
                )

            task = self.store.get_task(task_id)
            task["duration_sec"] = round(result.duration_sec, 1)
            return task

        # ── Local agent: run synchronously ──────────────

        # Determine if we need worktree isolation
        effective_workdir = workdir
        needs_worktree = (Capability.CODING in agent.capabilities
                          and not workdir)
        wm = None
        if needs_worktree and self.config.execution.use_worktrees:
            base = Path.cwd()
            for _ in range(3):
                if WorktreeManager.is_git_repo(base):
                    wm = WorktreeManager(base)
                    wt = wm.create()
                    if wt:
                        effective_workdir = str(wt)
                    break
                parent = base.parent
                if parent == base:
                    break
                base = parent

        # Mark running
        self.store.update_task(task_id, status="running")

        # Execute
        result: AgentResult = agent.run(description, workdir=effective_workdir)

        # Verify (if enabled)
        if self.config.execution.verify_results:
            result = Verifier.verify(result, workdir=effective_workdir)

        # Save result
        if result.success:
            self.store.update_task(
                task_id, status="completed",
                result=result.output,
            )
        else:
            self.store.update_task(
                task_id, status="failed",
                result=result.output, error=result.error,
            )

        # Store verification in metadata
        if result.verified is not None:
            self.store._conn.execute(
                "UPDATE tasks SET metadata = ? WHERE id = ?",
                (json.dumps({
                    "verified": result.verified,
                    "verification": result.verification_details,
                }), task_id),
            )
            self.store._conn.commit()

        # Cleanup worktree
        if wm and effective_workdir:
            wm.remove(effective_workdir)

        # Return full task
        task = self.store.get_task(task_id)
        task["duration_sec"] = round(result.duration_sec, 1)
        if result.verified is not None:
            task["verified"] = result.verified
            task["verification"] = result.verification_details
        return task

    def poll_remote_task(self, task_id: str) -> Optional[dict]:
        """Poll a remote task and update local store if completed.

        Returns updated task dict or None if task is not remote.
        """
        task = self.store.get_task(task_id)
        if not task:
            return None

        meta = task.get("metadata") or {}
        if not meta.get("remote"):
            return task  # Not a remote task

        remote_task_id = meta.get("remote_task_id")
        host_name = meta.get("remote_host")
        if not remote_task_id or not host_name:
            return task

        remote_key = f"{host_name}/{meta.get('agent_type', '')}"
        # Find the remote agent by host name
        remote_agent = None
        for name, agent in self.remote_agents.items():
            if agent.host_name == host_name:
                remote_agent = agent
                break

        if not remote_agent:
            return task

        # Try the remote task ID directly
        result = remote_agent.poll_status(remote_task_id)

        if result.artifacts.get("completed"):
            if result.success:
                self.store.update_task(
                    task_id, status="completed",
                    result=result.output or task.get("result", ""),
                )
            else:
                error_msg = result.error or result.stderr or "Remote task failed"
                self.store.update_task(
                    task_id, status="failed",
                    result=result.output, error=error_msg,
                )
            return self.store.get_task(task_id)

        # Still running — update with partial output
        if result.output:
            self.store.update_task(task_id, result=result.output[:2000])
        return self.store.get_task(task_id)
