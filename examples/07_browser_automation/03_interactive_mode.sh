#!/bin/bash
# Demo 03: Interactive Mode (bez auto-confirm)
# Demonstruje interaktywne pytania o screenshot i video
# UWAGA: Wymaga ręcznego potwierdzenia (T/n)

set -e

echo "=========================================="
echo "DEMO 03: Interactive Mode (bez auto-confirm)"
echo "=========================================="
echo ""
echo "Strona: brainbox.com.pl"
echo "Oczekiwane: Pytania o screenshot i video"
echo ""
echo "Instrukcja:"
echo "  - Na pytanie 'Zrobić zrzut ekranu?' odpowiedz 't' lub naciśnij Enter"
echo "  - Na pytanie 'Nagrać wideo?' odpowiedz 't' lub naciśnij Enter"
echo "  - Na pytanie o ścieżkę zapisu naciśnij Enter (domyślna)"
echo ""

python3 -m nlp2cmd -r -q "Znajdź i wypełnij formularz kontaktowy na https://www.brainbox.com.pl" 2>&1 | tee /tmp/demo03.log

echo ""
echo "Rezultaty:"
ls -lh ./screenshots/ 2>/dev/null | tail -3 || echo "Brak screenshotów"
ls -lh ./recordings/ 2>/dev/null | tail -3 || echo "Brak nagrań"
echo ""
echo "Log: /tmp/demo03.log"
