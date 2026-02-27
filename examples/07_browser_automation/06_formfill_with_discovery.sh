#!/bin/bash
# Demo 06: Form Fill with Site Discovery
# Wypełnienie formularza z automatycznym wykryciem strony kontaktowej

set -e

echo "=========================================="
echo "DEMO 06: Form Fill with Site Discovery"
echo "=========================================="
echo ""
echo "Strona: pracodawcypomorza.pl (wymaga nawigacji do /kontakt)"
echo "Oczekiwane: Automatyczne znalezienie i wypełnienie formularza"
echo ""

python3 -m nlp2cmd -r -q "Znajdź formularz kontaktowy na https://www.pracodawcypomorza.pl i wypełnij go" --auto-confirm 2>&1 | tee /tmp/demo06.log

echo ""
echo "Rezultat:"
grep -E "(found|success|navigating|exploring)" /tmp/demo06.log | tail -10 || echo "Sprawdź pełny log: /tmp/demo06.log"
