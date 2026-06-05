# StepMetric - extracted from metrics.py
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
@dataclass
class StepMetric:
    """Metrics for a single orchestration step."""
    action: str
    status: str  # "success", "failed", "skipped", "repaired"
    duration_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    llm_model: str = ""
    error: Optional[str] = None
