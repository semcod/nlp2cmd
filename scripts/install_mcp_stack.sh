#!/usr/bin/env bash
# Install nlp2cmd + MCP bridge (nlp2uri) with sibling monorepo packages.
# Works with plain pip (no uv path sources).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIP="${PIP:-pip}"
PYTHON="${PYTHON:-python}"

dsl_root="$(cd "$ROOT/../nlp2dsl/packages" 2>/dev/null && pwd || true)"
semcod_nlp2uri="$(cd "$ROOT/../../semcod/nlp2uri" 2>/dev/null && pwd || true)"

install_pkg() {
    local path="$1"
    if [[ -d "$path" && -f "$path/pyproject.toml" ]]; then
        echo "== editable: $path"
        "$PIP" install -e "$path" -q
    fi
}

if [[ -n "$dsl_root" ]]; then
    for pkg in pact-ir nlp2cmd-intent nlp2cmd-planner nlp2cmd-propact; do
        install_pkg "$dsl_root/$pkg"
    done
    # Optional — only needed for nlp2cmd_plan integration tool
    install_pkg "$dsl_root/nlp2dsl-show"
else
    echo "warn: ../nlp2dsl/packages not found — nlp2cmd_analyze still works via PyPI nlp2cmd-intent"
fi

if [[ -n "$semcod_nlp2uri" ]]; then
    echo "== editable: $semcod_nlp2uri[envmap]"
    "$PIP" install -e "$semcod_nlp2uri[envmap]" -q
else
    echo "== pip: nlp2uri[envmap] from PyPI"
    "$PIP" install "nlp2uri[envmap]>=0.4" -q
fi

echo "== editable: nlp2cmd[mcp]"
"$PIP" install -e "$ROOT[mcp]" -q

"$PYTHON" -c "
import nlp2cmd
import nlp2uri
print('ok nlp2cmd', nlp2cmd.__version__, '+ nlp2uri', nlp2uri.__version__)
"
