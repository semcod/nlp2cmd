"""Stdio MCP server — nlp2cmd tools + optional nlp2uri bridge."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from typing import Any

from nlp2cmd import __version__
from nlp2cmd.mcp.tools import MCP_TOOLS, call_tool

_PROTOCOL_VERSION = "2024-11-05"
_SERVER_NAME = "nlp2cmd"
_NOTIFICATIONS = frozenset({"notifications/initialized", "notifications/cancelled"})


def _jsonrpc_response(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _write_json(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, separators=(",", ":"), default=str) + "\n")
    sys.stdout.flush()


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def handle_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    req_id = msg.get("id")
    method = msg.get("method", "")

    if method in _NOTIFICATIONS:
        return None

    if method == "initialize":
        return _jsonrpc_response(
            req_id,
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": _SERVER_NAME, "version": __version__},
            },
        )

    if method == "tools/list":
        return _jsonrpc_response(req_id, {"tools": MCP_TOOLS})

    if method == "tools/call":
        params = msg.get("params") or {}
        tool_name = str(params.get("name") or "")
        arguments = params.get("arguments") or {}
        try:
            result = call_tool(tool_name, arguments)
            is_error = not result.get("ok", True)
            content = result.pop("mcp_content", [{"type": "text", "text": json.dumps(result, indent=2)}])
            payload: dict[str, Any] = {"content": content}
            if is_error:
                payload["isError"] = True
            return _jsonrpc_response(req_id, payload)
        except Exception as exc:
            return _jsonrpc_response(
                req_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error in {tool_name}: {exc}\n{traceback.format_exc()}",
                        }
                    ],
                    "isError": True,
                },
            )

    return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


def run_stdio() -> int:
    _log(f"nlp2cmd mcp-server: started (stdio, v{__version__})")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            _write_json(_jsonrpc_error(None, -32700, f"Parse error: {exc}"))
            continue
        response = handle_message(msg)
        if response is not None:
            _write_json(response)
    _log("nlp2cmd mcp-server: stdin closed, exiting")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nlp2cmd-mcp")
    parser.parse_args(argv)
    return run_stdio()


if __name__ == "__main__":
    raise SystemExit(main())
