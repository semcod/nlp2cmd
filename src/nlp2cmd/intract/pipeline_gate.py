"""Pre-execute Intract gate for PipelineRunner."""

from __future__ import annotations

import os
from typing import Any, Optional

from nlp2cmd.intract.runtime_bridge import GateResult, RuntimeArtifact, RuntimeBridge
from nlp2cmd.ir import ActionIR


def intract_gate_enabled() -> bool:
    return os.getenv("NLP2CMD_INTRACT_GATE", "0").strip().lower() in {"1", "true", "yes", "on"}


class PipelineRunnerGate:
    """Validate ActionIR against Intract contracts before execution."""

    def __init__(self, bridge: Optional[RuntimeBridge] = None):
        self.bridge = bridge or RuntimeBridge()

    def artifact_from_ir(self, ir: ActionIR) -> tuple[Optional[RuntimeArtifact], list[str]]:
        warnings: list[str] = []
        metadata = ir.metadata or {}
        intent = str(metadata.get("intent") or ir.action_id or "")
        dom_action = metadata.get("dom_action") or metadata.get("action")
        action_name = metadata.get("registry_action") or metadata.get("action_name")

        contract_id = None
        if ir.dsl_kind == "dom" and dom_action:
            contract_id = self.bridge.resolve_contract_id(dom_action=str(dom_action))
        if not contract_id and action_name:
            contract_id = self.bridge.resolve_contract_id(action_name=str(action_name))
        if not contract_id and intent:
            contract_id = self.bridge.resolve_contract_id(intent=intent)
        if not contract_id and ir.action_id:
            contract_id = (
                self.bridge.resolve_contract_id(dom_action=ir.action_id)
                or self.bridge.resolve_contract_id(action_name=ir.action_id)
                or self.bridge.resolve_contract_id(intent=ir.action_id)
            )

        if not contract_id:
            warnings.append(f"No Intract contract mapped for ActionIR action_id={ir.action_id!r}")
            return None, warnings

        semantic_intent = str(metadata.get("semantic_intent") or intent or ir.action_id)
        return (
            RuntimeArtifact(
                contract_id=contract_id,
                intent=semantic_intent,
                dsl_kind=str(ir.dsl_kind),
                dsl=ir.dsl,
                params=dict(ir.params or {}),
            ),
            warnings,
        )

    def check(self, ir: ActionIR) -> GateResult:
        artifact, warnings = self.artifact_from_ir(ir)
        if artifact is None:
            return GateResult(
                passed=True,
                contract_id="",
                warnings=warnings,
                metadata={"skipped": True},
            )

        result = self.bridge.check(artifact)
        result.warnings = warnings + result.warnings
        return result

    def failure_message(self, result: GateResult) -> str:
        parts = [f"Intract gate blocked execution for {result.contract_id or 'unknown contract'}"]
        if result.violations:
            parts.append("violations: " + "; ".join(result.violations))
        if result.warnings:
            parts.append("warnings: " + "; ".join(result.warnings))
        return " | ".join(parts)

    def gate_result_metadata(self, result: GateResult) -> dict[str, Any]:
        return {
            "intract_gate": {
                "passed": result.passed,
                "contract_id": result.contract_id,
                "score": result.score,
                "violations": result.violations,
                "warnings": result.warnings,
                **result.metadata,
            }
        }
