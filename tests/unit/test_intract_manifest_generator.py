"""Tests for Intract manifest generation."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.generate_intract_manifest import generate_manifest, write_outputs


def test_generate_manifest_has_expected_layers(tmp_path: Path) -> None:
    manifest, bindings, policy = generate_manifest()

    scopes = {c["scope"] for c in manifest["contracts"]}
    assert "action" in scopes
    assert "intent" in scopes
    assert "dom_action" in scopes
    assert "canvas_step" in scopes

    assert manifest["version"] == "intract.v1"
    assert manifest["project"]["name"] == "nlp2cmd"
    assert "files" in manifest
    assert "guard.shell_safety" in {c["id"] for c in manifest["files"]["src/nlp2cmd/validators/shell_validator.py"]}


def test_action_contracts_reference_registry_not_params() -> None:
    manifest, bindings, _ = generate_manifest()

    shell_find = next(c for c in manifest["contracts"] if c["id"] == "action.shell_find")
    assert shell_find["domain"] == "shell"
    assert "path" in shell_find["input"]
    assert "forbid" not in shell_find
    assert "ActionRegistry:shell_find" in shell_find["meaning"]

    shell_policy = bindings["contract_policy"]["action.shell_find"]
    assert "eval" in shell_policy["forbid"]

    # Param types stay in registry bindings, not in contract body.
    assert "ParamType" not in json.dumps(shell_find)
    assert bindings["contract_to_registry"]["action.shell_find"]["registry"] == "ActionRegistry"


def test_detects_missing_router_bindings() -> None:
    _, bindings, _ = generate_manifest()

    missing_actions = {item["expected_action"] for item in bindings["missing_bindings"]}
    assert "shell_file_op" in missing_actions
    assert "k8s_describe" in missing_actions
    assert "docker_build" in missing_actions
    assert "shell_network" in missing_actions
    assert "shell_process" in missing_actions


def test_write_outputs_roundtrip(tmp_path: Path) -> None:
    manifest, bindings, policy = generate_manifest()
    manifest_path = tmp_path / "intract.yaml"
    bindings_path = tmp_path / "bindings.json"
    policy_path = tmp_path / "policy.json"

    write_outputs(
        manifest,
        bindings,
        policy,
        manifest_path=manifest_path,
        bindings_path=bindings_path,
        policy_path=policy_path,
    )

    loaded = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert loaded["project"]["name"] == "nlp2cmd"
    assert len(loaded["contracts"]) == len(manifest["contracts"])

    loaded_bindings = json.loads(bindings_path.read_text(encoding="utf-8"))
    assert loaded_bindings["intent_to_action"]["select"] == "sql_select"
    assert loaded_bindings["dom_to_contract"]["goto"] == "dom.goto"
    assert loaded_bindings["dom_to_contract"]["draw_filled_circle"] == "dom.draw_filled_circle"
    assert loaded_bindings["dom_to_contract"]["set_color"] == "dom.set_color"


def test_canvas_step_contracts_have_inputs() -> None:
    manifest, bindings, _ = generate_manifest()
    draw = next(c for c in manifest["contracts"] if c["id"] == "dom.draw_filled_circle")
    color = next(c for c in manifest["contracts"] if c["id"] == "dom.set_color")
    assert draw["scope"] == "canvas_step"
    assert "radius" in draw["input"]
    assert "color" in color["input"]
    assert bindings["contract_to_registry"]["dom.set_color"]["registry"] == "HandlerRegistry"


def test_pact_ir_plan_actions_in_bindings() -> None:
    manifest, bindings, _ = generate_manifest()
    shell_list = next(c for c in manifest["contracts"] if c["id"] == "action.shell_list")
    assert shell_list["scope"] == "plan_action"
    assert "path" in shell_list["input"]
    assert bindings["action_to_contract"]["shell_list"] == "action.shell_list"
    assert bindings["intent_to_contract"]["find"] == bindings["intent_to_contract"]["file_search"]
