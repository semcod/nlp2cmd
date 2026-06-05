"""ValidationResult - extracted from __init__.py."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import re

@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another validation result into this one."""
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            suggestions=self.suggestions + other.suggestions,
            metadata={**self.metadata, **other.metadata},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationResult":
        """Create validation result from dictionary."""
        return cls(
            is_valid=data.get("is_valid", True),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            suggestions=data.get("suggestions", []),
            metadata=data.get("metadata", {}),
        )

    def add_error(self, error: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(warning)

    def has_errors(self) -> bool:
        """Check if validation result has errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if validation result has warnings."""
        return len(self.warnings) > 0

    def copy(self) -> "ValidationResult":
        """Create a copy of the validation result."""
        return ValidationResult(
            is_valid=self.is_valid,
            errors=self.errors.copy(),
            warnings=self.warnings.copy(),
            suggestions=self.suggestions.copy(),
            metadata=self.metadata.copy(),
        )

    def __str__(self) -> str:
        """String representation of validation result."""
        status = "VALID" if self.is_valid else "INVALID"
        details = []
        if self.errors:
            details.append(f" - {', '.join(self.errors[:2])}")
            if len(self.errors) > 2:
                details[-1] += f" (and {len(self.errors) - 2} more)"
        if self.warnings:
            details.append(f" - {', '.join(self.warnings[:2])}")
            if len(self.warnings) > 2:
                details[-1] += f" (and {len(self.warnings) - 2} more)"
        return f"{status} ValidationResult(errors={len(self.errors)}, warnings={len(self.warnings)}){''.join(details)}"

