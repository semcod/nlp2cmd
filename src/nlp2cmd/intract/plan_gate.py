"""Intract gate for ExecutionPlanIR PlanStep validation."""

from __future__ import annotations

from typing import Any, Optional

from nlp2cmd.intract.pipeline_gate import intract_gate_enabled
from nlp2cmd.intract.runtime_bridge import GateResult, RuntimeArtifact, RuntimeBridge


class PlanContractViolation(Exception):
    """Raised when one or more plan steps fail Intract contract checks."""

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = results
        failed = [item for item in results if not item.get("passed")]
        messages = []
        for item in failed:
            step_id = item.get("step_id", "?")
            violations = item.get("violations") or []
            messages.append(f"{step_id}: {'; '.join(violations) or 'contract check failed'}")
        super().__init__("; ".join(messages) or "plan contract violation")


class PlanStepGate:
    """Validate PlanStep artifacts against Intract contracts."""

    def __init__(self, bridge: Optional[RuntimeBridge] = None):
        self.bridge = bridge or RuntimeBridge()

    def artifact_from_step(
        self,
        step: Any,
        *,
        intent_name: str,
    ) -> tuple[Optional[RuntimeArtifact], list[str]]:
        warnings: list[str] = []
        action = str(getattr(step, "action", "") or "")
        contract_id = self.bridge.resolve_contract_id(action_name=action)
        if not contract_id and intent_name:
            contract_id = self.bridge.resolve_contract_id(intent=intent_name)
        if not contract_id:
            warnings.append(
                f"No Intract contract mapped for step action={action!r} intent={intent_name!r}",
            )
            return None, warnings

        target_kind = getattr(step, "target_kind", None)
        dsl_kind = getattr(target_kind, "value", None) or str(target_kind or "shell")
        params = dict(getattr(step, "params", None) or {})
        return (
            RuntimeArtifact(
                contract_id=contract_id,
                intent=intent_name,
                dsl_kind=str(dsl_kind),
                dsl=str(getattr(step, "dsl", "") or ""),
                params=params,
            ),
            warnings,
        )

    def check_step(self, step: Any, *, intent_name: str) -> GateResult:
        artifact, warnings = self.artifact_from_step(step, intent_name=intent_name)
        if artifact is None:
            return GateResult(
                passed=True,
                contract_id="",
                warnings=warnings,
                metadata={"skipped": True, "step_id": getattr(step, "id", "")},
            )

        result = self.bridge.check(artifact)
        result.warnings = warnings + result.warnings
        result.metadata = {**result.metadata, "step_id": getattr(step, "id", "")}
        return result

    def check_plan(self, plan: Any, intent: Any) -> list[dict[str, Any]]:
        intent_name = str(getattr(intent, "intent", "") or plan.metadata.get("intent", ""))
        results: list[dict[str, Any]] = []
        for step in getattr(plan, "steps", []) or []:
            gate = self.check_step(step, intent_name=intent_name)
            results.append(
                {
                    "step_id": getattr(step, "id", ""),
                    "action": getattr(step, "action", ""),
                    "contract_id": gate.contract_id,
                    "passed": gate.passed,
                    "skipped": gate.metadata.get("skipped", False),
                    "violations": gate.violations,
                    "warnings": gate.warnings,
                    "score": gate.score,
                    "metadata": gate.metadata,
                }
            )
        return results

    def validate_plan(self, plan: Any, intent: Any) -> list[dict[str, Any]]:
        results = self.check_plan(plan, intent)
        if any(not item["passed"] for item in results):
            raise PlanContractViolation(results)
        return results


def check_plan_contracts(plan: Any, intent: Any, *, bridge: Optional[RuntimeBridge] = None) -> dict[str, Any]:
    """Return structured contract check results for a plan."""
    gate = PlanStepGate(bridge=bridge)
    results = gate.check_plan(plan, intent)
    return {
        "enabled": True,
        "passed": all(item["passed"] for item in results),
        "steps": results,
    }


def validate_plan_contracts_if_enabled(plan: Any, intent: Any) -> dict[str, Any] | None:
    """Validate plan contracts when NLP2CMD_INTRACT_GATE is enabled."""
    if not intract_gate_enabled():
        return None
    return check_plan_contracts(plan, intent)
