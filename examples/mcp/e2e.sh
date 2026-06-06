#!/usr/bin/env bash
set -euo pipefail

payload='{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"nlp2cmd_analyze","arguments":{"query":"list files in /tmp"}}}'
out="$(printf '%s\n' "$payload" | nlp2cmd-mcp)"
echo "$out" | grep -q 'intent_ir'

if command -v nlp2uri-mcp >/dev/null 2>&1; then
  uri_payload='{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"nlp2cmd_resolve_uri","arguments":{"prompt":"open firefox","platform":"linux"}}}'
  uri_out="$(printf '%s\n' "$uri_payload" | nlp2cmd-mcp)"
  echo "$uri_out" | grep -q 'app://firefox'
fi

echo "examples/mcp/e2e: OK"
