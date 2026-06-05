"""Re-exports from split metrics.py module."""

from __future__ import annotations

import os
from pathlib import Path

from nlp2cmd.orchestration.function_cache import FunctionCache
from nlp2cmd.orchestration.metrics_helpers import _func_id, _hash_goal
from nlp2cmd.orchestration.generated_function import GeneratedFunction
from nlp2cmd.orchestration.learned_path import LearnedPath
from nlp2cmd.orchestration.metrics_collector import MetricsCollector
from nlp2cmd.orchestration.path_optimizer import PathOptimizer
from nlp2cmd.orchestration.step_metric import StepMetric
from nlp2cmd.orchestration.task_metric import TaskMetric

_WORKSPACE_ENV = "NLP2CMD_CACHE_DIR"
_DEFAULT_WORKSPACE = Path.home() / ".nlp2cmd"


def get_workspace() -> Path:
    """Return the .nlp2cmd workspace directory, creating it if needed."""
    ws = Path(os.environ.get(_WORKSPACE_ENV, str(_DEFAULT_WORKSPACE))).expanduser()
    ws.mkdir(parents=True, exist_ok=True)
    return ws


__all__ = [
    "StepMetric",
    "TaskMetric",
    "LearnedPath",
    "GeneratedFunction",
    "MetricsCollector",
    "PathOptimizer",
    "FunctionCache",
    "get_workspace",
]
