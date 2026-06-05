"""PlanValidator - extracted from __init__.py."""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from nlp2cmd.registry import ActionRegistry, ActionResult, get_registry
from nlp2cmd.executor.execution_plan import ExecutionPlan
from nlp2cmd.executor.plan_step import PlanStep

class PlanValidator:
    """Validates execution plans against action registry."""
    
    # JSON Schema for plan validation
    PLAN_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["steps"],
        "properties": {
            "steps": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["action"],
                    "properties": {
                        "action": {"type": "string"},
                        "params": {"type": "object"},
                        "foreach": {"type": "string"},
                        "condition": {"type": "string"},
                        "store_as": {"type": "string"},
                        "on_error": {
                            "type": "string",
                            "enum": ["stop", "skip", "continue"]
                        },
                        "timeout": {"type": "number", "minimum": 0},
                        "retry": {"type": "integer", "minimum": 0},
                    },
                },
            },
            "metadata": {"type": "object"},
        },
    }
    
    def __init__(self, registry: Optional[ActionRegistry] = None):
        self.registry = registry or get_registry()
    
    def validate(self, plan: ExecutionPlan) -> tuple[bool, list[str]]:
        """
        Validate an execution plan.
        
        Args:
            plan: Plan to validate
            
        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []
        
        if not plan.steps:
            errors.append("Plan must have at least one step")
            return False, errors
        
        defined_variables = set()
        
        for i, step in enumerate(plan.steps):
            step_errors = self._validate_step(step, i, defined_variables)
            errors.extend(step_errors)
            
            # Track defined variables
            if step.store_as:
                defined_variables.add(step.store_as)
        
        return len(errors) == 0, errors
    
    def _validate_step(
        self,
        step: PlanStep,
        index: int,
        defined_variables: set[str],
    ) -> list[str]:
        """Validate a single step."""
        errors = []
        prefix = f"Step {index + 1} ({step.action})"
        
        # Check action exists
        if not self.registry.has(step.action):
            errors.append(f"{prefix}: Unknown action '{step.action}'")
            return errors  # Can't validate params if action unknown
        
        # Validate params
        is_valid, param_errors = self.registry.validate_action(
            step.action, step.params
        )
        if not is_valid:
            for err in param_errors:
                errors.append(f"{prefix}: {err}")
        
        # Validate foreach reference
        if step.foreach:
            ref_var = step.foreach.split(".")[0]
            if ref_var not in defined_variables and not ref_var.startswith("$"):
                errors.append(
                    f"{prefix}: foreach references undefined variable '{ref_var}'"
                )
        
        # Validate condition references
        if step.condition:
            refs = re.findall(r"\$(\w+)", step.condition)
            for ref in refs:
                if ref not in defined_variables and ref not in ("item", "index"):
                    errors.append(
                        f"{prefix}: condition references undefined variable '{ref}'"
                    )
        
        # Validate param references
        for param_name, param_value in step.params.items():
            if isinstance(param_value, str) and param_value.startswith("$"):
                ref_var = param_value[1:].split(".")[0]
                if ref_var not in defined_variables and ref_var not in ("item", "index"):
                    errors.append(
                        f"{prefix}: param '{param_name}' references undefined variable '{ref_var}'"
                    )
        
        return errors

