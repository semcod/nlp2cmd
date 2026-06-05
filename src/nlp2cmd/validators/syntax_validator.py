"""SyntaxValidator - extracted from __init__.py."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import re
from nlp2cmd.validators.base_validator import BaseValidator
from nlp2cmd.validators.validation_result import ValidationResult

class SyntaxValidator(BaseValidator):
    """Generic syntax validator for balanced brackets, quotes, etc."""

    def validate(self, content: str) -> ValidationResult:
        """Validate basic syntax."""
        errors = []
        warnings = []

        # Check balanced parentheses
        if content.count("(") != content.count(")"):
            errors.append("Unbalanced parentheses")

        # Check balanced brackets
        if content.count("[") != content.count("]"):
            errors.append("Unbalanced square brackets")

        # Check balanced braces
        if content.count("{") != content.count("}"):
            errors.append("Unbalanced curly braces")

        # Check single quotes
        single_quotes = content.count("'") - content.count("\\'")
        if single_quotes % 2 != 0:
            errors.append("Unclosed single quote string")

        # Check double quotes
        double_quotes = content.count('"') - content.count('\\"')
        if double_quotes % 2 != 0:
            errors.append("Unclosed double quote string")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

