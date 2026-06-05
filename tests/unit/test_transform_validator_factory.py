"""Tests for transform validator factory and pact-ir bindings."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nlp2cmd.validators.factory import TransformValidator, build_transform_validator
from scripts.generate_intract_manifest import generate_manifest


def test_bindings_include_pact_ir_shell_list() -> None:
    _, bindings, _ = generate_manifest()
    assert bindings["action_to_contract"]["shell_list"] == "action.shell_list"
    assert bindings["contract_to_registry"]["action.shell_list"]["registry"] == "pact_ir"
    policy = bindings["contract_policy"]["action.shell_list"]
    assert "eval" in policy["forbid"]


def test_bindings_include_planner_intent_aliases() -> None:
    _, bindings, _ = generate_manifest()
    assert bindings["intent_to_contract"]["find"] == bindings["intent_to_contract"]["file_search"]
    assert bindings["intent_to_contract"]["ls"] == bindings["intent_to_contract"]["list"]


def test_build_transform_validator_includes_shell_validator() -> None:
    validator = build_transform_validator("shell")
    assert validator is not None


def test_build_transform_validator_adds_intract_when_gate_enabled(monkeypatch) -> None:
    monkeypatch.setenv("NLP2CMD_INTRACT_GATE", "1")
    validator = build_transform_validator("shell")
    assert isinstance(validator, TransformValidator)
    assert len(validator.validators) == 2


def test_transform_validator_blocks_destructive_shell_with_intract(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("NLP2CMD_INTRACT_GATE", "1")

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

    from nlp2cmd.intract.validator import IntractValidator
    from nlp2cmd.intract.runtime_bridge import RuntimeBridge
    from nlp2cmd.validators.shell_validator import ShellValidator

    bridge = RuntimeBridge(bindings_path=bindings_path, manifest_path=manifest_path)
    validator = TransformValidator([ShellValidator(), IntractValidator(bridge=bridge)])

    class _Plan:
        intent = "file_search"
        domain = "shell"
        entities = {"path": "/"}

    ok = validator.validate("find . -type f", _Plan())
    assert ok.is_valid

    bad = validator.validate("rm -rf /", _Plan())
    assert not bad.is_valid
    assert bad.errors
