"""MCP stdio server tests."""

from __future__ import annotations

import json

import pytest

from nlp2cmd.mcp.server import handle_message
from nlp2cmd.mcp.tools import call_tool


def test_tools_list_includes_core_tools() -> None:
    response = handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    assert response is not None
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert {
        "nlp2cmd_analyze",
        "nlp2cmd_plan",
        "nlp2cmd_resolve_uri",
        "nlp2cmd_uri_plan",
        "nlp2cmd_list_system_uris",
    }.issubset(names)


def test_analyze_tool_shell_query() -> None:
    pytest.importorskip("nlp2cmd_intent")
    result = call_tool("nlp2cmd_analyze", {"query": "list files in /tmp"})
    assert result["ok"] is True
    assert result["target_kind"] == "shell"
    assert result["intent_ir"]["format"] == "nlp2cmd.intent_ir.v1"


def test_resolve_uri_desktop_fallback() -> None:
    pytest.importorskip("nlp2uri")
    result = call_tool(
        "nlp2cmd_resolve_uri",
        {"prompt": "open firefox", "platform": "linux"},
    )
    assert result["ok"] is True
    assert result["source"] == "desktop"
    assert result["uri"].startswith("app://firefox/")


def test_resolve_uri_system_map() -> None:
    pytest.importorskip("nlp2uri")
    result = call_tool(
        "nlp2cmd_resolve_uri",
        {
            "prompt": "send invoice",
            "system_map": {
                "example_id": "01-invoice",
                "commands": [{"name": "send_invoice", "runtime": "executor:worker"}],
                "runtimes": [{"id": "executor:worker", "kind": "worker"}],
            },
        },
    )
    assert result["ok"] is True
    assert result["source"] == "system_map"
    assert "send_invoice" in result["uri"]


def test_stdio_tools_call_analyze() -> None:
    pytest.importorskip("nlp2cmd_intent")
    response = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "nlp2cmd_analyze",
                "arguments": {"query": "show docker containers"},
            },
        }
    )
    assert response is not None
    text = response["result"]["content"][0]["text"]
    payload = json.loads(text)
    assert payload["ok"] is True
    assert payload["intent_ir"]
