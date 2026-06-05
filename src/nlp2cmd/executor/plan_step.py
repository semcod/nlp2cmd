"""PlanStep - extracted from __init__.py."""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from nlp2cmd.registry import ActionRegistry, ActionResult, get_registry

@dataclass
class PlanStep:
    """A single step in an execution plan."""
    
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    foreach: Optional[str] = None  # Reference to iterate over
    condition: Optional[str] = None  # Condition for execution
    store_as: Optional[str] = None  # Variable name to store result
    on_error: str = "stop"  # "stop", "skip", "continue"
    timeout: Optional[float] = None  # Timeout in seconds
    retry: int = 0  # Number of retries on failure
    
    def __post_init__(self):
        # Generate store_as if not provided
        if self.store_as is None:
            self.store_as = f"{self.action}_result"

