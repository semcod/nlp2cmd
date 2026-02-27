#!/bin/bash
# Demo 01: Screenshot only (auto-confirm)
# Demonstruje automatyczny screenshot po wypełnieniu formularza

set -e

echo "=========================================="
echo "DEMO 01: Screenshot Only (auto-confirm)"
echo "=========================================="
echo ""
echo "Strona: brainbox.com.pl"
echo "Oczekiwane: Formularz wypełniony + screenshot zapisany"
echo ""

mkdir -p ./screenshots

python3 -m nlp2cmd -r -q "Znajdź i wypełnij formularz kontaktowy na https://www.brainbox.com.pl" --auto-confirm 2>&1 | tee /tmp/demo01.log

echo ""
echo "Rezultaty:"
ls -lh ./screenshots/ 2>/dev/null | tail -5 || echo "Brak screenshotów"
echo ""
echo "Log: /tmp/demo01.log"
