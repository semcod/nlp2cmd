"""ActionHandler - extracted from __init__.py."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Generic
from nlp2cmd.registry.action_result import ActionResult
from nlp2cmd.registry.action_schema import ActionSchema
from nlp2cmd.registry.param_type import ParamType

class ActionHandler:
    """Base class for action handlers."""
    
    def __init__(self, schema: ActionSchema):
        self.schema = schema
    
    def validate_params(self, params: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate parameters against schema.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check required params
        for param_name in self.schema.get_required_params():
            if param_name not in params:
                errors.append(f"Missing required parameter: {param_name}")
        
        # Validate each provided param
        for name, value in params.items():
            param_schema = self.schema.get_param(name)
            
            if param_schema is None:
                errors.append(f"Unknown parameter: {name}")
                continue
            
            # Type validation
            if not self._validate_type(value, param_schema.type):
                errors.append(
                    f"Parameter '{name}' has invalid type. "
                    f"Expected {param_schema.type.value}, got {type(value).__name__}"
                )
                continue
            
            # Allowed values
            if param_schema.allowed_values is not None:
                if value not in param_schema.allowed_values:
                    errors.append(
                        f"Parameter '{name}' must be one of: {param_schema.allowed_values}"
                    )
            
            # Range validation
            if param_schema.min_value is not None and value < param_schema.min_value:
                errors.append(
                    f"Parameter '{name}' must be >= {param_schema.min_value}"
                )
            
            if param_schema.max_value is not None and value > param_schema.max_value:
                errors.append(
                    f"Parameter '{name}' must be <= {param_schema.max_value}"
                )
            
            # Custom validators
            for validator in param_schema.validators:
                try:
                    if not validator(value):
                        errors.append(f"Parameter '{name}' failed custom validation")
                except Exception as e:
                    errors.append(f"Parameter '{name}' validation error: {e}")
        
        return len(errors) == 0, errors
    
    def _validate_type(self, value: Any, expected: ParamType) -> bool:
        """Validate value type."""
        if expected == ParamType.ANY:
            return True
        
        type_map = {
            ParamType.STRING: str,
            ParamType.INTEGER: int,
            ParamType.FLOAT: (int, float),
            ParamType.BOOLEAN: bool,
            ParamType.LIST: list,
            ParamType.DICT: dict,
            ParamType.FILE_PATH: str,
            ParamType.GLOB_PATTERN: str,
            ParamType.REGEX_PATTERN: str,
            ParamType.SQL_IDENTIFIER: str,
            ParamType.K8S_RESOURCE: str,
        }
        
        expected_type = type_map.get(expected, object)
        return isinstance(value, expected_type)
    
    def execute(self, params: dict[str, Any]) -> ActionResult:
        """
        Execute the action.
        
        Must be overridden by concrete handlers.
        """
        raise NotImplementedError("Subclasses must implement execute()")

