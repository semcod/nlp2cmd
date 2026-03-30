"""Autonomous example runner built on the evolutionary engine."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console

    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None

from .engine import EvolutionaryRecoveryEngine
from .types import ExecutionMetrics


class AutonomousExampleRunner:
    """Autonomiczny runner z evolutionary recovery."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console
        self.recovery_engine = EvolutionaryRecoveryEngine(console)
        self.execution_history: list[ExecutionMetrics] = []

    def _print(self, message: str, style: str = "") -> None:
        if self.console and HAS_RICH:
            self.console.print(message, style=style)
        else:
            print(message)

    async def run_example(
        self,
        scenario_id: str,
        script_path: Path,
        args: list[str],
        env_setup: dict,
    ) -> tuple[bool, ExecutionMetrics]:
        """Uruchamia przykład z pełnym autonomicznym recovery."""

        async def _execute(context: dict) -> dict:
            """Funkcja wykonywana z retry."""
            python_exe = shutil.which("python3") or sys.executable
            cmd = [python_exe, str(context["script_path"])]

            args = context.get("modified_args", context["args"])
            if context.get("positional_arg"):
                cmd.append(context["positional_arg"])

            cmd.extend(args)

            self._print(f"   Executing: {' '.join(cmd)}", "dim")

            import subprocess

            env = os.environ.copy()
            for key, value in context.get("env_setup", {}).items():
                env[key] = value
            if context.get("skip_hf_hub"):
                env["HF_HUB_OFFLINE"] = "1"

            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(context["script_path"].parent),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                raise RuntimeError("TIMEOUT_ERROR: Script execution exceeded 120s")

            if result.returncode != 0:
                stderr = result.stderr
                stdout = result.stdout
                error_msg = stderr or stdout

                if "No such option" in error_msg:
                    raise ValueError(f"ARG_ERROR: {error_msg}")
                if "ModuleNotFoundError" in error_msg:
                    raise RuntimeError(f"DEPENDENCY_ERROR: {error_msg}")
                if "HF_TOKEN" in error_msg or "huggingface" in error_msg.lower():
                    raise RuntimeError(f"HF_TOKEN_ERROR: {error_msg}")
                if "playwright" in error_msg.lower():
                    raise RuntimeError(f"PLAYWRIGHT_ERROR: {error_msg}")
                raise RuntimeError(f"EXECUTION_ERROR: {error_msg}")

            if result.stdout.strip():
                self._print(result.stdout.strip())

            return {"stdout": result.stdout, "stderr": result.stderr}

        context = {
            "scenario_id": scenario_id,
            "script_path": script_path,
            "args": args,
            "env_setup": env_setup,
        }

        success, result, metrics = await self.recovery_engine.execute_with_evolutionary_recovery(
            _execute,
            context,
            max_attempts=5,
        )

        self.execution_history.append(metrics)

        self._print(f"\n{'=' * 60}", "dim")
        self._print("Execution Summary:", "bold")
        self._print(f"  Attempts: {metrics.attempts}", "cyan")
        self._print(f"  Recovery operations: {metrics.recovery_count}", "cyan")
        self._print(f"  Duration: {metrics.duration_ms:.0f}ms", "cyan")
        self._print(f"  Success: {'✓' if success else '✗'}", "green" if success else "red")

        if metrics.recovery_attempts:
            self._print("\nRecovery strategies used:", "yellow")
            for attempt in metrics.recovery_attempts:
                status = "✓" if attempt.success else "✗"
                self._print(f"  {status} {attempt.strategy.value} ({attempt.duration_ms:.0f}ms)", "dim")

        self._print(f"{'=' * 60}\n", "dim")
        return success, metrics

    def get_learning_report(self) -> dict:
        """Generuje raport uczenia się."""
        if not self.execution_history:
            return {"message": "No executions yet"}

        total = len(self.execution_history)
        successful = sum(1 for metrics in self.execution_history if metrics.success)
        avg_duration = sum(metrics.duration_ms for metrics in self.execution_history) / total
        avg_recoveries = sum(metrics.recovery_count for metrics in self.execution_history) / total

        return {
            "total_executions": total,
            "successful": successful,
            "success_rate": successful / total,
            "avg_duration_ms": avg_duration,
            "avg_recoveries": avg_recoveries,
            "evolution": "System is learning and adapting",
        }
