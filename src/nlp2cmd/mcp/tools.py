"""MCP tool schemas and handlers for nlp2cmd."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Callable

MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "nlp2cmd_analyze",
        "description": (
            "Analyze natural-language query via nlp2cmd-intent (IntentIR). "
            "Returns intent, target_kind, confidence, optional execution plan."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language command or question."},
                "include_plan": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include execution_plan_ir when available.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "nlp2cmd_plan",
        "description": (
            "Full nlp2dsl integration pipeline: IntentIR → ExecutionPlanIR → Propact markdown. "
            "Requires NLP2CMD_INTEGRATION=1 and integration packages."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "nlp2cmd_resolve_uri",
        "description": (
            "Resolve NL to URI: SystemMap (env2llm) when map provided, else nlp2uri desktop "
            "(open app, screenshot, terminal). Requires nlp2uri for URI output."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "platform": {"type": "string", "enum": ["linux", "darwin", "windows"]},
                "system_map": {"type": "object"},
                "doql_path": {"type": "string"},
                "example_dir": {"type": "string"},
                "fallback_desktop": {"type": "boolean", "default": True},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "nlp2cmd_uri_plan",
        "description": "Desktop NL → abstract URI + OS action plan (nlp2uri). Requires nlp2uri installed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "platform": {"type": "string", "enum": ["linux", "darwin", "windows"]},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "nlp2cmd_list_system_uris",
        "description": "List canonical URIs from env2llm SystemMapIR. Requires nlp2uri[envmap].",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_map": {"type": "object"},
                "doql_path": {"type": "string"},
                "example_dir": {"type": "string"},
                "example_id": {"type": "string"},
            },
        },
    },
]


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    return obj


def _nlp2uri_available() -> bool:
    try:
        import nlp2uri  # noqa: F401

        return True
    except ImportError:
        return False


def _nlp2uri_missing() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "nlp2uri not installed. Run: pip install -e /path/to/nlp2uri",
    }


def tool_analyze(arguments: dict[str, Any]) -> dict[str, Any]:
    from nlp2cmd.bridge.query_input import analyze_query_input

    query = str(arguments.get("query") or "")
    analysis = analyze_query_input(query, include_plan=bool(arguments.get("include_plan", False)))
    return {
        "ok": True,
        "query": query,
        "intent": analysis.intent,
        "target_kind": analysis.target_kind,
        "confidence": analysis.confidence,
        "source": analysis.source,
        "intent_ir": analysis.intent_ir,
        "execution_plan_ir": analysis.execution_plan_ir,
        "plan_error": analysis.plan_error,
        "nlp2dsl_workflow": analysis.nlp2dsl_workflow,
    }


def tool_plan(arguments: dict[str, Any]) -> dict[str, Any]:
    from nlp2cmd.bridge.integration import integration_enabled, plan_query_via_integration

    query = str(arguments.get("query") or "")
    if not integration_enabled():
        return {
            "ok": False,
            "error": (
                "Integration disabled. Set NLP2CMD_INTEGRATION=1 and install "
                "nlp2cmd[integration] (pact-ir, planner, propact)."
            ),
        }
    payload = plan_query_via_integration(query)
    return {"ok": True, "query": query, **payload}


def tool_resolve_uri(arguments: dict[str, Any]) -> dict[str, Any]:
    if not _nlp2uri_available():
        return _nlp2uri_missing()

    from nlp2uri.models import HostPlatform
    from nlp2uri.systemmap.context import load_ir_from_arguments
    from nlp2uri.systemmap.fallback import resolve_prompt_with_fallback

    prompt = str(arguments.get("prompt") or "")
    platform = arguments.get("platform")
    host = HostPlatform(platform) if platform else None

    ir = None
    if any(arguments.get(k) for k in ("system_map", "doql_path", "example_dir")):
        ir = load_ir_from_arguments(arguments)

    payload = resolve_prompt_with_fallback(
        prompt,
        ir,
        platform=host,
    )
    return {"ok": payload.get("uri") is not None, "prompt": prompt, **payload}


def tool_uri_plan(arguments: dict[str, Any]) -> dict[str, Any]:
    if not _nlp2uri_available():
        return _nlp2uri_missing()

    from nlp2uri.models import HostPlatform
    from nlp2uri.service import NLP2URIService

    prompt = str(arguments.get("prompt") or "")
    platform = arguments.get("platform")
    host = HostPlatform(platform) if platform else None
    service = NLP2URIService.for_platform(host) if host else NLP2URIService.default()
    plan = service.from_prompt(prompt)
    return {"ok": True, "prompt": prompt, "platform": service._host().value, "plan": plan.to_dict()}


def tool_list_system_uris(arguments: dict[str, Any]) -> dict[str, Any]:
    if not _nlp2uri_available():
        return _nlp2uri_missing()

    from nlp2uri.service import NLP2URIService
    from nlp2uri.systemmap.context import load_ir_from_arguments

    try:
        ir = load_ir_from_arguments(arguments)
    except (ValueError, RuntimeError) as exc:
        return {"ok": False, "error": str(exc)}

    payload = NLP2URIService.default().list_system_uris(ir)
    return {"ok": True, **payload}


_TOOL_DISPATCH: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "nlp2cmd_analyze": tool_analyze,
    "nlp2cmd_plan": tool_plan,
    "nlp2cmd_resolve_uri": tool_resolve_uri,
    "nlp2cmd_uri_plan": tool_uri_plan,
    "nlp2cmd_list_system_uris": tool_list_system_uris,
}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    handler = _TOOL_DISPATCH.get(name)
    if handler is None:
        return {"ok": False, "error": f"unknown tool: {name}"}
    result = handler(arguments)
    result.setdefault(
        "mcp_content",
        [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
    )
    return result
