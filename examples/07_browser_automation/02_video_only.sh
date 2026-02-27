#!/bin/bash
# Demo 02: Video Recording only (auto-confirm)
# Demonstruje nagrywanie video z całej sesji browser automation

set -e

echo "=========================================="
echo "DEMO 02: Video Recording Only"
echo "=========================================="
echo ""
echo "Strona: axsoft.pl"
echo "Oczekiwane: Nagranie video zapisane w ./recordings/"
echo ""

mkdir -p ./recordings

python3 -m nlp2cmd -r -q "Znajdź i wypełnij formularz kontaktowy na https://www.axsoft.pl" --auto-confirm 2>&1 | tee /tmp/demo02.log

echo ""
echo "Rezultaty:"
ls -lh ./recordings/*.webm 2>/dev/null | tail -5 || echo "Brak nagrań video"
echo ""
echo "Log: /tmp/demo02.log"
echo ""
echo "Odtworzenie video:"
echo "  firefox ./recordings/form_automation_*.webm"
