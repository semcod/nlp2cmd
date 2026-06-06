#!/usr/bin/env bash
# Reinstall nlp2cmd (editable) and nlp2dsl integration packages from sibling monorepo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NLP2DSL_DIR="${NLP2DSL_DIR:-$ROOT/../nlp2dsl}"

if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  PY="$ROOT/.venv/bin/python3"
elif [[ -x "$ROOT/venv/bin/python3" ]]; then
  PY="$ROOT/venv/bin/python3"
else
  PY="${PYTHON:-python3}"
fi

export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
export LANG="${LANG:-C.UTF-8}"
export LC_CTYPE="${LC_CTYPE:-$LANG}"

if command -v uv >/dev/null 2>&1 && [[ -f "$ROOT/uv.lock" ]]; then
  echo "==> uv sync --extra all (project .venv)"
  (cd "$ROOT" && uv sync --extra all)
else
  echo "==> nlp2cmd (editable + integration extra)"
  "$PY" -m pip install -e "$ROOT[integration]" --upgrade
fi

echo "==> nlp2cmd-intent >=0.1.1 (keywords module)"
"$PY" -m pip install -U "nlp2cmd-intent>=0.1.1" -q

if [[ -d "$NLP2DSL_DIR/packages" ]]; then
  echo "==> nlp2dsl packages from $NLP2DSL_DIR"
  NLP2DSL_DIR="$NLP2DSL_DIR" "$NLP2DSL_DIR/packages/install-dev.sh"
  echo "==> nlp2dsl SDK"
  "$PY" -m pip install -e "$NLP2DSL_DIR" --upgrade
  echo "==> Re-pin editable packages after nlp2cmd[integration]"
  NLP2DSL_DIR="$NLP2DSL_DIR" "$NLP2DSL_DIR/packages/install-dev.sh"
else
  echo "WARN: nlp2dsl not found at $NLP2DSL_DIR — only PyPI integration deps installed" >&2
  echo "      Set NLP2DSL_DIR=/path/to/nlp2dsl for local editable packages" >&2
fi

NLP2CMD_BIN="$("$PY" -c "import shutil; print(shutil.which('nlp2cmd') or 'nlp2cmd')")"
echo ""
echo "Python: $("$PY" --version 2>&1)"
echo "nlp2cmd: $NLP2CMD_BIN"
echo ""
echo "Done. Activate the same venv before running CLI, then:"
echo "  export NLP2CMD_INTEGRATION=1 LANG=C.UTF-8"
echo "  nlp2cmd plan 'znajdź pliki *.py w src' --explain"
echo "  nlp2cmd plan 'znajdź pliki *.py w src' --execute --explain"
