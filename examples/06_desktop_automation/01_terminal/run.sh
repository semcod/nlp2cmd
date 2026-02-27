#!/bin/bash
# 01_terminal — Open terminal and run shell commands via nlp2cmd
# Usage: bash examples/06_desktop_automation/01_terminal/run.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGS="$SCRIPT_DIR/logs"
SRC="novnc://localhost:6080"

rm -rf "$LOGS"
mkdir -p "$LOGS"

echo "=== 01 Terminal: Run Shell Commands ==="
echo "Source: $SRC"
echo "Logs:   $LOGS/"
echo ""

nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "press Control+Alt+t"
sleep 2

nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "type uname -a"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "press Enter"
sleep 1.5

nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "type whoami"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "press Enter"
sleep 1.5

nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "type df -h /"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "press Enter"
sleep 1.5

nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "type free -h"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "press Enter"
sleep 1.5

# Final screenshot
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" -q "screenshot"

echo ""
echo "Done. Session log: $LOGS/session.md"
