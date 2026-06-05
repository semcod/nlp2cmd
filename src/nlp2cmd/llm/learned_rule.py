# LearnedRule - extracted from adaptive_learner.py
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
class LearnedRule:
    """A routing rule learned from experience."""
    rule_id: str
    task: str
    condition: str  # "credit_exhausted:openrouter/*", "timeout:ollama/*", etc.
    preferred_model: str
    avoided_model: str
    confidence: float = 0.5
    times_applied: int = 0
    created: str = ""
    last_applied: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LearnedRule":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
