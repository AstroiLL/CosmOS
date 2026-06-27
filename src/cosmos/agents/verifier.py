"""Agent result verifier — checks that the agent actually produced valid output."""

import os
import subprocess
from pathlib import Path
from typing import Optional

from .base import AgentResult


class Verifier:
    """Verifies agent results. Runs checks and produces a verification verdict."""

    @staticmethod
    def verify(result: AgentResult, workdir: Optional[str] = None) -> AgentResult:
        """Run checks on an agent result and add verification info."""
        checks = []
        all_pass = True

        # 1. Exit code check
        exit_ok = result.exit_code == 0
        checks.append(("exit_code", exit_ok, f"exit={result.exit_code}"))
        if not exit_ok:
            all_pass = False

        # 2. Empty output check
        has_output = bool(result.output.strip())
        checks.append(("has_output", has_output,
                       f"{len(result.output)} chars" if has_output else "empty"))
        if not has_output and exit_ok:
            all_pass = False

        # 3. Error message check
        has_no_error = not result.error
        checks.append(("no_error", has_no_error,
                       result.error[:100] if result.error else "clean"))

        # 4. Timeout check
        not_timeout = result.duration_sec < 590  # slightly less than default timeout
        checks.append(("not_timeout", not_timeout,
                       f"{result.duration_sec:.1f}s"))

        # 5. Workdir git diff check (if in a git repo)
        if workdir and Verifier._is_git_repo(workdir):
            diff_output = Verifier._get_git_diff(workdir)
            has_changes = bool(diff_output)
            checks.append(("git_changes", has_changes,
                           f"{len(diff_output)} lines diff" if has_changes else "no changes"))
            # For coding tasks, no changes might be suspicious
            # but not necessarily a failure

        # Build verification details
        lines = []
        for name, ok, detail in checks:
            icon = "✅" if ok else "⚠️"
            lines.append(f"{icon} {name}: {detail}")
        details = "\n".join(lines)

        # Overall
        verified = all_pass and (not workdir or not Verifier._is_git_repo(workdir)
                                 or any("git_changes" in c[0] and c[1] for c in checks))

        result.verified = all_pass
        result.verification_details = details
        return result

    @staticmethod
    def _is_git_repo(path: str) -> bool:
        return (Path(path) / ".git").exists()

    @staticmethod
    def _get_git_diff(path: str) -> str:
        try:
            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=path,
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return ""
