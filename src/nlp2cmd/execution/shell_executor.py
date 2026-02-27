"""
Shell command executor — Etap 3 of the NLP refactoring plan.

Extracted from ``pipeline_runner.PipelineRunner._run_shell`` (~120 lines).
Handles: command parsing, safety checks, subprocess execution, and
automatic resource-discovery recovery on failure.
"""

from __future__ import annotations

import logging
import re
import shlex
import subprocess
from typing import Any, Optional

from nlp2cmd.execution.base import BaseExecutor, ExecutorContext, ExecutorResult

log = logging.getLogger(__name__)


class ShellExecutor(BaseExecutor):
    """Execute shell commands with safety checks and error recovery."""

    def __init__(
        self,
        shell_policy: Any = None,
        safety_policy: Any = None,
        max_discovery_attempts: int = 3,
    ) -> None:
        self._shell_policy = shell_policy
        self._safety_policy = safety_policy
        self._max_discovery_attempts = max_discovery_attempts

    @property
    def supported_actions(self) -> list[str]:
        return ["shell", "run_command", "execute"]

    def execute(
        self,
        params: dict[str, Any],
        ctx: ExecutorContext,
    ) -> ExecutorResult:
        """Execute a shell command.

        Expected *params* keys:
          - ``command`` (str): The shell command string.
          - ``cwd`` (str, optional): Working directory.
          - ``timeout_s`` (float, optional): Timeout in seconds (default 15).
        """
        command = str(params.get("command", "")).strip()
        cwd = params.get("cwd")
        timeout_s = float(params.get("timeout_s", 15.0))

        if not command:
            return ExecutorResult(success=False, kind="shell", error="Empty command")

        # Safety policy check
        if self._safety_policy is not None:
            chk = self._check_safety_policy(command)
            if not chk["allowed"]:
                return ExecutorResult(
                    success=False, kind="shell",
                    error=str(chk.get("reason", "Blocked")),
                )
            if chk.get("requires_confirmation") and not ctx.confirm:
                return ExecutorResult(
                    success=False, kind="shell",
                    error="Command requires confirmation",
                    data={"requires_confirmation": True},
                )

        # Shell policy check + parse
        parsed = self._parse_command(command)
        if not parsed["allowed"]:
            return ExecutorResult(
                success=False, kind="shell",
                error=str(parsed.get("reason", "Blocked")),
            )
        if parsed.get("requires_confirmation") and not ctx.confirm:
            return ExecutorResult(
                success=False, kind="shell",
                error="Command requires confirmation",
                data={"requires_confirmation": True},
            )

        argv = parsed.get("argv")
        if not isinstance(argv, list) or not argv:
            return ExecutorResult(success=False, kind="shell", error="Failed to parse command")

        if ctx.dry_run:
            return ExecutorResult(
                success=True, kind="shell",
                data={"argv": argv, "dry_run": True},
            )

        return self._execute_with_recovery(argv, cwd=cwd, timeout_s=timeout_s)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _parse_command(self, command: str) -> dict[str, Any]:
        """Parse and validate a shell command against the shell policy."""
        cmd = command.strip()
        cmd_lower = cmd.lower()
        policy = self._shell_policy

        if policy is not None:
            if not policy.allow_sudo and re.search(r"(^|\s)sudo(\s|$)", cmd_lower):
                return {"allowed": False, "reason": "sudo is not allowed"}

            if not policy.allow_pipes and any(
                op in cmd for op in ["|", ";", "&&", "||", ">", "<"]
            ):
                return {"allowed": False, "reason": "Pipes/redirects/chaining not allowed"}

            if any(x in cmd for x in ["$(`", "`", "$(", "${"]):
                return {"allowed": False, "reason": "Shell expansions not allowed"}

            for pat in policy.blocked_regex:
                if re.search(pat, cmd_lower):
                    return {"allowed": False, "reason": f"Blocked by pattern: {pat}"}

            requires = any(
                re.search(p, cmd_lower)
                for p in policy.require_confirm_regex
            )
        else:
            requires = False

        try:
            argv = shlex.split(cmd)
        except Exception:
            argv = cmd.split()

        if not argv:
            return {"allowed": False, "reason": "Empty command"}

        base = argv[0]
        if policy is not None and policy.allowlist and base not in policy.allowlist:
            return {"allowed": False, "reason": f"Command not in allowlist: {base}"}

        return {"allowed": True, "argv": argv, "requires_confirmation": requires}

    def _check_safety_policy(self, command: str) -> dict[str, Any]:
        """Check command against the global safety policy."""
        policy = self._safety_policy
        cmd_lower = (command or "").lower()

        if not policy.enabled:
            return {"allowed": True, "requires_confirmation": False}

        for pattern in policy.blocked_patterns:
            if str(pattern).lower() in cmd_lower:
                return {
                    "allowed": False,
                    "reason": f"Blocked pattern: {pattern}",
                    "requires_confirmation": False,
                }

        requires = any(
            str(p).lower() in cmd_lower
            for p in policy.require_confirmation_for
        )
        return {"allowed": True, "requires_confirmation": requires}

    def _execute_with_recovery(
        self,
        argv: list[str],
        *,
        cwd: Optional[str],
        timeout_s: float,
    ) -> ExecutorResult:
        """Run subprocess with optional resource-discovery recovery."""
        resource_discovery = self._get_resource_discovery()
        current_argv = list(argv)
        attempts = 0

        while True:
            cp = subprocess.run(
                current_argv,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout_s,
                check=False,
            )

            if cp.returncode == 0:
                return ExecutorResult(
                    success=True, kind="shell",
                    data={
                        "argv": current_argv,
                        "returncode": 0,
                        "stdout": cp.stdout,
                        "stderr": cp.stderr,
                    },
                )

            if resource_discovery and attempts < self._max_discovery_attempts:
                error_output = cp.stderr or ""
                command_str = " ".join(current_argv)
                recovered, new_cmd = resource_discovery.handle_execution_failure(
                    command_str, error_output, attempts,
                )
                if recovered and new_cmd:
                    try:
                        current_argv = shlex.split(new_cmd)
                        attempts += 1
                        continue
                    except Exception:
                        pass

            return ExecutorResult(
                success=False, kind="shell",
                data={
                    "argv": current_argv,
                    "returncode": cp.returncode,
                    "stdout": cp.stdout,
                    "stderr": cp.stderr,
                },
                error=cp.stderr.strip() or f"returncode={cp.returncode}",
            )

    @staticmethod
    def _get_resource_discovery() -> Any:
        """Lazy-load resource discovery manager."""
        try:
            from nlp2cmd.exploration.resource_discovery import (
                get_resource_discovery_manager,
            )
            return get_resource_discovery_manager()
        except Exception:
            return None
