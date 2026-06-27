"""Git worktree isolation for coding tasks.

Creates a disposable git worktree so agent edits don't touch the main branch.
"""

import subprocess
import uuid
from pathlib import Path
from typing import Optional


class WorktreeManager:
    """Manages disposable git worktrees for isolated agent tasks."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir).resolve()

    def create(self, branch_name: Optional[str] = None) -> Optional[Path]:
        """Create a temporary worktree. Returns path or None on failure."""
        if not (self.base_dir / ".git").exists():
            # Not a git repository — can't create worktree
            return None
        name = branch_name or f"cosmos-task-{uuid.uuid4().hex[:8]}"
        worktree_path = self.base_dir.parent / f".worktrees/{name}"
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), "HEAD", "-b", name],
                cwd=self.base_dir,
                capture_output=True, text=True, timeout=30,
                check=True,
            )
            return worktree_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError):
            return None

    def remove(self, worktree_path: str | Path) -> bool:
        """Remove a worktree. Returns True on success."""
        path = Path(worktree_path)
        try:
            # Get branch name
            result = subprocess.run(
                ["git", "branch", "--list", f"--list", f"*/{path.name}"],
                cwd=self.base_dir,
                capture_output=True, text=True, timeout=10,
            )
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(path)],
                cwd=self.base_dir,
                capture_output=True, timeout=15,
                check=True,
            )
            # Clean up branch
            branch = path.name
            subprocess.run(
                ["git", "branch", "-D", branch],
                cwd=self.base_dir,
                capture_output=True, timeout=10,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def is_git_repo(path: str | Path) -> bool:
        return (Path(path) / ".git").exists()
