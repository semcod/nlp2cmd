"""Runtime bridge between nlp2cmd artifacts and Intract contract rules."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Optional

import yaml

from nlp2cmd.intract.color_validation import is_valid_hex_color

try:
    from intract.core.models import ContractRecord
    from intract.parsers.manifest import contract_from_mapping
    from intract.signature import build_signatures
    from intract.validators.engine import validate_contract_against_source
    from intract.validators.effects import detect_effects

    INTRACT_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    INTRACT_AVAILABLE = False


BINDINGS_PACKAGE = "nlp2cmd.data"
BINDINGS_FILENAME = "intract-bindings.json"


@dataclass
class RuntimeArtifact:
    contract_id: str
    intent: str
    dsl_kind: str
    dsl: str
    params: dict[str, Any] = field(default_factory=dict)
    effects_observed: list[str] = field(default_factory=list)


@dataclass
class GateResult:
    passed: bool
    contract_id: str
    score: float = 1.0
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _default_bindings_path() -> Path:
    with resources.as_file(resources.files(BINDINGS_PACKAGE) / BINDINGS_FILENAME) as path:
        return Path(path)


def _find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "intract.yaml").exists():
            return candidate
    return start


def _infer_effects_from_dsl(artifact: RuntimeArtifact) -> list[str]:
    if artifact.effects_observed:
        return list(artifact.effects_observed)

    effects: set[str] = set()
    if INTRACT_AVAILABLE:
        effects.update(detect_effects(artifact.dsl))

    dsl_lower = artifact.dsl.lower()
    if artifact.dsl_kind == "shell":
        if any(token in dsl_lower for token in ("curl", "wget", "nc ", "ssh ")):
            effects.add("network")
        if any(token in dsl_lower for token in ("rm ", "mv ", "cp ", "chmod", "mkdir", "touch")):
            effects.add("write")
        if "rm " in dsl_lower:
            effects.add("delete")
        if any(token in dsl_lower for token in ("cat ", "ls ", "find ", "grep ", "head ", "tail ")):
            effects.add("read")
    elif artifact.dsl_kind == "dom":
        effects.update({"read", "network"})
        if any(token in dsl_lower for token in ("fill", "click", "type", "submit")):
            effects.add("write")
        if any(
            token in dsl_lower
            for token in (
                "draw_",
                "set_color",
                "set_line_width",
                "fill_at",
                "click_canvas",
                "select_tool",
            )
        ):
            effects.add("write_canvas")
        if "wait_for_canvas" in dsl_lower or "get_canvas_center" in dsl_lower:
            effects.add("read_canvas")
    elif artifact.dsl_kind == "sql":
        if re.search(r"\b(select|show|describe)\b", dsl_lower):
            effects.add("read")
        if re.search(r"\b(insert|update|delete|drop|truncate)\b", dsl_lower):
            effects.add("write")
        if re.search(r"\bdelete\b", dsl_lower):
            effects.add("delete")

    return sorted(effects)


def build_runtime_source(artifact: RuntimeArtifact) -> str:
    """Build a structural source snippet for Intract effect/input rules."""
    effects = _infer_effects_from_dsl(artifact)
    inputs = ",".join(sorted(str(k) for k in artifact.params))
    effect_decl = ",".join(effects) if effects else "none"
    return (
        f"# @intract.v1 scope:runtime intent:{artifact.intent}\n"
        f"# input:{inputs or 'none'}\n"
        f"# effect:{effect_decl}\n"
        f"{artifact.dsl}\n"
    )


class RuntimeBridge:
    """Validate runtime artifacts against generated Intract bindings."""

    def __init__(self, bindings_path: Optional[Path] = None, manifest_path: Optional[Path] = None):
        self.bindings_path = bindings_path or _default_bindings_path()
        self.bindings = self._load_bindings(self.bindings_path)
        self.contract_policy: dict[str, Any] = self.bindings.get("contract_policy", {})
        self.manifest_path = manifest_path or (_find_repo_root(self.bindings_path) / "intract.yaml")

    @staticmethod
    def _load_bindings(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def resolve_contract_id(
        self,
        *,
        intent: Optional[str] = None,
        action_name: Optional[str] = None,
        dom_action: Optional[str] = None,
    ) -> Optional[str]:
        if dom_action:
            return self.bindings.get("dom_to_contract", {}).get(dom_action)
        if action_name:
            return self.bindings.get("action_to_contract", {}).get(action_name)
        if intent:
            return self.bindings.get("intent_to_contract", {}).get(intent)
        return None

    def check_policy(self, artifact: RuntimeArtifact) -> GateResult:
        policy = self.contract_policy.get(artifact.contract_id, {})
        violations: list[str] = []
        warnings: list[str] = []

        observed = set(_infer_effects_from_dsl(artifact))
        for forbidden in policy.get("forbid", []):
            normalized = forbidden.lower()
            if normalized in observed:
                violations.append(f"forbid:{forbidden} violated by observed effect '{normalized}'")
            elif normalized == "eval" and "eval" in artifact.dsl.lower():
                violations.append("forbid:eval violated in DSL")
            elif normalized in {"recursive_root", "wildcard_delete"}:
                if "rm " in artifact.dsl and ("-rf /" in artifact.dsl or " *" in artifact.dsl):
                    violations.append(f"forbid:{forbidden} violated in shell DSL")
            elif normalized == "invalid_hex_color":
                color = str(artifact.params.get("color", "") or "")
                if color and not is_valid_hex_color(color):
                    violations.append(
                        "forbid:invalid_hex_color violated — expected #RGB, #RRGGBB, or #RRGGBBAA",
                    )

        required_inputs: list[str] = []
        for req in policy.get("require", []):
            if req == "confirm.destructive":
                warnings.append("confirm.destructive required — ensure caller confirmed execution")
            elif req in {"validate.pre_execute", "validate.step_pre"}:
                required_inputs.append(req)

        return GateResult(
            passed=not violations,
            contract_id=artifact.contract_id,
            violations=violations,
            warnings=warnings,
            metadata={"policy": policy, "observed_effects": sorted(observed), "required_inputs": required_inputs},
        )

    def check(self, artifact: RuntimeArtifact) -> GateResult:
        policy_result = self.check_policy(artifact)
        if not INTRACT_AVAILABLE:
            policy_result.warnings.append("intract package not installed — policy-only gate")
            return policy_result

        contract = self._find_contract_in_manifest(artifact.contract_id)
        if contract is None:
            policy_result.warnings.append(f"contract not found in manifest: {artifact.contract_id}")
            return policy_result

        policy = self.contract_policy.get(artifact.contract_id, {})
        record = {
            "id": contract.get("id", artifact.contract_id),
            "scope": contract.get("scope", "runtime"),
            "intent": contract.get("intent", artifact.intent),
            "domain": contract.get("domain", ""),
            "input": contract.get("input", []),
            "output": contract.get("output", []),
            "effect": contract.get("effect", []),
            "forbid": policy.get("forbid", []),
            "validate": ["input_presence", "no_forbidden_effect"],
        }
        contract_obj = contract_from_mapping(record)
        signature = build_signatures(
            [ContractRecord(contract=contract_obj, file_path="<runtime>", start_line=1, end_line=1)]
        )[0]
        result = validate_contract_against_source(signature, build_runtime_source(artifact))

        violations = list(policy_result.violations)
        violations.extend(issue.message for issue in result.violations)
        passed = policy_result.passed and result.status.value in {"pass", "partial"}

        return GateResult(
            passed=passed,
            contract_id=artifact.contract_id,
            score=result.score,
            violations=violations,
            warnings=policy_result.warnings,
            metadata={**policy_result.metadata, "intract_status": result.status.value},
        )

    def _find_contract_in_manifest(self, contract_id: str) -> Optional[dict[str, Any]]:
        if not self.manifest_path.exists():
            return None
        data = yaml.safe_load(self.manifest_path.read_text(encoding="utf-8"))
        for contract in data.get("contracts", []):
            if contract.get("id") == contract_id:
                return contract
        return None
