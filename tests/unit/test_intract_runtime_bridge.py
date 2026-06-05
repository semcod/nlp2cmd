"""Tests for Intract runtime bridge and validator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nlp2cmd.intract.runtime_bridge import RuntimeArtifact, RuntimeBridge, build_runtime_source
from nlp2cmd.intract.validator import IntractValidator


@pytest.fixture
def bridge(tmp_path: Path) -> RuntimeBridge:
    repo = tmp_path / "repo"
    repo.mkdir()
    bindings = {
        "intent_to_contract": {"file_search": "intent.file_search"},
        "action_to_contract": {"shell_find": "action.shell_find"},
        "contract_policy": {
            "intent.file_search": {
                "preferred_action": "action.shell_find",
                "forbid": ["write", "delete", "network", "eval"],
                "require": ["validate.pre_execute"],
            },
            "action.shell_find": {
                "forbid": ["write", "delete", "network", "eval"],
                "require": [],
            },
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
  - id: action.shell_find
    scope: action
    intent: find:files
    domain: shell
    input: [path, glob]
    output: [file_list]
    effect: [read]
""".strip(),
        encoding="utf-8",
    )
    return RuntimeBridge(bindings_path=bindings_path, manifest_path=manifest_path)


def test_build_runtime_source_includes_effects() -> None:
    artifact = RuntimeArtifact(
        contract_id="action.shell_find",
        intent="find:files",
        dsl_kind="shell",
        dsl="find . -name '*.py'",
        params={"path": ".", "glob": "*.py"},
    )
    source = build_runtime_source(artifact)
    assert "scope:runtime" in source
    assert "find . -name '*.py'" in source
    assert "effect:" in source


def test_policy_gate_blocks_forbidden_shell_effects(bridge: RuntimeBridge) -> None:
    artifact = RuntimeArtifact(
        contract_id="action.shell_find",
        intent="find:files",
        dsl_kind="shell",
        dsl="rm -rf /tmp/*",
        params={"path": "/tmp"},
    )
    result = bridge.check_policy(artifact)
    assert not result.passed
    assert any("forbid:write" in item or "forbid:delete" in item for item in result.violations)


def test_policy_gate_allows_read_only_find(bridge: RuntimeBridge) -> None:
    artifact = RuntimeArtifact(
        contract_id="action.shell_find",
        intent="find:files",
        dsl_kind="shell",
        dsl="find . -type f -name '*.py'",
        params={"path": "."},
    )
    result = bridge.check_policy(artifact)
    assert result.passed


def test_validator_uses_intent_contract_mapping(bridge: RuntimeBridge) -> None:
    class _Plan:
        intent = "file_search"
        domain = "shell"
        entities = {"path": "."}

    validator = IntractValidator(bridge=bridge)
    ok = validator.validate("find . -type f", _Plan())
    assert ok.is_valid

    bad = validator.validate("rm -rf /", _Plan())
    assert not bad.is_valid
    assert bad.errors


def test_validator_warns_on_unmapped_intent(bridge: RuntimeBridge) -> None:
    class _Plan:
        intent = "unknown_intent"
        domain = "shell"
        entities = {}

    validator = IntractValidator(bridge=bridge)
    result = validator.validate("ls", _Plan())
    assert result.is_valid
    assert any("No Intract contract mapped" in w for w in result.warnings)
