"""CompositeValidator - extracted from __init__.py."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import re
from nlp2cmd.validators.base_validator import BaseValidator
from nlp2cmd.validators.validation_result import ValidationResult

class CompositeValidator(BaseValidator):
    """Combines multiple validators."""

    def __init__(self, validators: list[BaseValidator]):
        self.validators = validators

    def validate(self, content: str) -> ValidationResult:
        """Run all validators and merge results."""
        result = ValidationResult(is_valid=True)

        for validator in self.validators:
            validator_result = validator.validate(content)
            result = result.merge(validator_result)

        return result

