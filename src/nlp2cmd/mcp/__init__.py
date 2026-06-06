"""MCP stdio server for nlp2cmd (+ optional nlp2uri bridge)."""

from nlp2cmd.mcp.server import MCP_TOOLS, handle_message, main, run_stdio

__all__ = ["MCP_TOOLS", "handle_message", "main", "run_stdio"]
