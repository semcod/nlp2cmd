"""Tests for ExecutionPlanIR PlanStep Intract gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nlp2cmd.intract.plan_gate import PlanContractViolation, PlanStepGate
from nlp2cmd.intract.runtime_bridge import RuntimeBridge
from pact_ir import ExecutionPlanIR, IntentIR, PlanStep, TargetKind


@pytest.fixture
def gate(tmp_path: Path) -> PlanStepGate:
    repo = tmp_path / "repo"
    repo.mkdir()
    bindings = {
        "intent_to_contract": {"find": "intent.file_search"},
        "action_to_contract": {"shell_find": "action.shell_find"},
        "contract_policy": {
            "action.shell_find": {
                "forbid": ["write", "delete", "network", "eval"],
                "require": ["validate.pre_execute"],
            }
        },
    }
    bindings_path = repo / "bindings.json"
    bindings_path.write_text(json.dumps(bindings), encoding="utf-8")
    manifest_path = repo / "intract.yaml"
    manifest_path.write_text(
        """
version: intract.v1
contracts:
  - id: action.shell_find
    scope: action
    intent: search:files
    domain: shell
    input: [path, name]
    output: [file_list]
    effect: [read]
""".strip(),
        encoding="utf-8",
    )
    bridge = RuntimeBridge(bindings_path=bindings_path, manifest_path=manifest_path)
    return PlanStepGate(bridge=bridge)


def _sample_plan() -> tuple[IntentIR, ExecutionPlanIR]:
    intent = IntentIR(
        query="znajdź pliki *.py",
        intent="find",
        target_kind=TargetKind.SHELL,
        confidence=0.95,
    )
    step = PlanStep(
        id="s1",
        action="shell_find",
        target_kind=TargetKind.SHELL,
        params={"path": "src", "name": "*.py"},
        dsl='find src -name "*.py"',
    )
    plan = ExecutionPlanIR.from_intent(intent, steps=[step], source="rule_shell")
    return intent, plan


def test_plan_gate_allows_safe_find(gate: PlanStepGate) -> None:
    intent, plan = _sample_plan()
    results = gate.check_plan(plan, intent)
    assert len(results) == 1
    assert results[0]["passed"] is True
    assert results[0]["contract_id"] == "action.shell_find"


def test_plan_gate_blocks_destructive_shell(gate: PlanStepGate) -> None:
    intent, plan = _sample_plan()
    plan.steps[0].dsl = "rm -rf /"
    with pytest.raises(PlanContractViolation):
        gate.validate_plan(plan, intent)


def test_plan_gate_resolves_shell_list_with_default_bindings() -> None:
    gate = PlanStepGate()
    intent = IntentIR(
        query="pokaż katalog src",
        intent="list",
        target_kind=TargetKind.SHELL,
        confidence=0.95,
    )
    step = PlanStep(
        id="s1",
        action="shell_list",
        target_kind=TargetKind.SHELL,
        params={"path": "src"},
        dsl="ls -la src",
    )
    plan = ExecutionPlanIR.from_intent(intent, steps=[step], source="rule_shell")
    results = gate.check_plan(plan, intent)
    assert results[0]["contract_id"] == "action.shell_list"
    assert results[0]["passed"] is True


def test_plan_query_blocks_low_confidence_intent():
    pytest.importorskip("nlp2cmd_planner")
    pytest.importorskip("nlp2cmd_propact")

    from nlp2cmd.bridge.integration import plan_query_via_integration
    from nlp2cmd_intent import IntentClarificationRequired

    with pytest.raises(IntentClarificationRequired):
        plan_query_via_integration("xyz")
