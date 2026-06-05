"""Tests for PipelineRunner Intract pre-execute gate."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nlp2cmd.intract.pipeline_gate import PipelineRunnerGate
from nlp2cmd.intract.runtime_bridge import RuntimeBridge
from nlp2cmd.ir import ActionIR
from nlp2cmd.pipeline_runner import PipelineRunner


@pytest.fixture
def gate(tmp_path: Path) -> PipelineRunnerGate:
    repo = tmp_path / "repo"
    repo.mkdir()
    bindings = {
        "intent_to_contract": {"file_search": "intent.file_search"},
        "action_to_contract": {"shell_find": "action.shell_find"},
        "contract_policy": {
            "intent.file_search": {
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
  - id: intent.file_search
    scope: intent
    intent: search:files
    domain: shell
    input: [path, pattern]
    output: [file_list]
    effect: [read]
""".strip(),
        encoding="utf-8",
    )
    bridge = RuntimeBridge(bindings_path=bindings_path, manifest_path=manifest_path)
    return PipelineRunnerGate(bridge=bridge)


def test_pipeline_gate_blocks_destructive_shell(gate: PipelineRunnerGate) -> None:
    runner = PipelineRunner(headless=True, intract_gate=gate)
    ir = ActionIR(
        action_id="file_search",
        dsl="rm -rf /",
        dsl_kind="shell",
        params={"path": "/"},
        metadata={"intent": "file_search"},
    )

    runner._executor_registry = None
    with patch.object(runner, "_run_shell") as run_shell:
        result = runner.run(ir, dry_run=True, confirm=False)

    run_shell.assert_not_called()
    assert not result.success
    assert "Intract gate blocked execution" in (result.error or "")
    assert result.data.get("intract_gate", {}).get("passed") is False


def test_pipeline_gate_allows_safe_shell(gate: PipelineRunnerGate) -> None:
    runner = PipelineRunner(headless=True, intract_gate=gate)
    ir = ActionIR(
        action_id="file_search",
        dsl="find . -type f",
        dsl_kind="shell",
        params={"path": "."},
        metadata={"intent": "file_search"},
    )

    runner._executor_registry = None
    with patch.object(runner, "_run_shell") as run_shell:
        from nlp2cmd.pipeline_runner_utils import RunnerResult

        run_shell.return_value = RunnerResult(success=True, kind="shell", data={"stdout": "ok"})
        result = runner.run(ir, dry_run=True, confirm=False)

    run_shell.assert_called_once()
    assert result.success


def test_pipeline_gate_skips_unmapped_contract(gate: PipelineRunnerGate) -> None:
    runner = PipelineRunner(headless=True, intract_gate=gate)
    ir = ActionIR(
        action_id="unknown_action",
        dsl="echo hello",
        dsl_kind="shell",
        params={},
        metadata={},
    )

    runner._executor_registry = None
    with patch.object(runner, "_run_shell") as run_shell:
        from nlp2cmd.pipeline_runner_utils import RunnerResult

        run_shell.return_value = RunnerResult(success=True, kind="shell")
        result = runner.run(ir, dry_run=True, confirm=False)

    run_shell.assert_called_once()
    assert result.success
