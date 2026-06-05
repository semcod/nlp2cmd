#!/usr/bin/env python3
"""Generate intract.yaml and bindings from nlp2cmd registry sources."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from nlp2cmd.dom_actions.registry import ActionRegistry as DomActionRegistry
from nlp2cmd.registry.action_registry import ActionRegistry
from nlp2cmd.registry.action_schema import ActionSchema
from nlp2cmd.step_handlers.registry import HandlerRegistry

ROUTER_CONFIG = REPO_ROOT / "src" / "nlp2cmd" / "data" / "router_config.json"
OUT_MANIFEST = REPO_ROOT / "intract.yaml"
OUT_BINDINGS = REPO_ROOT / "src" / "nlp2cmd" / "data" / "intract-bindings.json"
OUT_POLICY = REPO_ROOT / "src" / "nlp2cmd" / "data" / "intract-policy.json"

INTENT_SEMANTICS: dict[str, str] = {
    "select": "query:table",
    "get": "get:resource",
    "list": "list:resources",
    "show": "show:resource",
    "count": "count:resources",
    "describe": "describe:resource",
    "status": "read:status",
    "version": "read:version",
    "help": "read:help",
    "insert": "mutate:insert",
    "update": "mutate:update",
    "delete": "delete:resource",
    "aggregate": "aggregate:data",
    "analyze": "analyze:data",
    "compare": "compare:data",
    "migrate": "migrate:resource",
    "refactor": "refactor:resource",
    "optimize": "optimize:resource",
    "diagnose": "diagnose:system",
    "report": "report:summary",
    "audit": "audit:compliance",
    "file_search": "search:files",
    "file_operation": "mutate:file",
    "process_monitoring": "monitor:processes",
    "network": "inspect:network",
    "container_run": "run:container",
    "container_stop": "stop:container",
    "container_list": "list:containers",
    "image_build": "build:image",
    "scale": "scale:deployment",
    "logs": "read:logs",
}

ACTION_INTENT_OVERRIDES: dict[str, str] = {
    "sql_select": "query:select",
    "sql_insert": "mutate:insert",
    "sql_update": "mutate:update",
    "sql_delete": "mutate:delete",
    "sql_aggregate": "aggregate:query",
    "shell_find": "find:files",
    "shell_read_file": "read:file",
    "shell_count_pattern": "count:pattern",
    "shell_process_list": "list:processes",
    "docker_ps": "list:containers",
    "docker_run": "run:container",
    "docker_stop": "stop:container",
    "docker_logs": "read:container_logs",
    "k8s_get": "get:k8s_resource",
    "k8s_scale": "scale:deployment",
    "k8s_logs": "read:pod_logs",
    "summarize_results": "summarize:data",
    "filter_results": "filter:data",
    "sort_results": "sort:data",
}

DOM_INTENT_OVERRIDES: dict[str, str] = {
    "goto": "navigate:url",
    "navigate": "navigate:url",
    "explore_for_content": "explore:page_content",
    "explore_for_form": "explore:form",
    "fill_form": "fill:form_field",
    "extract_companies": "extract:structured_data",
    "extract_company_websites_deep": "extract:structured_data",
    "save_to_file": "persist:data",
    "save_to_csv": "persist:csv",
}

DOM_FORBID: dict[str, list[str]] = {
    "goto": ["local_file_access", "credential_exfil"],
    "navigate": ["local_file_access", "credential_exfil"],
    "fill_form": ["submit_without_confirm", "password_autofill"],
    "extract_companies": ["network_post_extract"],
    "extract_company_websites_deep": ["network_post_extract"],
    "save_to_file": ["overwrite_system_path"],
    "save_to_csv": ["overwrite_system_path"],
}

# Canvas / browser step handlers (HandlerRegistry) — not in DomActionRegistry.
CANVAS_STEP_ACTIONS: frozenset[str] = frozenset({
    "screenshot",
    "wait",
    "wait_for_canvas",
    "get_canvas_center",
    "select_tool",
    "set_color",
    "set_line_width",
    "draw_circle",
    "draw_filled_circle",
    "draw_filled_ellipse",
    "draw_filled_rectangle",
    "draw_rectangle",
    "draw_ellipse",
    "draw_arc",
    "draw_polygon",
    "draw_bezier",
    "draw_svg_path",
    "draw_line",
    "fill_at",
    "click_canvas",
})

CANVAS_STEP_INTENTS: dict[str, str] = {
    "screenshot": "browser:screenshot",
    "wait": "browser:wait",
    "wait_for_canvas": "canvas:wait_ready",
    "get_canvas_center": "canvas:measure_center",
    "select_tool": "canvas:select_tool",
    "set_color": "canvas:set_color",
    "set_line_width": "canvas:set_stroke_width",
    "draw_circle": "canvas:draw_stroke",
    "draw_filled_circle": "canvas:draw_fill",
    "draw_filled_ellipse": "canvas:draw_fill",
    "draw_filled_rectangle": "canvas:draw_fill",
    "draw_rectangle": "canvas:draw_stroke",
    "draw_ellipse": "canvas:draw_stroke",
    "draw_arc": "canvas:draw_stroke",
    "draw_polygon": "canvas:draw_shape",
    "draw_bezier": "canvas:draw_shape",
    "draw_svg_path": "canvas:draw_path",
    "draw_line": "canvas:draw_stroke",
    "fill_at": "canvas:flood_fill",
    "click_canvas": "canvas:click",
}

CANVAS_STEP_INPUTS: dict[str, list[str]] = {
    "set_color": ["color"],
    "set_line_width": ["width"],
    "select_tool": ["tool"],
    "draw_filled_circle": ["radius"],
    "draw_circle": ["radius"],
    "draw_filled_ellipse": ["rx", "ry"],
    "draw_ellipse": ["rx", "ry"],
    "draw_filled_rectangle": ["width", "height"],
    "draw_rectangle": ["width", "height"],
    "draw_line": ["from_offset", "to_offset"],
    "draw_polygon": ["points"],
    "draw_bezier": ["curves"],
    "draw_arc": ["radius", "start_angle", "end_angle"],
    "draw_svg_path": ["path"],
    "fill_at": ["offset"],
    "click_canvas": ["offset"],
    "screenshot": [],
    "wait": [],
    "wait_for_canvas": [],
    "get_canvas_center": [],
}

CANVAS_STEP_FORBID: dict[str, list[str]] = {
    "set_color": ["invalid_hex_color"],
    "screenshot": ["overwrite_system_path"],
}

GUARD_FILES: dict[str, list[dict[str, Any]]] = {
    "src/nlp2cmd/validators/shell_validator.py": [
        {
            "id": "guard.shell_safety",
            "scope": "guard",
            "intent": "guard:shell_execution",
            "domain": "shell",
            "forbid": ["eval", "pipe_to_shell", "rm_wildcard", "rm_root"],
            "require": ["confirm.destructive"],
            "meaning": "ShellValidator dangerous-pattern gate",
        }
    ],
    "src/nlp2cmd/pipeline_runner_shell.py": [
        {
            "id": "guard.shell_dispatch",
            "scope": "guard",
            "intent": "gate:pre_execute",
            "domain": "shell",
            "require": ["guard.shell_safety"],
            "forbid": ["blocked_pattern"],
            "meaning": "Shell dispatch gate before ExecutionRunner",
        }
    ],
    "src/nlp2cmd/automation/step_validator.py": [
        {
            "id": "guard.step_pre_post",
            "scope": "guard",
            "intent": "guard:browser_step",
            "domain": "browser",
            "require": ["page_loaded", "session_valid"],
            "forbid": ["log_secret"],
            "meaning": "StepValidator pre/post browser conditions",
        }
    ],
}

DOMAIN_FORBID_READ: dict[str, list[str]] = {
    "sql": ["write", "delete", "ddl", "drop"],
    "shell": ["write", "delete", "network", "eval"],
    "docker": ["privileged", "host_network"],
    "kubernetes": ["cluster_admin"],
    "utility": [],
}

# pact-ir planner actions (ExecutionPlanIR) not present in ActionRegistry.
PACT_IR_PLAN_ACTIONS: dict[str, dict[str, Any]] = {
    "shell_list": {
        "intent": "list:directory",
        "domain": "shell",
        "input": ["path"],
        "output": ["directory_listing"],
        "effect": ["read"],
        "forbid": DOMAIN_FORBID_READ["shell"],
        "require": ["validate.pre_execute"],
        "meaning": "Planner action shell_list; binds pact-ir RuleShellPlanStrategy",
        "intent_aliases": ["list", "ls", "dir"],
    },
}

# Keyword/planner intent aliases → canonical intent contract ids.
PACT_IR_INTENT_ALIASES: dict[str, str] = {
    "find": "file_search",
    "search": "file_search",
    "ls": "list",
    "dir": "list",
}


def _tags_to_effects(tags: list[str]) -> list[str]:
    effects: list[str] = []
    mapping = {
        "read": "read",
        "write": "write",
        "delete": "delete",
        "insert": "write",
        "update": "write",
        "query": "read",
        "aggregate": "read",
        "filesystem": "read",
        "containers": "read",
        "k8s": "read",
        "network": "network",
    }
    for tag in tags:
        effect = mapping.get(tag)
        if effect and effect not in effects:
            effects.append(effect)
    return effects or ["read"]


def _semantic_output(schema: ActionSchema) -> str:
    desc = schema.returns_description.lower()
    if "list" in desc or schema.returns.value == "list":
        return "result_list"
    if "file" in desc:
        return "file_contents" if "content" in desc else "file_list"
    if "container" in desc:
        return "container_id" if "id" in desc else "container_list"
    if "log" in desc:
        return "log_output"
    if "row" in desc or "match" in desc:
        return "row_set"
    if "success" in desc or schema.returns.value == "boolean":
        return "success_status"
    if "summary" in desc or "formatted" in desc:
        return "formatted_output"
    return "execution_result"


def _policy_tags(schema: ActionSchema) -> list[str]:
    """Policy hints for runtime bridge / intract-policy.json — not manifest require."""
    tags: list[str] = []
    if schema.requires_confirmation or schema.is_destructive:
        tags.append("confirm_required")
    if "read" in schema.tags:
        tags.append("read_only")
    if "write" in schema.tags or "delete" in schema.tags:
        tags.append("mutating")
    return tags


def _policy_forbid(schema: ActionSchema) -> list[str]:
    """Semantic forbid tokens stored in bindings, not intract.yaml (avoids YAML self-scan noise)."""
    forbid: list[str] = []
    if schema.domain == "sql" and "read" in schema.tags:
        forbid.extend(DOMAIN_FORBID_READ["sql"])
    elif schema.domain == "shell" and "read" in schema.tags:
        forbid.extend(DOMAIN_FORBID_READ["shell"])
    elif schema.domain == "docker":
        forbid.extend(DOMAIN_FORBID_READ["docker"])
    elif schema.domain == "kubernetes" and schema.is_destructive:
        forbid.append("scale_to_zero_production")
    if schema.is_destructive or "delete" in schema.tags:
        forbid.extend(["recursive_root", "wildcard_delete"])
    if schema.domain == "shell":
        forbid.append("eval")
    return sorted(set(forbid))


def _priority(schema: ActionSchema | None = None, *, complex_intent: bool = False) -> int:
    if schema and (schema.is_destructive or schema.requires_confirmation):
        return 1
    if complex_intent:
        return 2
    return 3


def _contract(
    *,
    cid: str,
    scope: str,
    intent: str,
    domain: str,
    priority: int = 3,
    input_fields: list[str] | None = None,
    output_fields: list[str] | None = None,
    effect: list[str] | None = None,
    tags: list[str] | None = None,
    forbid: list[str] | None = None,
    require: list[str] | None = None,
    validate: list[str] | None = None,
    meaning: str = "",
) -> dict[str, Any]:
    contract: dict[str, Any] = {
        "id": cid,
        "scope": scope,
        "intent": intent,
        "domain": domain,
        "priority": priority,
    }
    if input_fields:
        contract["input"] = input_fields
    if output_fields:
        contract["output"] = output_fields
    if effect:
        contract["effect"] = effect
    if tags:
        contract["tags"] = tags
    if forbid:
        contract["forbid"] = forbid
    if require:
        contract["require"] = require
    if validate:
        contract["validate"] = validate
    if meaning:
        contract["meaning"] = meaning
    return contract


def _action_contract(schema: ActionSchema) -> tuple[dict[str, Any], dict[str, Any]]:
    required = schema.get_required_params()
    optional = schema.get_optional_params()
    inputs = required + [p for p in optional if p not in required]
    contract = _contract(
        cid=f"action.{schema.name}",
        scope="action",
        intent=ACTION_INTENT_OVERRIDES.get(schema.name, f"execute:{schema.name}"),
        domain=schema.domain,
        priority=_priority(schema),
        input_fields=inputs,
        output_fields=[_semantic_output(schema)],
        effect=_tags_to_effects(schema.tags),
        tags=_policy_tags(schema),
        meaning=f"{schema.description}; binds ActionRegistry:{schema.name}",
    )
    policy = {
        "forbid": _policy_forbid(schema),
        "require": ["confirm.destructive"] if schema.requires_confirmation or schema.is_destructive else [],
    }
    return contract, policy


def _intent_contract(
    intent: str,
    *,
    complex_intent: bool,
    mapped_action: str | None,
    registry_names: set[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    domain = "any"
    if mapped_action:
        if mapped_action.startswith("sql_"):
            domain = "sql"
        elif mapped_action.startswith("shell_"):
            domain = "shell"
        elif mapped_action.startswith("docker_"):
            domain = "docker"
        elif mapped_action.startswith("k8s_"):
            domain = "kubernetes"

    tags = ["pre_execute_gate"]
    if complex_intent:
        tags.append("multi_step")
    destructive_intents = {
        "delete", "update", "insert", "file_operation",
        "scale", "container_run", "container_stop", "image_build",
    }
    if intent in destructive_intents:
        tags.append("confirm_required")

    contract = _contract(
        cid=f"intent.{intent}",
        scope="intent",
        intent=INTENT_SEMANTICS.get(intent, f"execute:{intent}"),
        domain=domain,
        priority=1 if "confirm_required" in tags else (2 if complex_intent else 3),
        input_fields=["user_query", "entities"],
        output_fields=["action_plan_or_command"],
        effect=["read"] if intent in {"list", "get", "show", "count", "select", "describe", "status", "logs", "file_search"} else ["read"],
        tags=tags,
        meaning=(
            f"NL intent '{intent}'"
            + (f" → ActionRegistry:{mapped_action}" if mapped_action else "")
            + ("; complex multi-step" if complex_intent else "")
            + (
                "; MISSING_IN_REGISTRY"
                if mapped_action and mapped_action not in registry_names
                else ""
            )
        ),
    )
    policy = {
        "preferred_action": f"action.{mapped_action}" if mapped_action else None,
        "require": (
            ["confirm.destructive", "validate.pre_execute"]
            if "confirm_required" in tags
            else ["validate.pre_execute"]
        ),
        "forbid": (
            ["destructive_without_confirm", "recursive_root", "wildcard_delete"]
            if "confirm_required" in tags
            else []
        ),
    }
    return contract, policy


def _dom_contract(action_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    inputs = {
        "goto": ["url"],
        "navigate": ["url"],
        "explore_for_content": ["page_context"],
        "explore_for_form": ["page_context"],
        "fill_form": ["selector", "value"],
        "extract_companies": ["page_context"],
        "extract_company_websites_deep": ["page_context"],
        "save_to_file": ["data", "filepath"],
        "save_to_csv": ["data", "filepath"],
    }.get(action_name, ["params"])

    outputs = {
        "goto": ["page_loaded"],
        "navigate": ["page_loaded"],
        "fill_form": ["field_filled"],
        "extract_companies": ["company_list"],
        "extract_company_websites_deep": ["company_list"],
        "save_to_file": ["file_written"],
        "save_to_csv": ["file_written"],
    }.get(action_name, ["step_result"])

    effects = ["network", "read"] if action_name in {"goto", "navigate", "explore_for_content", "explore_for_form"} else ["read"]
    if action_name == "fill_form":
        effects = ["write_dom"]
    if action_name.startswith("save_"):
        effects = ["write"]

    tags = ["browser_step"]
    if action_name in {"goto", "navigate", "fill_form"}:
        tags.append("step_pre_gate")

    contract = _contract(
        cid=f"dom.{action_name}",
        scope="dom_action",
        intent=DOM_INTENT_OVERRIDES.get(action_name, f"dom:{action_name}"),
        domain="browser",
        priority=3,
        input_fields=inputs,
        output_fields=outputs,
        effect=effects,
        tags=tags,
        meaning=f"DOM action '{action_name}'; binds DomActionRegistry:{action_name}",
    )
    policy = {
        "forbid": DOM_FORBID.get(action_name, []),
        "require": ["validate.step_pre"] if "step_pre_gate" in tags else [],
    }
    return contract, policy


def _pact_ir_plan_contract(action_name: str, spec: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _contract(
        cid=f"action.{action_name}",
        scope="plan_action",
        intent=spec["intent"],
        domain=spec["domain"],
        priority=3,
        input_fields=spec.get("input"),
        output_fields=spec.get("output"),
        effect=spec.get("effect"),
        tags=["pact_ir", "read_only"] if "read" in (spec.get("effect") or []) else ["pact_ir"],
        meaning=spec.get("meaning", f"pact-ir planner action {action_name}"),
    )
    policy = {
        "forbid": spec.get("forbid", []),
        "require": spec.get("require", ["validate.pre_execute"]),
    }
    return contract, policy


def _canvas_step_contract(action_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    inputs = CANVAS_STEP_INPUTS.get(action_name, [])
    is_draw = action_name.startswith("draw_") or action_name in {"fill_at", "click_canvas"}
    outputs = ["canvas_mutated"] if is_draw else ["step_result"]
    if action_name == "screenshot":
        outputs = ["screenshot_file"]
    if action_name == "get_canvas_center":
        outputs = ["canvas_center"]
    if action_name == "wait_for_canvas":
        outputs = ["canvas_ready"]

    if is_draw or action_name in {"set_color", "set_line_width", "fill_at", "click_canvas"}:
        effects = ["write_canvas"]
    elif action_name in {"wait_for_canvas", "get_canvas_center", "select_tool"}:
        effects = ["read_canvas"]
    elif action_name == "screenshot":
        effects = ["read", "write"]
    else:
        effects = ["read"]

    tags = ["canvas_step"]
    if action_name in {"wait_for_canvas", "set_color", "set_line_width"}:
        tags.append("step_pre_gate")

    contract = _contract(
        cid=f"dom.{action_name}",
        scope="canvas_step",
        intent=CANVAS_STEP_INTENTS.get(action_name, f"canvas:{action_name}"),
        domain="browser",
        priority=3,
        input_fields=inputs or None,
        output_fields=outputs,
        effect=effects,
        tags=tags,
        meaning=f"Canvas step '{action_name}'; binds HandlerRegistry:{action_name}",
    )
    policy = {
        "forbid": CANVAS_STEP_FORBID.get(action_name, []),
        "require": ["validate.step_pre"] if "step_pre_gate" in tags else [],
    }
    return contract, policy


def generate_manifest() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    registry = ActionRegistry()
    router = json.loads(ROUTER_CONFIG.read_text(encoding="utf-8"))
    registry_names = set(registry.list_actions())
    dom_actions = sorted(DomActionRegistry.list_actions())

    contracts: list[dict[str, Any]] = []
    bindings: dict[str, Any] = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "router_config": "src/nlp2cmd/data/router_config.json",
            "action_registry": "src/nlp2cmd/registry/action_registry.py",
            "dom_registry": "src/nlp2cmd/dom_actions/registry.py",
            "step_handler_registry": "src/nlp2cmd/step_handlers/registry.py",
            "pact_ir_planner": "nlp2cmd_planner/strategies/rule_shell.py",
        },
        "intent_to_contract": {},
        "intent_to_action": {},
        "action_to_contract": {},
        "dom_to_contract": {},
        "contract_to_registry": {},
        "contract_policy": {},
        "missing_bindings": [],
    }

    for name in sorted(registry.list_actions()):
        schema = registry.get(name)
        assert schema is not None
        contract, action_policy = _action_contract(schema)
        contracts.append(contract)
        bindings["action_to_contract"][name] = contract["id"]
        bindings["contract_to_registry"][contract["id"]] = {
            "registry": "ActionRegistry",
            "name": name,
            "param_source": "ActionSchema.params",
        }
        bindings["contract_policy"][contract["id"]] = action_policy

    seen_intents: set[str] = set()
    for intent in router.get("simple_intents", []):
        mapped = router.get("intent_action_map", {}).get(intent)
        contract, intent_policy = _intent_contract(
            intent, complex_intent=False, mapped_action=mapped, registry_names=registry_names
        )
        contracts.append(contract)
        bindings["intent_to_contract"][intent] = contract["id"]
        bindings["contract_policy"][contract["id"]] = intent_policy
        if mapped:
            bindings["intent_to_action"][intent] = mapped
            if mapped not in registry_names:
                bindings["missing_bindings"].append(
                    {
                        "intent": intent,
                        "expected_action": mapped,
                        "reason": "in intent_action_map but not in ActionRegistry",
                    }
                )
        seen_intents.add(intent)

    for intent in router.get("complex_intents", []):
        mapped = router.get("intent_action_map", {}).get(intent)
        contract, intent_policy = _intent_contract(
            intent, complex_intent=True, mapped_action=mapped, registry_names=registry_names
        )
        contracts.append(contract)
        bindings["intent_to_contract"][intent] = contract["id"]
        bindings["contract_policy"][contract["id"]] = intent_policy
        if mapped:
            bindings["intent_to_action"][intent] = mapped
            if mapped not in registry_names:
                bindings["missing_bindings"].append(
                    {
                        "intent": intent,
                        "expected_action": mapped,
                        "reason": "in intent_action_map but not in ActionRegistry",
                    }
                )
        seen_intents.add(intent)

    for intent, action_name in router.get("intent_action_map", {}).items():
        if intent in seen_intents:
            continue
        contract, intent_policy = _intent_contract(
            intent, complex_intent=False, mapped_action=action_name, registry_names=registry_names
        )
        contracts.append(contract)
        bindings["intent_to_contract"][intent] = contract["id"]
        bindings["contract_policy"][contract["id"]] = intent_policy
        bindings["intent_to_action"][intent] = action_name
        if action_name not in registry_names:
            bindings["missing_bindings"].append(
                {
                    "intent": intent,
                    "expected_action": action_name,
                    "reason": "in intent_action_map but not in ActionRegistry",
                }
            )

    alias_targets: dict[str, str] = {}
    for action_name in dom_actions:
        contract, dom_policy = _dom_contract(action_name)
        contracts.append(contract)
        bindings["dom_to_contract"][action_name] = contract["id"]
        bindings["contract_to_registry"][contract["id"]] = {
            "registry": "DomActionRegistry",
            "name": action_name,
        }
        bindings["contract_policy"][contract["id"]] = dom_policy
        if action_name in {"goto", "navigate"}:
            alias_targets[action_name] = contract["id"]

    if "goto" in alias_targets and "navigate" in alias_targets:
        bindings["dom_to_contract"]["navigate"] = alias_targets["goto"]

    for action_name, spec in sorted(PACT_IR_PLAN_ACTIONS.items()):
        if action_name in bindings["action_to_contract"]:
            continue
        contract, plan_policy = _pact_ir_plan_contract(action_name, spec)
        contracts.append(contract)
        bindings["action_to_contract"][action_name] = contract["id"]
        bindings["contract_to_registry"][contract["id"]] = {
            "registry": "pact_ir",
            "name": action_name,
            "param_source": "PlanStep.params",
        }
        bindings["contract_policy"][contract["id"]] = plan_policy

    for alias, canonical_intent in PACT_IR_INTENT_ALIASES.items():
        target = bindings["intent_to_contract"].get(canonical_intent)
        if target and alias not in bindings["intent_to_contract"]:
            bindings["intent_to_contract"][alias] = target

    dom_bound = set(bindings["dom_to_contract"])
    for action_name in sorted(CANVAS_STEP_ACTIONS):
        if action_name in dom_bound:
            continue
        if action_name not in HandlerRegistry.list_actions():
            continue
        contract, canvas_policy = _canvas_step_contract(action_name)
        contracts.append(contract)
        bindings["dom_to_contract"][action_name] = contract["id"]
        bindings["contract_to_registry"][contract["id"]] = {
            "registry": "HandlerRegistry",
            "name": action_name,
        }
        bindings["contract_policy"][contract["id"]] = canvas_policy

    manifest = {
        "version": "intract.v1",
        "project": {
            "name": "nlp2cmd",
            "intent": "translate:natural_language_to_command",
            "domain": "orchestration",
            "meaning": (
                "NL → command/plan system. Intract covers semantic intent contracts; "
                "ActionRegistry remains execution schema source of truth."
            ),
        },
        "contracts": contracts,
        "files": GUARD_FILES,
    }

    policy = {
        "fail_on": ["violation"],
        "warn_on": ["partial", "missing_binding"],
        "ci_commands": [
            "intract check-manifest intract.yaml",
            "intract duplicates --threshold 0.85",
            "intract graph --format mermaid",
        ],
        "runtime_policy_source": "contract_policy in intract-bindings.json",
        "graph_required": [
            "intent.file_search preferred_action action.shell_find",
            "intent.delete confirm_required",
            "action.docker_run confirm_required",
            "dom.goto step_pre_gate",
            "dom.set_color step_pre_gate",
            "dom.draw_filled_circle canvas_write",
        ],
    }

    return manifest, bindings, policy


def _yaml_dump(data: dict[str, Any]) -> str:
    return yaml.dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )


def write_outputs(
    manifest: dict[str, Any],
    bindings: dict[str, Any],
    policy: dict[str, Any],
    *,
    manifest_path: Path = OUT_MANIFEST,
    bindings_path: Path = OUT_BINDINGS,
    policy_path: Path = OUT_POLICY,
) -> None:
    manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")
    bindings_path.write_text(json.dumps(bindings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    policy_path.write_text(json.dumps(policy, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    manifest, bindings, policy = generate_manifest()
    write_outputs(manifest, bindings, policy)

    n_contracts = len(manifest["contracts"])
    n_missing = len(bindings["missing_bindings"])
    print(f"Wrote {OUT_MANIFEST} ({n_contracts} contracts)")
    print(f"Wrote {OUT_BINDINGS}")
    print(f"Wrote {OUT_POLICY}")
    if n_missing:
        print(f"Warning: {n_missing} missing ActionRegistry bindings:")
        for item in bindings["missing_bindings"]:
            print(f"  - intent.{item['intent']} → {item['expected_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
