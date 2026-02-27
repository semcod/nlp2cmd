#!/bin/bash
# 00_full_lifecycle — Start env, run all examples, analyze results, stop env
# Usage: bash examples/06_desktop_automation/00_full_lifecycle/run.sh [--skip-setup] [--skip-teardown] [--only 01 03]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXAMPLES_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$EXAMPLES_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker/novnc/docker-compose.yml"
RESULTS="$SCRIPT_DIR/results"
SRC="novnc://localhost:6080"

SKIP_SETUP=false
SKIP_TEARDOWN=false
ONLY_EXAMPLES=()

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-setup)    SKIP_SETUP=true; shift ;;
        --skip-teardown) SKIP_TEARDOWN=true; shift ;;
        --only)          shift; while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do ONLY_EXAMPLES+=("$1"); shift; done ;;
        *)               shift ;;
    esac
done

rm -rf "$RESULTS"
mkdir -p "$RESULTS"

STARTED_AT=$(date +%s)
PASS=0
FAIL=0
SKIP=0

log() { echo "[$(date +%H:%M:%S)] $*"; }

# ─── 1. Setup ───────────────────────────────────────────────
if [ "$SKIP_SETUP" = false ]; then
    log "🚀 Starting Docker desktop environment..."
    docker compose -f "$COMPOSE_FILE" up -d 2>&1 | tail -3

    log "⏳ Waiting for noVNC to be ready..."
    MAX_WAIT=60
    ELAPSED=0
    while [ $ELAPSED -lt $MAX_WAIT ]; do
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:6080/ 2>/dev/null | grep -q "200"; then
            log "✅ noVNC is ready (${ELAPSED}s)"
            break
        fi
        sleep 2
        ELAPSED=$((ELAPSED + 2))
    done

    if [ $ELAPSED -ge $MAX_WAIT ]; then
        log "❌ noVNC did not start within ${MAX_WAIT}s"
        exit 1
    fi

    # Extra wait for XFCE desktop to fully initialize
    sleep 5
    log "🖥️  Desktop environment ready"
else
    log "⏭️  Skipping setup (--skip-setup)"
fi

# ─── 2. Run bash examples (01-05) ───────────────────────────
BASH_EXAMPLES=(
    "01_terminal"
    "02_calculator"
    "03_text_editor"
    "04_browser_tabs"
    "05_email_client"
)

