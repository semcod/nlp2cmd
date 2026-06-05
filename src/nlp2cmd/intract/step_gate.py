"""Intract pre/post gate wrapper for browser StepValidator."""

from __future__ import annotations

from typing import Any, Optional

from nlp2cmd.intract.pipeline_gate import intract_gate_enabled
from nlp2cmd.intract.color_validation import is_valid_hex_color
from nlp2cmd.intract.runtime_bridge import RuntimeArtifact, RuntimeBridge
from nlp2cmd.automation.step_validator import ValidationResult


def _dom_dsl(action: str, params: dict[str, Any]) -> str:
    if not params:
        return action
    parts = [action]
    for key in sorted(params):
        value = params[key]
        if value is None or value == "":
            continue
        parts.append(f"{key}={value}")
    return " ".join(parts)


class IntractStepGate:
    """Wrap StepValidator with Intract contract checks for DOM plan steps."""

    def __init__(
        self,
        inner: Any | None = None,
        bridge: Optional[RuntimeBridge] = None,
        *,
        enabled: Optional[bool] = None,
    ):
        self.inner = inner
        self.bridge = bridge or RuntimeBridge()
        self.enabled = intract_gate_enabled() if enabled is None else enabled
        self._stats: dict[str, int] = {
            "pre_checked": 0,
            "post_checked": 0,
            "passed": 0,
            "failed": 0,
            "skipped_no_contract": 0,
        }
        self._last_results: list[dict[str, Any]] = []

    def summary(self) -> dict[str, Any]:
        """Runtime gate statistics for shell / YAML reporting."""
        from nlp2cmd.intract.runtime_bridge import INTRACT_AVAILABLE

        return {
            "enabled": self.enabled,
            "intract_installed": INTRACT_AVAILABLE,
            **self._stats,
            "recent": self._last_results[-5:],
        }

    def _record(
        self,
        *,
        phase: str,
        action: str,
        contract_id: str | None,
        passed: bool,
        skipped: bool = False,
        message: str = "",
    ) -> None:
        key = f"{phase}_checked"
        if key in self._stats:
            self._stats[key] += 1
        if skipped:
            self._stats["skipped_no_contract"] += 1
        elif passed:
            self._stats["passed"] += 1
        else:
            self._stats["failed"] += 1
        self._last_results.append({
            "phase": phase,
            "action": action,
            "contract_id": contract_id or "",
            "passed": passed,
            "skipped": skipped,
            "message": message,
        })

    def _missing_required_inputs(self, contract_id: str, params: dict[str, Any]) -> list[str]:
        contract = self.bridge._find_contract_in_manifest(contract_id)
        if not contract:
            return []
        missing: list[str] = []
        for field in contract.get("input", []):
            value = params.get(field)
            if value is None or value == "":
                missing.append(str(field))
        return missing

    def _policy_param_violations(
        self,
        contract_id: str,
        action: str,
        params: dict[str, Any],
    ) -> list[str]:
        policy = self.bridge.contract_policy.get(contract_id, {})
        violations: list[str] = []
        if "invalid_hex_color" not in policy.get("forbid", []):
            return violations
        if action != "set_color":
            return violations
        color = str(params.get("color", "") or "")
        if color and not is_valid_hex_color(color):
            violations.append(
                "invalid hex color (expected #RGB, #RRGGBB, or #RRGGBBAA)",
            )
        return violations

    def _contract_check(
        self,
        action: str,
        params: dict[str, Any],
        *,
        phase: str,
        result: Optional[str] = None,
    ) -> Optional[ValidationResult]:
        if not self.enabled:
            return None

        contract_id = self.bridge.resolve_contract_id(dom_action=action)
        if not contract_id:
            self._record(
                phase=phase,
                action=action,
                contract_id=None,
                passed=True,
                skipped=True,
            )
            return None

        if phase == "pre":
            missing = self._missing_required_inputs(contract_id, params)
            if missing:
                self._record(
                    phase=phase,
                    action=action,
                    contract_id=contract_id,
                    passed=False,
                    message=f"missing inputs: {', '.join(missing)}",
                )
                return ValidationResult(
                    passed=False,
                    message=f"Intract pre-check missing required inputs: {', '.join(missing)}",
                    details={"contract_id": contract_id, "missing_inputs": missing},
                    suggestion="Provide required step parameters before execution",
                )
            param_violations = self._policy_param_violations(contract_id, action, params)
            if param_violations:
                message = f"Intract pre-check failed for {action}: " + "; ".join(param_violations)
                self._record(
                    phase=phase,
                    action=action,
                    contract_id=contract_id,
                    passed=False,
                    message=message,
                )
                return ValidationResult(
                    passed=False,
                    message=message,
                    details={"contract_id": contract_id, "violations": param_violations},
                    suggestion="Use a valid #RRGGBB hex color for set_color",
                )

        dsl = _dom_dsl(action, params)
        if phase == "post" and result:
            dsl = f"{dsl}\n# result={result}"

        artifact = RuntimeArtifact(
            contract_id=contract_id,
            intent=str(self.bridge.bindings.get("dom_to_contract", {}).get(action, action)),
            dsl_kind="dom",
            dsl=dsl,
            params=params,
        )
        gate = self.bridge.check(artifact)
        intract_status = gate.metadata.get("intract_status")
        if gate.passed and intract_status in {None, "pass"}:
            self._record(
                phase=phase,
                action=action,
                contract_id=contract_id,
                passed=True,
            )
            return None
        if gate.passed and phase == "post" and intract_status == "partial":
            self._record(
                phase=phase,
                action=action,
                contract_id=contract_id,
                passed=True,
                message="partial",
            )
            return None

        message = f"Intract {phase}-check failed for {action}"
        if gate.violations:
            message = f"{message}: " + "; ".join(gate.violations)
        self._record(
            phase=phase,
            action=action,
            contract_id=contract_id,
            passed=False,
            message=message,
        )
        return ValidationResult(
            passed=False,
            message=message,
            details={
                "contract_id": gate.contract_id,
                "phase": phase,
                "violations": gate.violations,
                "warnings": gate.warnings,
                "score": gate.score,
            },
            suggestion="Adjust step params or update Intract contract policy",
        )

    def validate_pre(
        self,
        action: str,
        page: Any,
        params: dict,
        variables: dict,
    ) -> ValidationResult:
        if self.inner is not None:
            inner_result = self.inner.validate_pre(action, page, params, variables)
            if not inner_result.passed:
                return inner_result

        blocked = self._contract_check(action, params or {}, phase="pre")
        if blocked is not None:
            return blocked

        if self.inner is not None:
            return ValidationResult(True)
        return ValidationResult(True)

    def validate_post(
        self,
        action: str,
        page: Any,
        params: dict,
        result: Optional[str],
    ) -> ValidationResult:
        if self.inner is not None:
            inner_result = self.inner.validate_post(action, page, params, result)
            if not inner_result.passed:
                return inner_result

        blocked = self._contract_check(action, params or {}, phase="post", result=result)
        if blocked is not None:
            return blocked

        return ValidationResult(True)

    def snapshot_clipboard(self) -> str:
        if self.inner is not None and hasattr(self.inner, "snapshot_clipboard"):
            return self.inner.snapshot_clipboard()
        return ""

    def __getattr__(self, name: str) -> Any:
        if self.inner is not None:
            return getattr(self.inner, name)
        raise AttributeError(name)
