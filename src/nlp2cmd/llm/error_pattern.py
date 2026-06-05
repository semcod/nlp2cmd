# ErrorPattern - extracted from adaptive_learner.py
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

_ERROR_CLASSIFIERS: list[tuple[str, list[str], bool, float]] = [
    ("credit_exhausted", [
        "402", "payment required", "insufficient credit", "insufficient balance",
        "no credits", "billing", "quota exceeded", "credit limit",
        "exceeded your current quota", "rate limit exceeded.*tokens",
    ], False, 3600.0),
    ("rate_limited", [
        "429", "rate limit", "too many requests", "throttl",
        "requests per minute", "rpm", "tpm",
    ], True, 60.0),
    ("timeout", [
        "timeout", "timed out", "deadline exceeded", "connect timeout",
        "read timeout",
    ], True, 10.0),
    ("model_unavailable", [
        "404", "model not found", "does not exist", "unavailable",
        "service unavailable", "502", "503", "connection refused",
        "connect error", "no such model",
    ], True, 120.0),
    ("auth_error", [
        "401", "unauthorized", "invalid api key", "forbidden", "403",
    ], False, 3600.0),
    ("context_overflow", [
        "context length", "too long", "max.*token", "context_length_exceeded",
    ], True, 0.0),
]


@dataclass
class ErrorPattern:
    """Classified error pattern from LLM failures."""
    category: str  # "credit_exhausted", "rate_limited", "timeout", "model_unavailable", "unknown"
    model: str
    task: str
    error_msg: str
    timestamp: float = 0.0
    recoverable: bool = True
    cooldown_seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ErrorPattern":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def classify_error(error_msg: str, model: str = "", task: str = "") -> ErrorPattern:
    """Classify an error message into a known pattern category."""
    error_lower = error_msg.lower()
    for category, patterns, recoverable, cooldown in _ERROR_CLASSIFIERS:
        for pattern in patterns:
            if re.search(pattern, error_lower):
                return ErrorPattern(
                    category=category,
                    model=model,
                    task=task,
                    error_msg=error_msg[:500],
                    timestamp=time.time(),
                    recoverable=recoverable,
                    cooldown_seconds=cooldown,
                )
    return ErrorPattern(
        category="unknown",
        model=model,
        task=task,
        error_msg=error_msg[:500],
        timestamp=time.time(),
        recoverable=True,
        cooldown_seconds=30.0,
    )
