"""
Core data models for NLP2CMD framework.

This module contains the base classes and data models used throughout
the NLP2CMD framework for intent detection, entity extraction, and
command transformation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Compatibility layer for pydantic
try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    import copy
    from dataclasses import dataclass as _dataclass

    @_dataclass
    class _FieldInfo:
        default: Any = ...
        default_factory: Optional[Callable[[], Any]] = None

    def Field(
        default: Any = ...,  # noqa: N803
        default_factory: Optional[Callable[[], Any]] = None,
        description: str | None = None,
        **_: Any,
    ) -> Any:
        return _FieldInfo(default=default, default_factory=default_factory)

    class BaseModel:  # noqa: D101
        def __init__(self, **data: Any):
            annotations = getattr(self.__class__, "__annotations__", {})
            for key in annotations.keys():
                if key in data:
                    value = data[key]
                else:
                    default_value = getattr(self.__class__, key, ...)
                    if isinstance(default_value, _FieldInfo):
                        if default_value.default_factory is not None:
                            value = default_value.default_factory()
                        else:
                            value = default_value.default
                    else:
                        value = default_value

                if value is ...:
                    raise TypeError(f"Missing required field: {key}")

                setattr(self, key, value)

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, self.__class__):
                return False
            return self.model_dump() == other.model_dump()

        def __repr__(self) -> str:
            data = self.model_dump()
            inner = ", ".join(f"{k}={data[k]!r}" for k in data.keys())
            return f"{self.__class__.__name__}({inner})"

        def __str__(self) -> str:
            return self.__repr__()

        def model_dump(self) -> dict[str, Any]:
            out: dict[str, Any] = {}
            annotations = getattr(self.__class__, "__annotations__", {})
            for key in annotations.keys():
                value = getattr(self, key)
                if isinstance(value, BaseModel):
                    out[key] = value.model_dump()
                else:
                    out[key] = value
            return out

        def model_copy(self, update: Optional[dict[str, Any]] = None, deep: bool = False):
            data = self.model_dump()
            if update:
                data.update(update)
            if deep:
                data = copy.deepcopy(data)
            return self.__class__(**data)


class TransformStatus(str, Enum):
    """Status of a transformation operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"
    ERROR = "error"


class Intent(BaseModel):
    """Represents a detected intent from natural language input."""

    name: str = Field(..., description="Intent name")
    confidence: float = Field(default=0.0, description="Confidence score (0-1)")
    domain: Optional[str] = Field(default=None, description="Domain of the intent")
    patterns: list[str] = Field(default_factory=list, description="Keyword patterns for this intent")
    required_entities: list[str] = Field(default_factory=list, description="Required entity names")
    confidence_threshold: float = Field(default=0.7, description="Minimum confidence to accept")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Entity(BaseModel):
    """Represents an extracted entity from natural language input."""

    name: str = Field(..., description="Entity name")
    value: Any = Field(..., description="Entity value")
    type: Optional[str] = Field(default=None, description="Entity type")
    confidence: float = Field(default=1.0, description="Extraction confidence")
    start: Optional[int] = Field(default=None, description="Start position in text")
    end: Optional[int] = Field(default=None, description="End position in text")


class ExecutionPlan(BaseModel):
    """Structured plan for command execution."""

    intent: str = Field(..., description="Detected intent")
    entities: dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    confidence: float = Field(default=0.0, description="Overall confidence")
    domain: Optional[str] = Field(default=None, description="Target domain")
    requires_confirmation: bool = Field(default=False, description="Whether plan requires user confirmation")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    text: str = Field(default="", description="Original input text")
    
    def with_confidence(self, confidence: float) -> "ExecutionPlan":
        """Create a copy with updated confidence."""
        return self.model_copy(update={"confidence": confidence})
    
    def with_entities(self, entities: dict[str, Any]) -> "ExecutionPlan":
        """Create a copy with updated entities (merged with existing)."""
        merged_entities = {**self.entities, **entities}
        return self.model_copy(update={"entities": merged_entities})
    
    def with_metadata(self, metadata: dict[str, Any]) -> "ExecutionPlan":
        """Create a copy with updated metadata."""
        return self.model_copy(update={"metadata": metadata})
    
    def with_context(self, context: dict[str, Any]) -> "ExecutionPlan":
        """Create a copy with updated context."""
        return self.model_copy(update={"metadata": {**self.metadata, "context": context}})
    
    def with_errors(self, errors: list[str]) -> "ExecutionPlan":
        """Create a copy with error information in metadata."""
        return self.model_copy(update={"metadata": {**self.metadata, "errors": errors}})
    
    def with_security(self, security_context: dict[str, Any]) -> "ExecutionPlan":
        """Create a copy with security context."""
        return self.model_copy(update={"metadata": {**self.metadata, "security": security_context}})
    
    def with_performance(self, performance_data: dict[str, Any]) -> "ExecutionPlan":
        """Create a copy with performance data."""
        return self.model_copy(update={"metadata": {**self.metadata, "performance": performance_data}})
    
    def is_valid(self) -> bool:
        """Check if execution plan is valid."""
        return (
            len(self.intent.strip()) > 0 and
            self.confidence >= 0.0 and
            self.confidence <= 1.0
        )


@dataclass
class TransformResult:
    """Result of a natural language to command transformation."""

    status: TransformStatus
    command: Optional[str] = None
    intent: Optional[str] = None
    entities: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    execution_plan: Optional[ExecutionPlan] = None
    plan: Optional[ExecutionPlan] = None  # alias for execution_plan
    dsl_type: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Unify plan/execution_plan aliases
        if self.plan is not None and self.execution_plan is None:
            self.execution_plan = self.plan
        elif self.execution_plan is not None and self.plan is None:
            self.plan = self.execution_plan

    @property
    def is_success(self) -> bool:
        """Check if transformation was successful."""
        return self.status in [TransformStatus.SUCCESS, TransformStatus.PARTIAL]

    @property
    def is_blocked(self) -> bool:
        """Check if transformation was blocked by security policy."""
        return self.status == TransformStatus.BLOCKED

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "status": self.status.value,
            "command": self.command,
            "intent": self.intent,
            "entities": self.entities,
            "confidence": self.confidence,
            "execution_plan": self.execution_plan.model_dump() if self.execution_plan else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    def copy(self) -> "TransformResult":
        """Create a copy of the transform result."""
        return TransformResult(
            status=self.status,
            command=self.command,
            intent=self.intent,
            entities=self.entities.copy(),
            confidence=self.confidence,
            execution_plan=self.execution_plan.model_copy() if self.execution_plan else None,
            dsl_type=self.dsl_type,
            errors=self.errors.copy(),
            warnings=self.warnings.copy(),
            metadata=self.metadata.copy(),
        )

    def is_valid(self) -> bool:
        """Check if result is valid (no errors and successful status)."""
        return (
            self.status == TransformStatus.SUCCESS and 
            len(self.errors) == 0 and
            self.command is not None and
            len(self.command.strip()) > 0 and
            0.0 <= self.confidence <= 1.0
        )
