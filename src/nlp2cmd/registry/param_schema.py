"""ParamSchema - extracted from __init__.py."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Generic
from nlp2cmd.registry.param_type import ParamType

@dataclass
class ParamSchema:
    """Schema for an action parameter."""
    
    name: str
    type: ParamType
    required: bool = True
    default: Any = None
    description: str = ""
    validators: list[Callable[[Any], bool]] = field(default_factory=list)
    allowed_values: Optional[list[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # Regex pattern for strings

