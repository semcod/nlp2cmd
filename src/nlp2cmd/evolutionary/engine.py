"""Core evolutionary recovery engine."""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Optional

try:
    from rich.console import Console

    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None

from .planner import EvolutionaryRecoveryPlanner
from .store import EvolutionaryKnowledgeStore
from .types import ExecutionMetrics, RecoveryAttempt, RecoveryStrategy


class EvolutionaryRecoveryEngine:
    """Silnik ewolucyjnych napraw - uczy się z każdej sytuacji."""

    def __init__(self, console: Optional[Console] = None, learning_db_path: Optional[Path] = None):
        self.console = console
        self.learning_store = EvolutionaryKnowledgeStore(learning_db_path)
        self.learning_db_path = self.learning_store.learning_db_path
        self.knowledge_base = self.learning_store.knowledge_base
        self.recovery_planner = EvolutionaryRecoveryPlanner(self.learning_store, console)
        self.current_metrics: Optional[ExecutionMetrics] = None

    def _print(self, message: str, style: str = "") -> None:
        if self.console and HAS_RICH:
            self.console.print(message, style=style)
        else:
            print(message)

    async def execute_with_evolutionary_recovery(
        self,
        func: callable,
        context: dict[str, Any],
        max_attempts: int = 5,
    ) -> tuple[bool, Any, ExecutionMetrics]:
        """Główna metoda: wykonaj z ewolucyjnym recovery."""
        metrics = ExecutionMetrics(start_time=time.time())
        self.current_metrics = metrics
        self.recovery_planner.current_metrics = metrics

        result = None
        success = False
        seen_errors: set[str] = set()

        for attempt in range(max_attempts):
            metrics.attempts = attempt + 1

            self._print(f"\n🚀 Attempt {attempt + 1}/{max_attempts}", "bold cyan")

            try:
                result = await func(context)
                success = True
                metrics.success = True
                break
            except Exception as exc:
                error_type = type(exc).__name__
                error_msg = str(exc)

                metrics.error_type = error_type
                metrics.error_message = error_msg

                display_msg = error_msg[:300] + "..." if len(error_msg) > 300 else error_msg
                self._print(f"   ✗ Error: {error_type}: {display_msg}", "red")

                error_key = f"{error_type}:{error_msg[:100]}"
                if error_key in seen_errors:
                    self._print("   ⛔ Same error repeated — stopping retries", "yellow")
                    break
                seen_errors.add(error_key)

                strategy, reasoning, llm_consulted = await self.recovery_planner.plan_strategy(
                    error_type,
                    error_msg,
                    context,
                    attempt,
                    metrics,
                )

                recovery_start = time.time()
                recovery_success, new_context = await self.recovery_planner.execute_recovery(
                    strategy,
                    context,
                    metrics,
                )
                recovery_duration = (time.time() - recovery_start) * 1000

                attempt_record = RecoveryAttempt(
                    timestamp=time.time(),
                    strategy=strategy,
                    context=context.copy(),
                    llm_consulted=llm_consulted,
                    llm_advice=reasoning,
                    success=recovery_success,
                    duration_ms=recovery_duration,
                )
                metrics.recovery_attempts.append(attempt_record)

                if llm_consulted:
                    metrics.llm_calls += 1

                if recovery_success:
                    self._print(f"   ✓ Recovery ({strategy.value}), retrying...", "green")
                    context.update(new_context)
                else:
                    self._print(f"   ⚠ Recovery ({strategy.value}) failed", "yellow")

        metrics.end_time = time.time()
        self.learning_store.record_execution(metrics)
        return success, result, metrics

    def get_learning_report(self) -> dict[str, Any]:
        """Generuje raport uczenia się."""
        return self.learning_store.get_learning_report()
