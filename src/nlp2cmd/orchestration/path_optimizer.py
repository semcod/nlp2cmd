# PathOptimizer - extracted from metrics.py
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
from nlp2cmd.orchestration.learned_path import LearnedPath
from nlp2cmd.orchestration.metrics_helpers import _hash_goal
from nlp2cmd.orchestration.task_metric import TaskMetric

class PathOptimizer:
    """Stores successful decision paths for reuse on similar goals.

    When a task succeeds, its step sequence (decision path) is stored
    indexed by goal_hash. Next time a similar goal is requested, the
    cached path can be used instead of LLM planning — saving tokens and latency.
    """

    def __init__(self, workspace: Optional[Path] = None):
        self._ws = workspace or get_workspace()
        self._paths_dir = self._ws / "paths"
        self._paths_dir.mkdir(parents=True, exist_ok=True)
        self._paths_file = self._paths_dir / "learned_paths.json"
        self._cache: Optional[dict[str, LearnedPath]] = None

    def _load(self) -> dict[str, LearnedPath]:
        if self._cache is not None:
            return self._cache
        self._cache = {}
        if self._paths_file.exists():
            try:
                data = json.loads(self._paths_file.read_text(encoding="utf-8"))
                for k, v in data.items():
                    self._cache[k] = LearnedPath(**v)
            except Exception as exc:
                logger.debug("Failed to load learned paths: %s", exc)
        return self._cache

    def _save(self) -> None:
        if self._cache is None:
            return
        try:
            data = {k: asdict(v) for k, v in self._cache.items()}
            self._paths_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8",
            )
        except Exception as exc:
            logger.debug("Failed to save learned paths: %s", exc)

    def lookup(self, goal: str) -> Optional[LearnedPath]:
        """Find a cached path for a similar goal."""
        paths = self._load()
        gh = _hash_goal(goal)
        return paths.get(gh)

    def record_success(self, task: TaskMetric) -> None:
        """Store a successful task's decision path for future reuse."""
        if not task.success or not task.decision_path:
            return

        paths = self._load()
        gh = task.goal_hash

        if gh in paths:
            p = paths[gh]
            p.success_count += 1
            n = p.success_count
            p.avg_duration_ms = (p.avg_duration_ms * (n - 1) + task.total_duration_ms) / n
            p.avg_tokens = int((p.avg_tokens * (n - 1) + task.total_tokens_in + task.total_tokens_out) / n)
            p.last_used = datetime.now(timezone.utc).isoformat()
            if task.generated_functions:
                for fn in task.generated_functions:
                    if fn not in p.generated_functions:
                        p.generated_functions.append(fn)
        else:
            paths[gh] = LearnedPath(
                goal_hash=gh,
                goal_example=task.goal[:200],
                domain=task.domain,
                steps=[sm for sm in task.step_metrics if sm.get("status") == "success"],
                success_count=1,
                avg_duration_ms=task.total_duration_ms,
                avg_tokens=task.total_tokens_in + task.total_tokens_out,
                last_used=datetime.now(timezone.utc).isoformat(),
                generated_functions=list(task.generated_functions),
            )

        self._save()

    def get_stats(self) -> dict:
        """Return statistics about learned paths."""
        paths = self._load()
        return {
            "total_paths": len(paths),
            "total_successes": sum(p.success_count for p in paths.values()),
            "domains": list({p.domain for p in paths.values()}),
        }
