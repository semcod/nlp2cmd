"""BaseValidator - extracted from __init__.py."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import re
from nlp2cmd.validators.validation_result import ValidationResult

class BaseValidator(ABC):
    """Abstract base class for validators."""

    @abstractmethod
    def validate(self, content: str) -> ValidationResult:
        """
        Validate content.

        Args:
            content: Content to validate

        Returns:
            ValidationResult with validation outcome
        """
        raise NotImplementedError

    def validate_with_context(
        self,
        content: str,
        context: Optional[dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate content with additional context.

        Args:
            content: Content to validate
            context: Additional context for validation

        Returns:
            ValidationResult with validation outcome
        """
        return self.validate(content)

