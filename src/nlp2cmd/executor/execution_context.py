"""ExecutionContext - extracted from __init__.py."""

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
class ExecutionContext:
    """Context for plan execution."""
    
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    variables: dict[str, Any] = field(default_factory=dict)
    results: list[StepResult] = field(default_factory=list)
    current_step: int = 0
    dry_run: bool = False
    
    def set(self, name: str, value: Any) -> None:
        """Set a variable."""
        self.variables[name] = value
    
    def get(self, name: str, default: Any = None) -> Any:
        """Get a variable."""
        return self.variables.get(name, default)
    
    def resolve_reference(self, ref: str) -> Any:
        """
        Resolve a variable reference.
        
        Supports:
        - $variable_name
        - $step_result.field
        - $item (in foreach context)
        - $index (in foreach context)
        """
        if not ref.startswith("$"):
            return ref
        
        path = ref[1:].split(".")
        var_name = path[0]
        
        if var_name not in self.variables:
            raise ValueError(f"Unknown variable: {var_name}")
        
        value = self.variables[var_name]
        
        # Navigate nested path
        for key in path[1:]:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                value = value[int(key)]
            elif hasattr(value, key):
                value = getattr(value, key)
            else:
                raise ValueError(f"Cannot resolve path: {ref}")
        
        return value

