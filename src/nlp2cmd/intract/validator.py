"""Intract-backed validator for nlp2cmd transform pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from nlp2cmd.intract.runtime_bridge import RuntimeArtifact, RuntimeBridge
from nlp2cmd.validators.base_validator import BaseValidator
from nlp2cmd.validators.validation_result import ValidationResult


class IntractValidator(BaseValidator):
    """Validate generated DSL against Intract semantic contracts."""

    def __init__(
        self,
        bridge: Optional[RuntimeBridge] = None,
        *,
        bindings_path: Optional[Path] = None,
        manifest_path: Optional[Path] = None,
        default_dsl_kind: str = "shell",
    ):
        self.bridge = bridge or RuntimeBridge(
            bindings_path=bindings_path,
            manifest_path=manifest_path,
        )
        self.default_dsl_kind = default_dsl_kind

    def validate(self, content: str, plan: Any = None) -> ValidationResult:
        intent = getattr(plan, "intent", None) if plan is not None else None
        domain = getattr(plan, "domain", None) if plan is not None else None
        entities = getattr(plan, "entities", {}) if plan is not None else {}

        contract_id = None
        if intent:
            contract_id = self.bridge.resolve_contract_id(intent=intent)

        if not contract_id:
            return ValidationResult(
                is_valid=True,
                warnings=[f"No Intract contract mapped for intent: {intent}"],
                metadata={"intent": intent, "domain": domain},
            )

        artifact = RuntimeArtifact(
            contract_id=contract_id,
            intent=str(intent),
            dsl_kind=str(domain or self.default_dsl_kind),
            dsl=content,
            params=entities if isinstance(entities, dict) else {},
        )
        gate = self.bridge.check(artifact)

        return ValidationResult(
            is_valid=gate.passed,
            errors=gate.violations,
            warnings=gate.warnings,
            metadata={
                "contract_id": gate.contract_id,
                "score": gate.score,
                **gate.metadata,
            },
        )
