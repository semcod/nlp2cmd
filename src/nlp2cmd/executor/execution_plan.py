"""ExecutionPlan - extracted from __init__.py."""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from nlp2cmd.registry import ActionRegistry, ActionResult, get_registry
from nlp2cmd.executor.plan_step import PlanStep

@dataclass
class ExecutionPlan:
    """Multi-step execution plan."""
    
    steps: list[PlanStep]
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionPlan":
        """Create plan from dictionary."""
        steps = []
        for step_data in data.get("steps", []):
            steps.append(PlanStep(
                action=step_data["action"],
                params=step_data.get("params", {}),
                foreach=step_data.get("foreach"),
                condition=step_data.get("condition"),
                store_as=step_data.get("store_as"),
                on_error=step_data.get("on_error", "stop"),
                timeout=step_data.get("timeout"),
                retry=step_data.get("retry", 0),
            ))
        
        return cls(
            steps=steps,
            metadata=data.get("metadata", {}),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert plan to dictionary."""
        return {
            "steps": [
                {
                    "action": step.action,
                    "params": step.params,
                    "foreach": step.foreach,
                    "condition": step.condition,
                    "store_as": step.store_as,
                    "on_error": step.on_error,
                    "timeout": step.timeout,
                    "retry": step.retry,
                }
                for step in self.steps
            ],
            "metadata": self.metadata,
        }