should_run() {
    local name="$1"
    local num="${name%%_*}"
    if [ ${#ONLY_EXAMPLES[@]} -eq 0 ]; then
        return 0  # run all
    fi
    for o in "${ONLY_EXAMPLES[@]}"; do
        if [ "$o" = "$num" ] || [ "$o" = "$name" ]; then
            return 0
        fi
    done
    return 1
}

for example in "${BASH_EXAMPLES[@]}"; do
    example_dir="$EXAMPLES_DIR/$example"
    run_script="$example_dir/run.sh"
    log_file="$RESULTS/${example}.log"

    if [ ! -f "$run_script" ]; then
        log "⚠️  $example: run.sh not found, skipping"
        SKIP=$((SKIP + 1))
        continue
    fi

    if ! should_run "$example"; then
        log "⏭️  $example: skipped (--only filter)"
        SKIP=$((SKIP + 1))
        continue
    fi

    log "▶ Running $example..."
    EXAMPLE_START=$(date +%s)

    if bash "$run_script" > "$log_file" 2>&1; then
        EXAMPLE_END=$(date +%s)
        DURATION=$((EXAMPLE_END - EXAMPLE_START))
        log "  ✅ $example passed (${DURATION}s)"
        PASS=$((PASS + 1))
        echo "PASS ${DURATION}s" >> "$log_file"
    else
        EXAMPLE_END=$(date +%s)
        DURATION=$((EXAMPLE_END - EXAMPLE_START))
        log "  ❌ $example failed (${DURATION}s)"
        FAIL=$((FAIL + 1))
        echo "FAIL ${DURATION}s" >> "$log_file"
    fi
done

# ─── 3. Analyze results ─────────────────────────────────────
log ""
log "📊 Analyzing results..."

ENDED_AT=$(date +%s)
TOTAL_TIME=$((ENDED_AT - STARTED_AT))

# Count steps and screenshots in session logs
TOTAL_STEPS=0
TOTAL_SCREENSHOTS=0
for example in "${BASH_EXAMPLES[@]}"; do
    session_md="$EXAMPLES_DIR/$example/logs/session.md"
    if [ -f "$session_md" ]; then
        steps=$(grep -c "^## Step" "$session_md" 2>/dev/null || echo 0)
        shots=$(grep -c "data:image/png;base64," "$session_md" 2>/dev/null || echo 0)
        TOTAL_STEPS=$((TOTAL_STEPS + steps))
        TOTAL_SCREENSHOTS=$((TOTAL_SCREENSHOTS + shots))
    fi
done

# ─── 4. Generate summary report ─────────────────────────────
SUMMARY="$RESULTS/summary.md"
cat > "$SUMMARY" << EOF
# Desktop Automation Test Report

**Date:** $(date '+%Y-%m-%d %H:%M:%S')
**Total time:** ${TOTAL_TIME}s
**Source:** \`$SRC\`

## Results

| # | Example | Status | Duration | Steps | Screenshots |
|---|---------|--------|----------|-------|-------------|
EOF

for example in "${BASH_EXAMPLES[@]}"; do
    num="${example%%_*}"
    log_file="$RESULTS/${example}.log"
    session_md="$EXAMPLES_DIR/$example/logs/session.md"

    if [ -f "$log_file" ]; then
        last_line=$(tail -1 "$log_file")
        status=$(echo "$last_line" | awk '{print $1}')
        duration=$(echo "$last_line" | awk '{print $2}')
    else
        status="SKIP"
        duration="-"
    fi

    steps=0
    shots=0
    if [ -f "$session_md" ]; then
        steps=$(grep -c "^## Step" "$session_md" 2>/dev/null || echo 0)
        shots=$(grep -c "data:image/png;base64," "$session_md" 2>/dev/null || echo 0)
    fi

    icon="⏭️"
    [ "$status" = "PASS" ] && icon="✅"
    [ "$status" = "FAIL" ] && icon="❌"

    echo "| $num | $example | $icon $status | $duration | $steps | $shots |" >> "$SUMMARY"
done

cat >> "$SUMMARY" << EOF

## Summary

- **Passed:** $PASS
- **Failed:** $FAIL
- **Skipped:** $SKIP
- **Total steps:** $TOTAL_STEPS
- **Total screenshots:** $TOTAL_SCREENSHOTS
- **Total time:** ${TOTAL_TIME}s

## Session Logs

EOF

for example in "${BASH_EXAMPLES[@]}"; do
    session_md="$EXAMPLES_DIR/$example/logs/session.md"
    if [ -f "$session_md" ]; then
        size=$(wc -c < "$session_md" | tr -d ' ')
        size_kb=$((size / 1024))
        echo "- [\`$example/logs/session.md\`](../$example/logs/session.md) (${size_kb} KB)" >> "$SUMMARY"
    fi
done

cat >> "$SUMMARY" << EOF

## Commands Used

\`\`\`bash
# Start environment
docker compose -f docker/novnc/docker-compose.yml up -d

# Run individual example
bash examples/06_desktop_automation/01_terminal/run.sh

# Run all examples
bash examples/06_desktop_automation/00_full_lifecycle/run.sh

# Run specific examples only
bash examples/06_desktop_automation/00_full_lifecycle/run.sh --only 01 03

# Cleanup
docker compose -f docker/novnc/docker-compose.yml down
\`\`\`
EOF

log "📄 Report: $SUMMARY"

# ─── 5. Teardown ────────────────────────────────────────────
if [ "$SKIP_TEARDOWN" = false ]; then
    log "🛑 Stopping Docker environment..."
    docker compose -f "$COMPOSE_FILE" down 2>&1 | tail -3
    log "✅ Environment stopped"
else
    log "⏭️  Skipping teardown (--skip-teardown)"
fi

# ─── Final summary ──────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo " Desktop Automation Test Results"
echo "═══════════════════════════════════════════════"
echo " ✅ Passed:  $PASS"
echo " ❌ Failed:  $FAIL"
echo " ⏭️  Skipped: $SKIP"
echo " 📸 Screenshots: $TOTAL_SCREENSHOTS"
echo " ⏱️  Total time: ${TOTAL_TIME}s"
echo " 📄 Report: $SUMMARY"
echo "═══════════════════════════════════════════════"
