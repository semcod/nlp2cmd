"""Tests for IntractStepGate browser step wrapper."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nlp2cmd.automation.step_validator import StepValidator, ValidationResult
from nlp2cmd.intract.runtime_bridge import RuntimeBridge
from nlp2cmd.intract.step_gate import IntractStepGate
from nlp2cmd.plan_execution.step_orchestrator import StepOrchestrator


@pytest.fixture
def bridge(tmp_path: Path) -> RuntimeBridge:
    repo = tmp_path / "repo"
    repo.mkdir()
    bindings = {
        "dom_to_contract": {
            "goto": "dom.goto",
            "navigate": "dom.goto",
            "fill_form": "dom.fill_form",
            "draw_filled_circle": "dom.draw_filled_circle",
            "set_color": "dom.set_color",
        },
        "contract_policy": {
            "dom.goto": {"forbid": ["local_file_access"], "require": ["validate.step_pre"]},
            "dom.fill_form": {"forbid": ["submit_without_confirm"], "require": []},
            "dom.draw_filled_circle": {"forbid": [], "require": []},
            "dom.set_color": {"forbid": ["invalid_hex_color"], "require": ["validate.step_pre"]},
        },
    }
    bindings_path = repo / "bindings.json"
    bindings_path.write_text(json.dumps(bindings), encoding="utf-8")
    manifest_path = repo / "intract.yaml"
    manifest_path.write_text(
        """
version: intract.v1
contracts:
  - id: dom.goto
    scope: dom_action
    intent: navigate:url
    domain: browser
    input: [url]
    output: [page_loaded]
    effect: [network, read]
  - id: dom.fill_form
    scope: dom_action
    intent: fill:form_field
    domain: browser
    input: [selector, value]
    output: [field_filled]
    effect: [write_dom]
  - id: dom.draw_filled_circle
    scope: canvas_step
    intent: canvas:draw_fill
    domain: browser
    input: [radius]
    output: [canvas_mutated]
    effect: [write_canvas]
  - id: dom.set_color
    scope: canvas_step
    intent: canvas:set_color
    domain: browser
    input: [color]
    output: [step_result]
    effect: [write_canvas]
""".strip(),
        encoding="utf-8",
    )
    return RuntimeBridge(bindings_path=bindings_path, manifest_path=manifest_path)


def test_step_gate_blocks_invalid_navigate_without_inner(bridge: RuntimeBridge) -> None:
    gate = IntractStepGate(inner=None, bridge=bridge, enabled=True)
    result = gate.validate_pre("goto", None, {}, {})
    assert not result.passed
    assert "missing required inputs: url" in result.message


def test_step_gate_passes_valid_navigate(bridge: RuntimeBridge) -> None:
    gate = IntractStepGate(inner=None, bridge=bridge, enabled=True)
    result = gate.validate_pre(
        "goto",
        None,
        {"url": "https://example.com"},
        {},
    )
    assert result.passed


def test_step_gate_delegates_to_inner_first(bridge: RuntimeBridge) -> None:
    inner = MagicMock()
    inner.validate_pre.return_value = ValidationResult(False, "inner failed")
    gate = IntractStepGate(inner=inner, bridge=bridge, enabled=True)

    result = gate.validate_pre("goto", None, {"url": "https://example.com"}, {})

    inner.validate_pre.assert_called_once()
    assert not result.passed
    assert result.message == "inner failed"


def test_step_orchestrator_fails_pre_check_via_intract_gate(bridge: RuntimeBridge) -> None:
    gate = IntractStepGate(inner=StepValidator(), bridge=bridge, enabled=True)
    orch = StepOrchestrator(validator=gate)
    step = MagicMock()
    step.action = "goto"
    step.params = {}
    step.description = "open page"
    console = MagicMock()

    pre_ok, pre_message = orch._pre_validate(step, None, lambda p, v: p, console)

    assert not pre_ok
    assert "missing required inputs: url" in pre_message


def test_step_gate_blocks_draw_without_radius(bridge: RuntimeBridge) -> None:
    gate = IntractStepGate(inner=None, bridge=bridge, enabled=True)
    result = gate.validate_pre("draw_filled_circle", None, {"offset": [0, 0]}, {})
    assert not result.passed
    assert "missing required inputs: radius" in result.message


def test_step_gate_passes_draw_with_radius(bridge: RuntimeBridge) -> None:
    gate = IntractStepGate(inner=None, bridge=bridge, enabled=True)
    result = gate.validate_pre(
        "draw_filled_circle",
        None,
        {"radius": 20, "offset": [0, -35]},
        {},
    )
    assert result.passed


def test_step_gate_blocks_invalid_hex_color(bridge: RuntimeBridge) -> None:
    gate = IntractStepGate(inner=None, bridge=bridge, enabled=True)
    result = gate.validate_pre("set_color", None, {"color": "red"}, {})
    assert not result.passed
    assert "invalid hex color" in result.message


def test_step_gate_passes_valid_hex_color(bridge: RuntimeBridge) -> None:
    gate = IntractStepGate(inner=None, bridge=bridge, enabled=True)
    result = gate.validate_pre("set_color", None, {"color": "#FF8040"}, {})
    assert result.passed


def test_step_gate_summary_tracks_checks(bridge: RuntimeBridge) -> None:
    gate = IntractStepGate(inner=None, bridge=bridge, enabled=True)
    gate.validate_pre("goto", None, {"url": "https://example.com"}, {})
    gate.validate_pre("unknown_action", None, {}, {})
    summary = gate.summary()
    assert summary["enabled"] is True
    assert summary["pre_checked"] == 2
    assert summary["passed"] >= 1
    assert summary["skipped_no_contract"] >= 1


def test_plan_executor_wraps_validator_when_env_enabled(bridge: RuntimeBridge, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NLP2CMD_INTRACT_GATE", "1")
    from nlp2cmd.plan_execution.plan_executor import PlanExecutor

    executor = PlanExecutor()
    orchestrator = executor._create_orchestrator(MagicMock(query="test"))

    assert isinstance(orchestrator.validator, IntractStepGate)
