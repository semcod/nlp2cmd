#!/bin/bash
# 02_calculator — Open calculator and do math via nlp2cmd
# Usage: bash examples/06_desktop_automation/02_calculator/run.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGS="$SCRIPT_DIR/logs"
SRC="novnc://localhost:6080"

rm -rf "$LOGS"
mkdir -p "$LOGS"

echo "=== 02 Calculator: Do Math ==="
echo "Source: $SRC"
echo ""

# Open terminal
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "press Control+Alt+t"
sleep 2

# Launch calculator from terminal
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "type galculator &"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "press Enter"
sleep 2

# Calculate 42 * 137 = 5754
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "type 42*137"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "press Enter"
sleep 1

# Calculate 256 * 256 = 65536
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "press Escape"
sleep 0.3
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "type 256*256"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "press Enter"
sleep 1

# Final screenshot
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "screenshot"

echo ""
echo "Done. Session log: $LOGS/session.md"
