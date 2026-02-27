#!/bin/bash
# Demo 05: Simple Form Fill
# Proste wypełnienie formularza bez dodatkowych opcji

set -e

echo "=========================================="
echo "DEMO 05: Simple Form Fill"
echo "=========================================="
echo ""
echo "Strona: axsoft.pl"
echo "Oczekiwane: Szybkie wypełnienie bez screenshot/video"
echo ""

python3 -m nlp2cmd -r -q "Wypełnij formularz kontaktowy na https://www.axsoft.pl" --auto-confirm 2>&1 | tee /tmp/demo05.log

echo ""
echo "Rezultat:"
grep -E "(success|error|form)" /tmp/demo05.log | tail -5 || echo "Sprawdź log: /tmp/demo05.log"
