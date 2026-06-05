# MetricsCollector - extracted from metrics.py
"""
Metrics collection and decision-path optimization for the Orchestration Engine.

Tracks per-task and per-step execution costs to enable:
1. Cost analysis (LLM tokens, latency, step count, success rate)
2. Decision path learning (store successful paths for reuse)
3. Generated function caching (JS/Python functions for browser/devops automation)

Persistent storage: ~/.nlp2cmd/ (or $NLP2CMD_CACHE_DIR)

Directory layout:
    ~/.nlp2cmd/
    ├── metrics/
    │   ├── tasks.jsonl           # append-only task execution log
    │   └── summary.json          # aggregated statistics
    ├── paths/
    │   └── learned_paths.json    # successful decision paths indexed by goal hash
    ├── generated/
    │   ├── js/                   # cached JS functions (browser automation)
    │   ├── py/                   # cached Python functions (devops/local)
    │   └── index.json            # function index with metadata
    └── config.json               # workspace configuration
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_WORKSPACE_ENV = "NLP2CMD_CACHE_DIR"
_DEFAULT_WORKSPACE = Path.home() / ".nlp2cmd"


def get_workspace() -> Path:
    """Return the .nlp2cmd workspace directory, creating it if needed."""
    ws = Path(os.environ.get(_WORKSPACE_ENV, str(_DEFAULT_WORKSPACE))).expanduser()
    ws.mkdir(parents=True, exist_ok=True)
    return ws


# =====================================================================
# Data classes
# =====================================================================
from nlp2cmd.orchestration.metrics_helpers import _hash_goal
from nlp2cmd.orchestration.step_metric import StepMetric
from nlp2cmd.orchestration.task_metric import TaskMetric

class MetricsCollector:
    """Collects and persists orchestration metrics.

    Usage:
        mc = MetricsCollector()
        mc.start_task("fibonacci in python", domain="code_editor")
        mc.record_step("generate_code", "success", duration_ms=1200, tokens_out=500)
        mc.record_step("inject_code", "success", duration_ms=50)
        mc.finish_task(success=True, reflection_verdict="valid")
        summary = mc.get_summary()
    """

    def __init__(self, workspace: Optional[Path] = None):
        self._ws = workspace or get_workspace()
        self._metrics_dir = self._ws / "metrics"
        self._metrics_dir.mkdir(parents=True, exist_ok=True)
        self._tasks_file = self._metrics_dir / "tasks.jsonl"
        self._summary_file = self._metrics_dir / "summary.json"

        # Current task being tracked
        self._current: Optional[TaskMetric] = None
        self._task_start: float = 0.0
        self._step_start: float = 0.0

    def start_task(self, goal: str, domain: str = "general",
                   task_id: Optional[str] = None) -> str:
        """Begin tracking a new task."""
        tid = task_id or f"task_{int(time.time() * 1000)}"
        self._current = TaskMetric(
            task_id=tid,
            goal=goal,
            goal_hash=_hash_goal(goal),
            domain=domain,
        )
        self._task_start = time.time()
        return tid

    def record_step(
        self,
        action: str,
        status: str,
        duration_ms: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        llm_model: str = "",
        error: Optional[str] = None,
    ) -> None:
        """Record metrics for one step."""
        if not self._current:
            return

        sm = StepMetric(
            action=action,
            status=status,
            duration_ms=duration_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            llm_model=llm_model,
            error=error,
        )
        self._current.step_metrics.append(asdict(sm))
        self._current.decision_path.append(action)
        self._current.llm_calls += (1 if tokens_out > 0 else 0)
        self._current.total_tokens_in += tokens_in
        self._current.total_tokens_out += tokens_out

        if status == "success":
            self._current.steps_succeeded += 1
        elif status == "failed":
            self._current.steps_failed += 1
        elif status == "repaired":
            self._current.steps_repaired += 1
        self._current.steps_total += 1

    def record_generated_function(self, func_id: str) -> None:
        """Record that a function was generated during this task."""
        if self._current:
            self._current.generated_functions.append(func_id)

    def finish_task(
        self,
        success: bool,
        reflection_verdict: str = "",
        plan_source: str = "",
    ) -> TaskMetric:
        """Finish tracking and persist the task metrics."""
        if not self._current:
            raise RuntimeError("No task in progress")

        self._current.success = success
        self._current.total_duration_ms = (time.time() - self._task_start) * 1000
        self._current.reflection_verdict = reflection_verdict
        self._current.plan_source = plan_source

        # Append to JSONL log
        try:
            with open(self._tasks_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(self._current), ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.debug("Failed to write task metric: %s", exc)

        # Update summary
        self._update_summary(self._current)

        result = self._current
        self._current = None
        return result

    def get_summary(self) -> dict:
        """Load aggregated summary statistics."""
        if self._summary_file.exists():
            try:
                return json.loads(self._summary_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self._empty_summary()

    def get_recent_tasks(self, n: int = 20) -> list[dict]:
        """Load last N task metrics from the JSONL log."""
        if not self._tasks_file.exists():
            return []
        tasks = []
        try:
            for line in self._tasks_file.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    tasks.append(json.loads(line))
        except Exception:
            pass
        return tasks[-n:]

    # ── Private ──────────────────────────────────────────────────────

    def _update_summary(self, task: TaskMetric) -> None:
        summary = self.get_summary()
        summary["total_tasks"] += 1
        if task.success:
            summary["successful_tasks"] += 1
        else:
            summary["failed_tasks"] += 1
        summary["total_tokens_in"] += task.total_tokens_in
        summary["total_tokens_out"] += task.total_tokens_out
        summary["total_llm_calls"] += task.llm_calls
        summary["total_duration_ms"] += task.total_duration_ms
        summary["total_steps"] += task.steps_total
        summary["total_repairs"] += task.steps_repaired

        # Running averages
        n = summary["total_tasks"]
        summary["avg_duration_ms"] = summary["total_duration_ms"] / n
        summary["avg_tokens_per_task"] = (
            (summary["total_tokens_in"] + summary["total_tokens_out"]) / n
        )
        summary["success_rate"] = summary["successful_tasks"] / n

        # Per-domain stats
        domain = task.domain
        ds = summary.setdefault("domains", {}).setdefault(domain, {
            "tasks": 0, "success": 0, "avg_ms": 0.0, "total_ms": 0.0,
        })
        ds["tasks"] += 1
        if task.success:
            ds["success"] += 1
        ds["total_ms"] += task.total_duration_ms
        ds["avg_ms"] = ds["total_ms"] / ds["tasks"]

        summary["last_updated"] = datetime.now(timezone.utc).isoformat()

        try:
            self._summary_file.write_text(
                json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8",
            )
        except Exception as exc:
            logger.debug("Failed to write summary: %s", exc)

    @staticmethod
    def _empty_summary() -> dict:
        return {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_llm_calls": 0,
            "total_duration_ms": 0.0,
            "total_steps": 0,
            "total_repairs": 0,
            "avg_duration_ms": 0.0,
            "avg_tokens_per_task": 0.0,
            "success_rate": 0.0,
            "domains": {},
            "last_updated": "",
        }
