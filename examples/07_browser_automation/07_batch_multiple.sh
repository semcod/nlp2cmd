#!/bin/bash
# Demo 07: Batch - Multiple Sites
# Szybkie testowanie wielu stron

set -e

echo "=========================================="
echo "DEMO 07: Batch - Multiple Sites"
echo "=========================================="
echo ""

SITES=(
    "https://www.axsoft.pl"
    "https://www.brainbox.com.pl"
)

mkdir -p ./screenshots ./recordings

for site in "${SITES[@]}"; do
    echo "--- Testing: $site ---"
    python3 -m nlp2cmd -r -q "Znajdź formularz na $site" --auto-confirm 2>&1 | tee "/tmp/demo07_$(echo $site | tr '/' '_').log" | tail -10
    echo ""
done

echo "Rezultaty zbiorcze:"
ls -lh ./screenshots/ ./recordings/ 2>/dev/null || echo "Brak plików"
echo ""
echo "Logi w: /tmp/demo07_*.log"
