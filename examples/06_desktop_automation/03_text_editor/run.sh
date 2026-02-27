#!/bin/bash
# 03_text_editor — Write and save a document via nlp2cmd
# Usage: bash examples/06_desktop_automation/03_text_editor/run.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGS="$SCRIPT_DIR/logs"
SRC="novnc://localhost:6080"

rm -rf "$LOGS"
mkdir -p "$LOGS"

echo "=== 03 Text Editor: Write and Save Document ==="
echo "Source: $SRC"
echo ""

# Open app launcher
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Alt+F2"
sleep 1

# Launch mousepad
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "type mousepad"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
sleep 2

# Type document content
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md \
    -q "type NLP2CMD Desktop Automation Report"
sleep 0.3
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md \
    -q "type ===================================="
sleep 0.3
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md \
    -q "type Date: 2026-02-27"
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md \
    -q "type System: Linux XFCE via noVNC"
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md \
    -q "type This document was created autonomously by NLP2CMD."
sleep 0.5

# Save with Ctrl+S
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md --screenshot \
    -q "press Control+s"
sleep 1.5

# Type filename in save dialog
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md \
    -q "type /home/nlp2cmd/report.txt"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md --screenshot \
    -q "press Enter"
sleep 1

echo ""
echo "Done. Session log: $LOGS/session.md"
