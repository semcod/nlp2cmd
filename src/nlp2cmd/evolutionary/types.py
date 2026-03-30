"""Shared types for the evolutionary recovery system."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RecoveryStrategy(Enum):
    """Strategie naprawy - rozszerzalne i ewolucyjne."""

    INSTALL_DEPENDENCY = "install_dependency"
    SWITCH_FALLBACK = "switch_fallback"
    CONFIGURE_ENV = "configure_env"
    CONSULT_LLM = "consult_llm"
    RETRY_WITH_DELAY = "retry_with_delay"
    MODIFY_ARGS = "modify_args"
    SKIP_AND_CONTINUE = "skip_and_continue"
    CREATE_WORKAROUND = "create_workaround"
    ESCALATE_TO_CLOUD = "escalate_to_cloud"
    USE_ALTERNATIVE_SITE = "use_alternative_site"
    FALLBACK_LOCAL_MODEL = "fallback_local_model"


@dataclass
class RecoveryAttempt:
    """Pojedyncza próba naprawy."""

    timestamp: float
    strategy: RecoveryStrategy
    context: dict[str, Any]
    llm_consulted: bool = False
    llm_advice: str = ""
    success: bool = False
    duration_ms: float = 0.0
    metrics_before: dict = field(default_factory=dict)
    metrics_after: dict = field(default_factory=dict)


@dataclass
class ExecutionMetrics:
    """Metryki wykonania - dla ciągłego doskonalenia."""

    start_time: float
    end_time: Optional[float] = None
    attempts: int = 0
    recovery_attempts: list[RecoveryAttempt] = field(default_factory=list)
    fallback_used: bool = False
    llm_calls: int = 0
    success: bool = False
    error_type: Optional[str] = None
    error_message: str = ""

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    @property
    def recovery_count(self) -> int:
        return len(self.recovery_attempts)
