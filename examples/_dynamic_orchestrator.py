"""
Dynamic Orchestrator — thin wrapper around nlp2cmd.orchestration.

This module provides backward-compatible imports for example scripts.
The actual implementation is in src/nlp2cmd/orchestration/.

Usage:
    from _dynamic_orchestrator import DynamicOrchestrator

    orch = DynamicOrchestrator(verbose=True)
    result = await orch.execute_task("write fibonacci in python", page)
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Optional

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nlp2cmd.orchestration import (
    Orchestrator,
    TaskResult,
    StepResult as _CoreStepResult,
    StepDef,
    TaskSchema,
    register_default_handlers,
    MetricsCollector,
    FunctionCache,
)
from nlp2cmd.orchestration.engine import StepStatus

try:
    from _verbose_helper import vlog, vlog_decision, dump_page_schema, init_verbose
except ImportError:
    def vlog(msg, indent=0): pass
    def vlog_decision(decision, reason=""): pass
    async def dump_page_schema(page): pass
    def init_verbose(enabled): pass


class DynamicOrchestrator:
    """Backward-compatible wrapper around nlp2cmd.orchestration.Orchestrator.

    Provides the same API as the old 1191-line version but delegates
    to the core module for all logic.
    """

    def __init__(self, verbose: bool = False, max_step_retries: int = 2):
        self.verbose = verbose
        self._orch = Orchestrator(enable_metrics=True)
        register_default_handlers(self._orch)

    async def execute_task(self, prompt: str, page) -> dict:
        """Execute a task on a Playwright page.

        Args:
            prompt: Natural language task description.
            page: Playwright Page object.

        Returns:
            dict with success, context, validation, results.
        """
        t0 = time.time()

        print(f"\n{'═' * 60}")
        print(f"  Dynamic Orchestrator (core module)")
        print(f"  Prompt: {prompt}")
        print(f"{'═' * 60}")

        result = await self._orch.run(prompt, context={"page": page})

        elapsed = time.time() - t0
        success = result.success

        print(f"\n{'═' * 60}")
        if success:
            print(f"  ✓ Task completed successfully")
        else:
            print(f"  ✗ Task failed: {result.error or 'see reflection'}")
        print(f"  Steps: {result.steps_executed}/{result.steps_total}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"{'═' * 60}")

        return {
            "success": success,
            "validation_passed": success,
            "validation": {
                "reason": result.reflection.reason if result.reflection else "",
            },
            "context": result.context,
            "results": [],
        }
