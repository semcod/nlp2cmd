"""StepResult - extracted from __init__.py."""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from nlp2cmd.registry import ActionRegistry, ActionResult, get_registry
from nlp2cmd.executor.step_status import StepStatus

@dataclass
class StepResult:
    """Result of executing a single step."""
    
    step_index: int
    action: str
    status: StepStatus
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    iterations: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

