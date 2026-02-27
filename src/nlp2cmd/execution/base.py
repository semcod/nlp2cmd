"""
Base executor interface — Etap 3 of the NLP refactoring plan.

All executors share a common interface: ``execute(context) → ExecutorResult``.
This enables the pipeline runner to dispatch to the right executor based on
domain/action type without needing to know implementation details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExecutorResult:
    """Unified result from any executor."""

    success: bool
    kind: str  # "shell", "browser", "form", "data", "media"
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_runner_result(self) -> Any:
        """Convert to legacy RunnerResult for backward compatibility."""
        from nlp2cmd.pipeline_runner_utils import RunnerResult
        return RunnerResult(
            success=self.success,
            kind=self.kind,
            data=self.data,
            error=self.error,
            duration_ms=self.duration_ms,
        )


@dataclass
class ExecutorContext:
    """Shared context passed to executors."""

    dry_run: bool = False
    confirm: bool = False
    headless: bool = True
    video_fmt: Optional[str] = None
    video_dir: str = "./recordings"
    console: Any = None  # Rich Console instance
    page: Any = None  # Playwright Page (for browser executors sharing a session)
    context: Any = None  # Playwright BrowserContext
    variables: dict[str, str] = field(default_factory=dict)  # shared step variables


class BaseExecutor(ABC):
    """Abstract base for all executors.

    Subclasses implement ``execute()`` with domain-specific logic.
    Each executor should be <200 lines and have a single responsibility.
    """

    @abstractmethod
    def execute(self, params: dict[str, Any], ctx: ExecutorContext) -> ExecutorResult:
        """Execute an action with the given parameters and context."""
        ...

    @property
    @abstractmethod
    def supported_actions(self) -> list[str]:
        """List of action names this executor handles."""
        ...
