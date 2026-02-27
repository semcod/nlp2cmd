#!/bin/bash
# Demo 04: Oferteo Company Extraction
# Demonstruje ekstrakcję firm z Oferteo.pl

set -e

echo "=========================================="
echo "DEMO 04: Oferteo Company Extraction"
echo "=========================================="
echo ""
echo "Zapytanie: Firmy budowlane w Gdańsku"
echo "Oczekiwane: 20 firm zapisanych do pliku"
echo ""

python3 -m nlp2cmd -r -q "Wyszukaj firmy budowlane w Gdańsku na oferteo.pl i zapisz do pliku" --auto-confirm 2>&1 | tee /tmp/demo04.log

echo ""
echo "Rezultaty:"
ls -lh oferteo_*.txt 2>/dev/null | tail -5 || echo "Brak pliku wyjściowego"
echo ""
echo "Podgląd (pierwsze 10 linii):"
head -10 oferteo_*.txt 2>/dev/null || echo "Brak danych"
echo ""
echo "Log: /tmp/demo04.log"
