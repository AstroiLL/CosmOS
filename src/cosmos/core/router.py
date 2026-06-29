"""Task router — maps tasks to the right agent with capability registry.

Supports local and remote (SSH) agents. Remote tasks are submitted in
background and can be polled later.
"""

import json
import time
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

    def __init__(self, config: CosmOSConfig, store: TaskStore,
                 memory_stores: Optional[dict] = None):
        self.config = config
        self.store = store
        self.memory_stores = memory_stores or {}
        self.agents: dict[str, BaseAgent] = {}
        self.remote_agents: dict[str, RemoteAgent] = {}
        self._agent_info_cache: list[AgentInfo] | None = None
        self._agent_info_cache_time: float = 0.0
        self._init_agents()
        # Pre-populate cache with all-true availability to avoid SSH delays on first load
        self._prefill_cache()

    def _prefill_cache(self):
        """Build initial cache: mark all agents as available (optimistic).
        First real list_agents() call will update actual availability."""
        results = []
        for agent in self.agents.values():
            results.append(AgentInfo(
                name=agent.name,
                command=agent.command,
                capabilities=agent.capabilities,
                available=True,  # optimistic
            ))
        # Annotate remote hosts
        for name, ra in self.remote_agents.items():
            for r in results:
                if r.name == name:
                    r.description = f"Remote on {ra.host_name} ({ra.host_config.host})"
        # Add shell
        results.append(AgentInfo(
            name="shell", command="bash",
            capabilities={Capability.SHELL},
            available=True,
            description="Generic shell command executor",
        ))
        self._agent_info_cache = results
        self._agent_info_cache_time = time.time()

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
                    model=ac[agent_cli].model,
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
          1. If host is given → remote agent matching host+agent_name
          2. Exact name match (local, only if no host specified)
          3. Capability match (local, then remote)
          4. Fallback chain
        """
        name = agent_name or self.config.default_agent

        # 1. If host specified → resolve remote first
        if host:
            for rname, ragent in self.remote_agents.items():
                if rname.startswith(f"{host}/"):
                    if agent_name and not rname.endswith(f"/{agent_name}"):
                        continue
                    if ragent.check_available():
                        return ragent
            remote_key = f"{host}/{agent_name or self.config.default_agent}"
            if remote_key in self.remote_agents and self.remote_agents[remote_key].check_available():
                return self.remote_agents[remote_key]

        # 2. Exact match by name (local only)
        if not host and name in self.agents and self.agents[name].check_available():
            return self.agents[name]

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
        """List all registered agents with capabilities.
        Returns cached data — all agents shown as available (optimistic).
        Real SSH availability is checked only in doctor() endpoint."""
        if self._agent_info_cache is not None:
            return self._agent_info_cache
        # Fallback: should never happen (prefilled at init), but just in case
        return [AgentInfo(
            name="hermes", command="hermes",
            capabilities={Capability.SHELL},
            available=True,
            description="No data yet",
        )]

    def run_task(self, description: str, agent_name: Optional[str] = None,
                 host: Optional[str] = None,
                 workdir: Optional[str] = None,
                 path: Optional[str] = None,
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
            # Use path if provided, otherwise workdir for remote run directory
            remote_run_dir = path or workdir
            result: AgentResult = remote_agent.run(description, workdir=remote_run_dir)

            if result.success and result.artifacts.get("remote_task_id"):
                # Store remote info in metadata
                remote_id = result.artifacts["remote_task_id"]
                effective_run = result.artifacts.get("run_path", remote_run_dir or f"~/.cosmos/{task_id}")

                # Check if the task completed during the initial poll
                already_completed = result.artifacts.get("completed", False)
                task_status = "completed" if (already_completed and result.success) else \
                              "failed" if (already_completed and not result.success) else \
                              "running"

                self.store.update_task(
                    task_id, status=task_status,
                    result=result.output or None,
                    metadata={
                        **task_metadata,
                        "remote": True,
                        "remote_host": remote_agent.host_name,
                        "remote_host_address": remote_agent.host_config.host,
                        "remote_task_id": remote_id,
                        "run_path": effective_run,
                    },
                )
                if task_status == "failed":
                    self.store.update_task(task_id, error=result.error or result.stderr or "Remote task failed")
            else:
                self.store.update_task(
                    task_id, status="failed",
                    result=result.output, error=result.error,
                )

            # Save to memory (only for completed/failed remote tasks)
            if result.artifacts.get("completed", False):
                self._save_to_memory(task_id, description, result, agent.name)

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

        # Save to memory
        self._save_to_memory(task_id, description, result, agent.name)

        # Return full task
        task = self.store.get_task(task_id)
        task["duration_sec"] = round(result.duration_sec, 1)
        if result.verified is not None:
            task["verified"] = result.verified
            task["verification"] = result.verification_details
        return task

    def _save_to_memory(self, task_id: str, description: str,
                        result: "AgentResult", agent_name: str):
        """Save task result to all active memory backends."""
        if not self.memory_stores:
            return

        # Build content
        status = "completed" if result.success else "failed"
        meta = getattr(result, 'artifacts', {}) or {}
        host = meta.get("host", meta.get("remote_host", ""))
        host_info = f" на {host}" if host else ""

        md_content = (
            f"## {description}\n\n"
            f"- **Статус:** {status}\n"
            f"- **Агент:** {agent_name}{host_info}\n"
            f"- **Время:** {result.duration_sec:.1f}с\n"
            f"- **ID:** {task_id}\n\n"
        )
        if result.output:
            md_content += "### Результат\n\n```\n" + result.output[:2000] + "\n```\n\n"
        if result.error:
            md_content += "### Ошибка\n\n```\n" + result.error[:500] + "\n```\n"
        if result.stderr:
            md_content += "### stderr\n\n```\n" + result.stderr[:500] + "\n```\n"

        tags = ["cosmos", agent_name.split("/")[0]]
        if host:
            tags.append(host)
        if not result.success:
            tags.append("failed")

        task_key = f"Tasks/{task_id}"
        try:
            for store in self.memory_stores.values():
                store.store(task_key, md_content, tags=tags, metadata={
                    "agent": agent_name,
                    "host": host,
                    "task_id": task_id,
                    "status": status,
                })
        except Exception:
            pass  # Memory write failure shouldn't break the task flow

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
