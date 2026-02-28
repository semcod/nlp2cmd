#!/usr/bin/env bash
# Demo: LLM Validation and Repair in nlp2cmd
#
# This script demonstrates the LLM Validator + Repair pipeline:
#   1. nlp2cmd generates a command from natural language
#   2. Command executes and captures stdout/stderr
#   3. LLM_VALIDATOR (local qwen2.5:3b via Ollama) checks if the output
#      matches the user's intent → pass/fail verdict
#   4. On fail → LLM_REPAIR (OpenRouter cloud model) suggests an improved
#      command and optionally patches data/patterns.json and data/templates.json
#
# Prerequisites:
#   - Ollama running locally (ollama serve)
#   - qwen2.5:3b model pulled (ollama pull qwen2.5:3b)
#   - OPENROUTER_API_KEY set in .env (for repair, optional)
#
# Usage:
#   bash examples/08_llm_validation/demo_validation.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

NLPCMD="${PROJECT_DIR}/venv/bin/nlp2cmd"

echo "============================================="
echo "  NLP2CMD — LLM Validation & Repair Demo"
echo "============================================="
echo ""

# Check Ollama
if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama is not running. Start with: ollama serve"
    exit 1
fi
echo "✓ Ollama is running"

# Check model
if ! curl -sf http://localhost:11434/api/tags | grep -q "qwen2.5:3b"; then
    echo "WARNING: qwen2.5:3b not found. Pull with: ollama pull qwen2.5:3b"
fi

echo ""
echo "--- Test 1: Camera scan (should pass validation) ---"
echo "$ nlp2cmd -r \"znajdz kamery podłączone do sieci lokalnej\""
echo "Y" | $NLPCMD -r "znajdz kamery podłączone do sieci lokalnej" 2>&1 || true

echo ""
echo "--- Test 2: List files (should pass validation) ---"
echo "$ nlp2cmd -r \"pokaż pliki w bieżącym katalogu\""
echo "Y" | $NLPCMD -r "pokaż pliki w bieżącym katalogu" 2>&1 || true

echo ""
echo "--- Test 3: Disk usage (should pass validation) ---"
echo "$ nlp2cmd -r \"pokaż użycie dysku\""
echo "Y" | $NLPCMD -r "pokaż użycie dysku" 2>&1 || true

echo ""
echo "--- Test 4: Run validator test suite ---"
echo "$ python3 examples/08_llm_validation/test_validator.py"
"${PROJECT_DIR}/venv/bin/python3" examples/08_llm_validation/test_validator.py 2>&1

echo ""
echo "============================================="
echo "  Demo complete"
echo "============================================="
