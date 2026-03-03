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


# Error classifiers — ordered by specificity
_ERROR_CLASSIFIERS: list[tuple[str, list[str], bool, float]] = [
    # (category, patterns, recoverable, default_cooldown_seconds)
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


# ---------------------------------------------------------------------------
# Model performance record
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


# ---------------------------------------------------------------------------
# Learned routing rule
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


# ---------------------------------------------------------------------------
# AdaptiveLearner — main class
# ---------------------------------------------------------------------------

class AdaptiveLearner:
    """
    Adaptive learning system for LLM routing.

    Learns from:
    1. Failures (credit exhaustion, rate limits, timeouts)
    2. Successes (records best model for each task)
    3. Fallback patterns (when A fails and B works, prefer B next time)
    4. New challenges (new task types, new error patterns)

    Persistent: saves state to ~/.nlp2cmd/adaptive_routing.json
    """

    CACHE_FILE = "adaptive_routing.json"
    MAX_RULES = 100
    MAX_HISTORY = 500

    def __init__(self, cache_dir: Optional[Path] = None):
        self._cache_dir = cache_dir or Path(
            os.environ.get("NLP2CMD_CACHE_DIR", str(Path.home() / ".nlp2cmd"))
        ).expanduser()
        self._cache_file = self._cache_dir / self.CACHE_FILE

        # Model performance tracking: key = "model:task"
        self._performance: dict[str, ModelPerformance] = {}
        # Learned routing rules
        self._rules: list[LearnedRule] = []
        # Error history (recent)
        self._error_history: list[ErrorPattern] = []
        # Fallback chain memory: tracks A→B fallback pairs that worked
        self._fallback_pairs: dict[str, str] = {}  # "failed_model:task" → "working_model"

        self._load()
        _debug(f"Loaded {len(self._performance)} perf records, {len(self._rules)} rules")

    # -------------------------------------------------------------------
    # Core learning methods
    # -------------------------------------------------------------------

    def record_success(
        self,
        model: str,
        task: str,
        latency_ms: float,
        was_fallback: bool = False,
        fallback_from: Optional[str] = None,
    ) -> None:
        """Record a successful model call. Learns from fallback patterns."""
        key = f"{model}:{task}"
        perf = self._get_or_create_perf(model, task)
        perf.total_calls += 1
        perf.successes += 1
        perf.total_latency_ms += latency_ms
        perf.last_success = time.time()
        perf.consecutive_failures = 0

        # Learn fallback pattern
        if was_fallback and fallback_from:
            fb_key = f"{fallback_from}:{task}"
            self._fallback_pairs[fb_key] = model
            _debug(f"Learned fallback: {fallback_from} → {model} for task={task}")

            # Create or update a routing rule
            self._learn_rule(
                task=task,
                condition=f"fallback:{fallback_from}",
                preferred=model,
                avoided=fallback_from,
            )

        self._save()

    def record_failure(
        self,
        model: str,
        task: str,
        error_msg: str,
    ) -> ErrorPattern:
        """Record a failed model call. Classifies the error and applies cooldowns."""
        pattern = classify_error(error_msg, model, task)

        perf = self._get_or_create_perf(model, task)
        perf.total_calls += 1
        perf.failures += 1
        perf.last_failure = time.time()
        perf.last_error_category = pattern.category
        perf.consecutive_failures += 1

        # Apply cooldown based on error type
        if pattern.cooldown_seconds > 0:
            perf.cooldown_until = time.time() + pattern.cooldown_seconds
            _debug(
                f"Model {model} cooled down for {pattern.cooldown_seconds}s "
                f"(error={pattern.category})"
            )

        # Non-recoverable errors get strong negative preference
        if not pattern.recoverable:
            perf.learned_preference = max(-1.0, perf.learned_preference - 0.5)
            _debug(f"Model {model} preference decreased to {perf.learned_preference:.2f}")

        # Record in history
        self._error_history.append(pattern)
        if len(self._error_history) > self.MAX_HISTORY:
            self._error_history = self._error_history[-self.MAX_HISTORY:]

        self._save()
        return pattern

    def recommend_model(
        self,
        task: str,
        available_models: Optional[list[str]] = None,
    ) -> Optional[str]:
        """
        Recommend the best model for a task based on learned performance.

        Returns model name or None if no recommendation.
        """
        candidates: list[tuple[str, float]] = []

        for key, perf in self._performance.items():
            if perf.task != task:
                continue
            if available_models and perf.model not in available_models:
                continue
            score = perf.health_score
            if score < 0:
                continue  # In cooldown
            candidates.append((perf.model, score))

        if not candidates:
            return None

        # Sort by health score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_model, best_score = candidates[0]
        _debug(f"Recommend {best_model} for task={task} (score={best_score:.3f})")
        return best_model

    def should_skip_model(self, model: str, task: str) -> bool:
        """Check if a model should be skipped (in cooldown or too many failures)."""
        key = f"{model}:{task}"
        perf = self._performance.get(key)
        if perf is None:
            return False

        # In cooldown
        if not perf.is_cooled_down:
            _debug(f"Skipping {model}: in cooldown until {perf.cooldown_until:.0f}")
            return True

        # Too many consecutive failures (3+)
        if perf.consecutive_failures >= 3:
            _debug(f"Skipping {model}: {perf.consecutive_failures} consecutive failures")
            return True

        # Learned negative preference below threshold
        if perf.learned_preference <= -0.8:
            _debug(f"Skipping {model}: learned_preference={perf.learned_preference:.2f}")
            return True

        return False

    def get_fallback_model(self, failed_model: str, task: str) -> Optional[str]:
        """Get the learned fallback for a model+task pair."""
        key = f"{failed_model}:{task}"
        return self._fallback_pairs.get(key)

    # -------------------------------------------------------------------
    # Evolution — detect patterns across errors and adapt
    # -------------------------------------------------------------------

    def evolve(self) -> list[str]:
        """
        Analyze recent error patterns and evolve routing rules.

        Returns list of evolution actions taken.
        """
        actions: list[str] = []
        now = time.time()

        # 1. Detect persistent credit exhaustion → block remote models
        recent_errors = [e for e in self._error_history if now - e.timestamp < 3600]
        credit_errors = [e for e in recent_errors if e.category == "credit_exhausted"]

        if credit_errors:
            affected_models = set(e.model for e in credit_errors)
            for model in affected_models:
                for task in ("vision", "coding", "text", "polish", "repair", "planning"):
                    perf = self._get_or_create_perf(model, task)
                    if perf.cooldown_until < now + 1800:
                        perf.cooldown_until = now + 3600  # 1-hour block
                        perf.learned_preference = -1.0
                        actions.append(
                            f"Blocked {model} for 1h (credit exhausted)"
                        )

        # 2. Detect rate limit patterns → extend cooldowns
        rate_errors = [e for e in recent_errors if e.category == "rate_limited"]
        if len(rate_errors) >= 3:
            affected = set(e.model for e in rate_errors)
            for model in affected:
                count = sum(1 for e in rate_errors if e.model == model)
                if count >= 3:
                    cooldown = min(300.0, 60.0 * count)  # Progressive cooldown
                    for task_name in set(e.task for e in rate_errors if e.model == model):
                        perf = self._get_or_create_perf(model, task_name)
                        perf.cooldown_until = max(perf.cooldown_until, now + cooldown)
                    actions.append(
                        f"Extended cooldown for {model}: {cooldown:.0f}s ({count} rate limits)"
                    )

        # 3. Promote consistently good local models
        for key, perf in self._performance.items():
            if (
                perf.model.startswith("ollama/")
                and perf.successes >= 5
                and perf.success_rate >= 0.9
                and perf.learned_preference < 0.5
            ):
                perf.learned_preference = min(1.0, perf.learned_preference + 0.2)
                actions.append(
                    f"Promoted {perf.model} for {perf.task} "
                    f"(preference={perf.learned_preference:.2f})"
                )

        # 4. Decay old cooldowns for recovered models
        for key, perf in self._performance.items():
            if (
                perf.cooldown_until > 0
                and perf.cooldown_until < now
                and perf.last_error_category in ("rate_limited", "timeout")
            ):
                # Only decay recoverable errors
                perf.consecutive_failures = max(0, perf.consecutive_failures - 1)
                perf.learned_preference = min(
                    0.0, perf.learned_preference + 0.1
                )

        if actions:
            _debug(f"Evolution: {len(actions)} actions taken")
            self._save()

        return actions

    # -------------------------------------------------------------------
    # Introspection
    # -------------------------------------------------------------------

    def get_performance_report(self) -> dict[str, Any]:
        """Get a human-readable performance report."""
        report: dict[str, Any] = {
            "models": {},
            "rules": [r.to_dict() for r in self._rules],
            "error_summary": {},
            "fallback_pairs": dict(self._fallback_pairs),
        }

        for key, perf in sorted(self._performance.items()):
            report["models"][key] = {
                "success_rate": round(perf.success_rate, 3),
                "avg_latency_ms": round(perf.avg_latency_ms, 1),
                "health_score": round(perf.health_score, 3),
                "total_calls": perf.total_calls,
                "consecutive_failures": perf.consecutive_failures,
                "learned_preference": round(perf.learned_preference, 2),
                "in_cooldown": not perf.is_cooled_down,
            }

        # Error category summary
        for ep in self._error_history:
            cat = ep.category
            report["error_summary"][cat] = report["error_summary"].get(cat, 0) + 1

        return report

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _get_or_create_perf(self, model: str, task: str) -> ModelPerformance:
        key = f"{model}:{task}"
        if key not in self._performance:
            self._performance[key] = ModelPerformance(model=model, task=task)
        return self._performance[key]

    def _learn_rule(
        self,
        task: str,
        condition: str,
        preferred: str,
        avoided: str,
    ) -> None:
        """Create or update a learned routing rule."""
        rule_id = f"{task}:{condition}"

        # Check if rule exists
        for rule in self._rules:
            if rule.rule_id == rule_id:
                rule.preferred_model = preferred
                rule.avoided_model = avoided
                rule.confidence = min(1.0, rule.confidence + 0.1)
                rule.times_applied += 1
                rule.last_applied = datetime.now().isoformat()
                return

        # Create new rule
        if len(self._rules) >= self.MAX_RULES:
            # Remove least-applied rule
            self._rules.sort(key=lambda r: r.times_applied)
            self._rules.pop(0)

        self._rules.append(LearnedRule(
            rule_id=rule_id,
            task=task,
            condition=condition,
            preferred_model=preferred,
            avoided_model=avoided,
            confidence=0.5,
            times_applied=1,
            created=datetime.now().isoformat(),
            last_applied=datetime.now().isoformat(),
        ))

    # -------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------

    def _load(self) -> None:
        """Load learned state from disk."""
        if not self._cache_file.exists():
            return
        try:
            data = json.loads(self._cache_file.read_text(encoding="utf-8"))
            for key, d in data.get("performance", {}).items():
                self._performance[key] = ModelPerformance.from_dict(d)
            for d in data.get("rules", []):
                self._rules.append(LearnedRule.from_dict(d))
            for d in data.get("error_history", []):
                self._error_history.append(ErrorPattern.from_dict(d))
            self._fallback_pairs = data.get("fallback_pairs", {})
        except Exception as e:
            _debug(f"Failed to load adaptive state: {e}")

    def _save(self) -> None:
        """Save learned state to disk."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                "version": 1,
                "updated": datetime.now().isoformat(),
                "performance": {k: v.to_dict() for k, v in self._performance.items()},
                "rules": [r.to_dict() for r in self._rules],
                "error_history": [e.to_dict() for e in self._error_history[-100:]],
                "fallback_pairs": self._fallback_pairs,
            }
            self._cache_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8",
            )
        except Exception as e:
            _debug(f"Failed to save adaptive state: {e}")

    def reset(self) -> None:
        """Reset all learned state."""
        self._performance.clear()
        self._rules.clear()
        self._error_history.clear()
        self._fallback_pairs.clear()
        if self._cache_file.exists():
            self._cache_file.unlink()
        _debug("Adaptive learner state reset")
