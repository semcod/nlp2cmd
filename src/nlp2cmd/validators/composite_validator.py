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

    def validate(self, content: str, plan: Any = None) -> ValidationResult:
        """Run all validators and merge results."""
        from nlp2cmd.validators.factory import _call_validator

        result = ValidationResult(is_valid=True)

        for validator in self.validators:
            validator_result = _call_validator(validator, content, plan)
            result = result.merge(validator_result)

        return result

