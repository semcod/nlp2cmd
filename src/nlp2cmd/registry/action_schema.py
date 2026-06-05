"""ActionSchema - extracted from __init__.py."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Generic
from nlp2cmd.registry.param_schema import ParamSchema
from nlp2cmd.registry.param_type import ParamType

@dataclass
class ActionSchema:
    """Schema definition for an action."""
    
    name: str
    description: str
    domain: str  # e.g., "sql", "shell", "docker", "kubernetes"
    params: list[ParamSchema] = field(default_factory=list)
    returns: ParamType = ParamType.ANY
    returns_description: str = ""
    requires_confirmation: bool = False
    is_destructive: bool = False
    tags: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
    
    def get_required_params(self) -> list[str]:
        """Get list of required parameter names."""
        return [p.name for p in self.params if p.required]
    
    def get_optional_params(self) -> list[str]:
        """Get list of optional parameter names."""
        return [p.name for p in self.params if not p.required]
    
    def get_param(self, name: str) -> Optional[ParamSchema]:
        """Get parameter schema by name."""
        for param in self.params:
            if param.name == name:
                return param
        return None

