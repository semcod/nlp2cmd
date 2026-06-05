# ModelPerformance - extracted from adaptive_learner.py
"""
Adaptive Learning System for LLM Router.

Learns from failures, evolves routing decisions, and self-improves over time.

Features:
- **Failure Pattern Learning**: Detects credit exhaustion, rate limits, timeouts
  and learns to skip failing models automatically.
- **Fallback Evolution**: When a fallback succeeds, it records the pattern so
  future calls route directly to the working model.
- **New Challenge Adaptation**: When encountering new task types or patterns,
  the system learns optimal routing from outcomes.
- **Persistent Memory**: Saves learned patterns to disk for cross-session learning.

Usage:
    learner = AdaptiveLearner()
    learner.record_failure("openrouter/model", "vision", "402 Payment Required")
    learner.record_success("ollama/qwen2.5vl:7b", "vision", latency_ms=1200)
    best = learner.recommend_model("vision")  # → "ollama/qwen2.5vl:7b"
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")
_VERBOSE = os.environ.get("NLP2CMD_ROUTER_VERBOSE", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    if _DEBUG or _VERBOSE:
        print(f"DEBUG [AdaptiveLearner] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------
@dataclass
class ModelPerformance:
    """Tracks performance metrics for a model on a specific task."""
    model: str
    task: str
    total_calls: int = 0
    successes: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0
    last_success: float = 0.0
    last_failure: float = 0.0
    last_error_category: str = ""
    cooldown_until: float = 0.0
    consecutive_failures: int = 0
    learned_preference: float = 0.0  # -1.0 (avoid) to +1.0 (prefer)

    @property
    def success_rate(self) -> float:
        return self.successes / self.total_calls if self.total_calls > 0 else 0.5

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.successes if self.successes > 0 else float("inf")

    @property
    def is_cooled_down(self) -> bool:
        return time.time() >= self.cooldown_until

    @property
    def health_score(self) -> float:
        """Combined health score: success_rate * speed_factor * preference."""
        if not self.is_cooled_down:
            return -1.0
        sr = self.success_rate
        # Speed bonus: models under 500ms get a boost
        speed_factor = min(1.0, 500.0 / max(self.avg_latency_ms, 1.0))
        # Consecutive failure penalty
        fail_penalty = max(0.0, 1.0 - self.consecutive_failures * 0.3)
        # Learned preference (-1 to +1) mapped to (0.0 to 2.0)
        pref_factor = 1.0 + self.learned_preference
        return sr * speed_factor * fail_penalty * pref_factor

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ModelPerformance":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
