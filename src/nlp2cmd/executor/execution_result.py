"""ExecutionResult - extracted from __init__.py."""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from nlp2cmd.registry import ActionRegistry, ActionResult, get_registry
from nlp2cmd.executor.step_result import StepResult

@dataclass
class ExecutionResult:
    """Result of executing a complete plan."""
    
    trace_id: str
    success: bool
    steps: list[StepResult]
    final_result: Any = None
    error: Optional[str] = None
    total_duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

