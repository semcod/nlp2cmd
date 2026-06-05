# TaskMetric - extracted from metrics.py
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

from nlp2cmd.orchestration.metrics_helpers import _hash_goal

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
@dataclass
class TaskMetric:
    """Metrics for a complete orchestrated task."""
    task_id: str
    goal: str
    goal_hash: str  # for path lookup
    domain: str = "general"
    success: bool = False
    total_duration_ms: float = 0.0
    steps_total: int = 0
    steps_succeeded: int = 0
    steps_failed: int = 0
    steps_repaired: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    llm_calls: int = 0
    plan_source: str = ""  # "llm", "heuristic", "cached_path"
    reflection_verdict: str = ""
    step_metrics: list[dict] = field(default_factory=list)
    generated_functions: list[str] = field(default_factory=list)
    timestamp: str = ""
    decision_path: list[str] = field(default_factory=list)  # action sequence

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.goal_hash:
            self.goal_hash = _hash_goal(self.goal)
