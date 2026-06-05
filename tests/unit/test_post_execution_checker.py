"""Tests for post-execution stdout validation."""

from __future__ import annotations

import pytest

from nlp2cmd.post_execution.checker import (
    PostCheckViolation,
    check_plan_outputs,
    check_step_output,
    infer_post_check_spec,
    post_check_enabled,
)
from nlp2cmd_propact.runner import RunResult
from pact_ir import ExecutionPlanIR, IntentIR, PlanStep, TargetKind


def _find_step() -> PlanStep:
    return PlanStep(
        id="s1",
        action="shell_find",
        target_kind=TargetKind.SHELL,
        params={"path": "src", "name": "*.py"},
        dsl='find src -name "*.py"',
    )


def test_infer_post_check_spec_for_shell_find() -> None:
    spec = infer_post_check_spec(_find_step())
    assert spec["returncode"] == 0
    assert spec["line_regex"] == r"\.py$"


def test_check_step_output_passes_matching_lines() -> None:
    result = check_step_output(
        _find_step(),
        stdout="src/foo.py\nsrc/bar.py\n",
        returncode=0,
    )
    assert result.passed


def test_check_step_output_fails_wrong_extension() -> None:
    result = check_step_output(
        _find_step(),
        stdout="src/foo.txt\n",
        returncode=0,
    )
    assert not result.passed
    assert result.violations


def test_explicit_metadata_post_check() -> None:
    step = PlanStep(
        id="s1",
        action="custom",
        target_kind=TargetKind.SHELL,
        metadata={"post_check": {"min_lines": 2, "returncode": 0}},
        dsl="echo a; echo b",
    )
    ok = check_step_output(step, stdout="a\nb\n", returncode=0)
    assert ok.passed
    bad = check_step_output(step, stdout="a\n", returncode=0)
    assert not bad.passed


def test_check_plan_outputs_with_execution_metadata() -> None:
    intent = IntentIR(query="q", intent="find", target_kind=TargetKind.SHELL, confidence=0.9)
    plan = ExecutionPlanIR.from_intent(intent, steps=[_find_step()], source="rule_shell")
    execution = RunResult(
        success=True,
        markdown="",
        stdout="src/a.py\n",
        metadata={
            "steps": [
                {
                    "step": "s1",
                    "success": True,
                    "stdout": "src/a.py\n",
                    "stderr": "",
                    "metadata": {"returncode": 0},
                }
            ]
        },
    )
    payload = check_plan_outputs(plan, intent, execution)
    assert payload["passed"] is True
    assert payload["steps"][0]["passed"] is True


def test_post_check_violation_raises_in_strict_mode(monkeypatch) -> None:
    monkeypatch.setenv("NLP2CMD_POST_CHECK_STRICT", "1")
    intent = IntentIR(query="q", intent="find", target_kind=TargetKind.SHELL, confidence=0.9)
    plan = ExecutionPlanIR.from_intent(intent, steps=[_find_step()], source="rule_shell")
    execution = RunResult(
        success=True,
        markdown="",
        stdout="src/a.txt\n",
        metadata={
            "steps": [
                {
                    "step": "s1",
                    "success": True,
                    "stdout": "src/a.txt\n",
                    "stderr": "",
                    "metadata": {"returncode": 0},
                }
            ]
        },
    )
    with pytest.raises(PostCheckViolation):
        check_plan_outputs(plan, intent, execution)


def test_post_check_enabled_env(monkeypatch) -> None:
    assert not post_check_enabled()
    monkeypatch.setenv("NLP2CMD_POST_CHECK", "1")
    assert post_check_enabled()
