#!/bin/bash
# 05_email_client — Thunderbird email automation via nlp2cmd
# Usage: bash examples/06_desktop_automation/05_email_client/run.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGS="$SCRIPT_DIR/logs"
SRC="novnc://localhost:6080"

rm -rf "$LOGS"
mkdir -p "$LOGS"

echo "=== 05 Email Client: Thunderbird Automation ==="
echo "Source: $SRC"
echo ""

# Open terminal
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Control+Alt+t"
sleep 2

# Launch Thunderbird
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "type thunderbird &"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
sleep 5

# Check for new messages
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Control+Shift+t"
sleep 3

# Screenshot: inbox view
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md --screenshot -q "screenshot"
sleep 1

# Compose new email
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Control+n"
sleep 2

# Type recipient
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "type test@example.com"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Tab"
sleep 0.3

# Skip CC, type subject
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Tab"
sleep 0.3
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md \
    -q "type NLP2CMD Desktop Automation Test"
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Tab"
sleep 0.5

# Type body
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md \
    -q "type This email was composed automatically by NLP2CMD desktop automation."
sleep 0.5
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Enter"
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md \
    -q "type Sent from noVNC Docker container."
sleep 0.5

# Screenshot: composed email
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md --screenshot -q "screenshot"
sleep 1

# Close compose window without sending (Escape → discard)
nlp2cmd --source "$SRC" --run --log-dir "$LOGS" --md -q "press Control+w"
sleep 1

echo ""
echo "Done. Session log: $LOGS/session.md"
