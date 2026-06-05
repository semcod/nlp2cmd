"""Build validators for NLP2CMD transform pipeline."""

from __future__ import annotations

import inspect
from typing import Any, Optional

from nlp2cmd.intract.pipeline_gate import intract_gate_enabled
from nlp2cmd.validators.base_validator import BaseValidator
from nlp2cmd.validators.composite_validator import CompositeValidator
from nlp2cmd.validators.validation_result import ValidationResult


def _call_validator(validator: BaseValidator, content: str, plan: Any = None) -> ValidationResult:
    signature = inspect.signature(validator.validate)
    if "plan" in signature.parameters:
        return validator.validate(content, plan)  # type: ignore[call-arg]
    return validator.validate(content)


def _domain_validator(dsl_name: str) -> Optional[BaseValidator]:
    normalized = (dsl_name or "").strip().lower()
    if normalized == "shell":
        from nlp2cmd.validators.shell_validator import ShellValidator

        return ShellValidator()
    if normalized == "sql":
        from nlp2cmd.validators.sql_validator import SQLValidator

        return SQLValidator()
    if normalized == "docker":
        from nlp2cmd.validators.docker_validator import DockerValidator

        return DockerValidator()
    if normalized in {"kubernetes", "k8s"}:
        from nlp2cmd.validators.kubernetes_validator import KubernetesValidator

        return KubernetesValidator()
    return None


class TransformValidator(BaseValidator):
    """Domain validator plus optional Intract contract checks."""

    def __init__(self, validators: list[BaseValidator]):
        self.validators = validators

    def validate(self, content: str, plan: Any = None) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        for validator in self.validators:
            result = result.merge(_call_validator(validator, content, plan))
        return result


def build_transform_validator(dsl_name: str) -> Optional[BaseValidator]:
    """Return transform validator for adapter domain (Intract when gate enabled)."""
    validators: list[BaseValidator] = []

    domain_validator = _domain_validator(dsl_name)
    if domain_validator is not None:
        validators.append(domain_validator)

    if intract_gate_enabled():
        from nlp2cmd.intract.validator import IntractValidator

        validators.append(IntractValidator())

    if not validators:
        return None
    if len(validators) == 1:
        return validators[0]
    return TransformValidator(validators)


def build_default_composite_validator(validators: list[BaseValidator]) -> CompositeValidator:
    """Backward-compatible composite builder for callers expecting CompositeValidator."""
    return CompositeValidator(validators)
