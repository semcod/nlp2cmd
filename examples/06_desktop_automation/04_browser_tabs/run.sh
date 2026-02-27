#!/bin/bash
# 04_browser_tabs — Multi-tab browser management via nlp2cmd
# Usage: bash examples/06_desktop_automation/04_browser_tabs/run.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGS="$SCRIPT_DIR/logs"
SRC="novnc://localhost:6080"

rm -rf "$LOGS"
mkdir -p "$LOGS"

echo "=== 04 Browser Tabs: Multi-Tab Management ==="
echo "Source: $SRC"
echo ""

# Open terminal
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Control+Alt+t"
sleep 2

# Launch Firefox
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "type firefox &"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
sleep 4

# Navigate to GitHub
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "type https://github.com"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
sleep 3

# Open new tab → Stack Overflow
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Control+t"
sleep 1
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "type https://stackoverflow.com"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
sleep 3

# Open new tab → DuckDuckGo
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Control+t"
sleep 1
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "type https://duckduckgo.com"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
sleep 3

# Screenshot with 3 tabs
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md --screenshot -q "screenshot"
sleep 1

# Switch back to first tab (GitHub)
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Control+1"
sleep 2

# Screenshot showing GitHub tab
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md --screenshot -q "screenshot"
sleep 1

# Close current tab
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Control+w"
sleep 1

# Final screenshot
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md --screenshot -q "screenshot"

echo ""
echo "Done. Session log: $LOGS/session.md"
