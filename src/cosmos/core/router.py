"""Task router — maps tasks to the right agent with capability registry."""

from pathlib import Path
from typing import Optional

from ..config import CosmOSConfig
from ..core.state import TaskStore
from ..agents.base import AgentResult, BaseAgent, Capability, AgentInfo
from ..agents.hermes_agent import HermesAgent
from ..agents.shell_agent import ShellAgent
from ..agents.claude_agent import ClaudeAgent
from ..agents.opencode_agent import OpenCodeAgent
from ..agents.worktree import WorktreeManager
from ..agents.verifier import Verifier


class TaskRouter:
    """Routes a task description to the appropriate agent."""

    def __init__(self, config: CosmOSConfig, store: TaskStore):
        self.config = config
        self.store = store
        self.agents: dict[str, BaseAgent] = {}
        self._init_agents()

    def _init_agents(self):
        """Initialise available agents from config."""
        ac = self.config.agents
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

    def get_agent(self, agent_name: Optional[str] = None,
                  required_capability: Optional[Capability] = None) -> BaseAgent:
        """Resolve agent by name or capability. Falls back to default."""
        name = agent_name or self.config.default_agent

        # Exact match by name
        if name in self.agents and self.agents[name].check_available():
            return self.agents[name]

        # Match by capability
        if required_capability:
            for agent in self.agents.values():
                if agent.check_available() and required_capability in agent.capabilities:
                    return agent

        # Fallback chain
        for fallback in ("hermes",):
            if fallback in self.agents and self.agents[fallback].check_available():
                return self.agents[fallback]

        # Last resort
        return ShellAgent()

    def list_agents(self) -> list[AgentInfo]:
        """List all registered agents with availability and capabilities."""
        results = []
        for agent in self.agents.values():
            results.append(agent.info())
        # Also add shell as always available
        results.append(AgentInfo(
            name="shell", command="bash",
            capabilities={Capability.SHELL},
            available=True,
            description="Generic shell command executor",
        ))
        return results

    def run_task(self, description: str, agent_name: Optional[str] = None,
                 workdir: Optional[str] = None,
                 metadata: Optional[dict] = None) -> dict:
        """Create a task, run it, verify, save result. Returns task dict."""
        # Determine agent
        agent = self.get_agent(agent_name)

        # Determine if we need worktree isolation
        effective_workdir = workdir
        needs_worktree = (Capability.CODING in agent.capabilities
                          and not workdir)
        wm = None
        if needs_worktree and self.config.execution.use_worktrees:
            # Try to find a git repo in current or parent dirs
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

        # Create task in store
        task_id = self.store.create_task(
            description=description,
            agent=agent.name,
            metadata={
                **(metadata or {}),
                "workdir": effective_workdir or "",
                "expected_capabilities": [c.value for c in agent.capabilities],
            },
        )

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

        # Store verification in a separate metadata update if needed
        if result.verified is not None:
            import json
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
